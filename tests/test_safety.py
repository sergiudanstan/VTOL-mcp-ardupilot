"""Tests for the real-vehicle guard, altitude clamp and dashboard Origin check."""

import asyncio
import json
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety import (
    ALLOW_REAL_ENV,
    MAX_ALT_ENV,
    check_command,
    is_sitl_connection,
    max_altitude_m,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ALLOW_REAL_ENV, raising=False)
    monkeypatch.delenv(MAX_ALT_ENV, raising=False)


@pytest.mark.parametrize("conn", [
    "udp:127.0.0.1:14550", "tcp:127.0.0.1:5760", "udpin:localhost:14550",
    "tcp:127.0.0.5:5760", "udpout:[::1]:14550",
])
def test_sitl_connections_allowed(conn):
    assert is_sitl_connection(conn)


@pytest.mark.parametrize("conn", [
    "/dev/ttyUSB0", "/dev/tty.usbserial-1", "COM3", "udp:192.168.1.10:14550",
    "tcp:example.com:5760", "udpin:0.0.0.0:14550", "tcp:127.evil.com:5760",
    "127.0.0.1:14550", "", "garbage",
])
def test_real_connections_refused(conn):
    assert not is_sitl_connection(conn)


MOTION = [
    ("arm", {}), ("takeoff", {"altitude": 10}), ("set_mode", {"mode": "GUIDED"}),
    ("upload_mission", {"waypoints": [{"lat": 1, "lon": 2, "alt": 10}]}),
]


@pytest.mark.parametrize("name,args", MOTION)
def test_motion_refused_on_serial(name, args):
    assert "Refused" in check_command(name, "/dev/ttyUSB0", args)


@pytest.mark.parametrize("name,args", MOTION)
def test_motion_allowed_on_sitl(name, args):
    assert check_command(name, "udp:127.0.0.1:14550", args) is None


@pytest.mark.parametrize("name", ["get_telemetry", "get_status", "get_mission", "disarm", "land"])
def test_read_only_and_safety_tools_not_gated(name):
    assert check_command(name, "/dev/ttyUSB0", {}) is None


@pytest.mark.parametrize("name,args", MOTION)
def test_override_env_allows_real_vehicle(monkeypatch, name, args):
    monkeypatch.setenv(ALLOW_REAL_ENV, "1")
    assert check_command(name, "/dev/ttyUSB0", args) is None


def test_override_requires_exactly_one(monkeypatch):
    monkeypatch.setenv(ALLOW_REAL_ENV, "true")
    assert check_command("arm", "/dev/ttyUSB0") is not None


def test_altitude_default_ceiling():
    assert max_altitude_m() == 120
    assert check_command("takeoff", "udp:127.0.0.1:14550", {"altitude": 120}) is None
    assert "ceiling" in check_command("takeoff", "udp:127.0.0.1:14550", {"altitude": 120.1})


def test_altitude_env_override(monkeypatch):
    monkeypatch.setenv(MAX_ALT_ENV, "30")
    assert check_command("takeoff", "udp:127.0.0.1:14550", {"altitude": 31}) is not None
    assert check_command("takeoff", "udp:127.0.0.1:14550", {"altitude": 30}) is None


@pytest.mark.parametrize("bad", ["abc", "nan", "inf", "-5", "0"])
def test_invalid_ceiling_falls_back(monkeypatch, bad):
    monkeypatch.setenv(MAX_ALT_ENV, bad)
    assert max_altitude_m() == 120


@pytest.mark.parametrize("alt", [float("nan"), float("inf"), "10", None, True, -5, 0])
def test_bad_takeoff_altitudes_refused(alt):
    assert check_command("takeoff", "udp:127.0.0.1:14550", {"altitude": alt}) is not None


def test_mission_item_above_ceiling_refused():
    wps = [{"lat": 0, "lon": 0, "alt": 50}, {"lat": 0, "lon": 0, "alt": 500}]
    err = check_command("upload_mission", "udp:127.0.0.1:14550", {"waypoints": wps})
    assert "waypoint 1" in err


def test_malformed_waypoints_refused():
    assert check_command("upload_mission", "udp:127.0.0.1:14550", {"waypoints": "x"}) is not None
    assert check_command("upload_mission", "udp:127.0.0.1:14550", {"waypoints": [3]}) is not None


# ---- tool level (MAVLink client mocked) ----

class _FakeServer:
    """Stand-in for mcp.server.Server so the tool handlers can be imported and
    called without the mcp package (its decorator API differs across versions)."""

    def __init__(self, *a, **k):
        pass

    def list_tools(self):
        return lambda f: f

    def call_tool(self):
        return lambda f: f


class _FakeText:
    def __init__(self, type, text):
        self.type, self.text = type, text


def _load_server(monkeypatch):
    import types
    for mod, attrs in {
        "mcp": {}, "mcp.server": {"Server": _FakeServer},
        "mcp.server.stdio": {"stdio_server": None},
        "mcp.types": {"Tool": lambda **k: k, "TextContent": _FakeText},
    }.items():
        m = types.ModuleType(mod)
        m.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, mod, m)
    monkeypatch.delitem(sys.modules, "ardupilot_mcp_server", raising=False)
    import ardupilot_mcp_server
    return ardupilot_mcp_server


def _call(monkeypatch, connection, name, args):
    srv = _load_server(monkeypatch)
    mock = MagicMock()
    mock.connection_string = connection
    mock.master = object()
    mock.get_telemetry.return_value = {}
    mock.arm.return_value = mock.takeoff.return_value = True
    mock.set_mode.return_value = mock.upload_mission.return_value = True
    monkeypatch.setattr(srv, "client", mock)
    out = asyncio.run(srv.call_tool(name, args))
    return mock, json.loads(out[0].text)


@pytest.mark.parametrize("name,args", MOTION)
def test_tool_refuses_on_serial_without_sending(monkeypatch, name, args):
    mock, result = _call(monkeypatch, "/dev/ttyUSB0", name, args)
    assert result["success"] is False and "Refused" in result["error"]
    getattr(mock, name).assert_not_called()


@pytest.mark.parametrize("name,args", MOTION)
def test_tool_runs_on_sitl(monkeypatch, name, args):
    mock, result = _call(monkeypatch, "udp:127.0.0.1:14550", name, args)
    assert result["success"] is True
    getattr(mock, name).assert_called_once()


def test_tool_takeoff_above_ceiling_refused(monkeypatch):
    mock, result = _call(monkeypatch, "udp:127.0.0.1:14550", "takeoff", {"altitude": 500})
    assert "ceiling" in result["error"]
    mock.takeoff.assert_not_called()


def test_tool_telemetry_allowed_on_serial(monkeypatch):
    mock, _ = _call(monkeypatch, "/dev/ttyUSB0", "get_telemetry", {})
    mock.get_telemetry.assert_called_once()


# ---- dashboard Origin ----

def test_origin_check_function():
    import dashboard
    assert dashboard.origin_allowed("http://127.0.0.1:8080")
    assert dashboard.origin_allowed("http://localhost:8080")
    assert dashboard.origin_allowed(None)
    assert not dashboard.origin_allowed("https://evil.example")
    assert not dashboard.origin_allowed("http://127.0.0.1:9999")
    assert not dashboard.origin_allowed("null")


def test_websocket_rejects_foreign_origin_and_accepts_own(monkeypatch):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    import dashboard
    mock = MagicMock()
    mock.connection_string = "udp:127.0.0.1:14550"
    mock.get_status.return_value = {}
    mock.get_telemetry.return_value = {}
    mock.arm.return_value = True
    monkeypatch.setattr(dashboard, "client", mock)
    tc = TestClient(dashboard.app)  # no lifespan: not used as context manager
    with pytest.raises(WebSocketDisconnect):
        with tc.websocket_connect("/ws", headers={"origin": "https://evil.example"}):
            pass
    mock.arm.assert_not_called()
    with tc.websocket_connect("/ws", headers={"origin": "http://127.0.0.1:8080"}) as ws:
        ws.send_json({"command": "arm"})
        resp = next(m for m in (ws.receive_json() for _ in range(10)) if "response" in m)
    assert resp["response"]["success"] is True
    mock.arm.assert_called_once()


def test_dashboard_refuses_motion_on_serial(monkeypatch):
    from fastapi.testclient import TestClient
    import dashboard
    mock = MagicMock()
    mock.connection_string = "/dev/ttyUSB0"
    mock.get_status.return_value = {}
    mock.get_telemetry.return_value = {}
    monkeypatch.setattr(dashboard, "client", mock)
    with TestClient(dashboard.app).websocket_connect("/ws") as ws:
        ws.send_json({"command": "arm"})
        resp = next(m for m in (ws.receive_json() for _ in range(10)) if "response" in m)
    assert "Refused" in resp["response"]["message"]
    mock.arm.assert_not_called()
