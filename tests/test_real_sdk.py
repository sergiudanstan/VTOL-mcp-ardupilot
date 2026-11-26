"""Run the server against the real MCP SDK (no stubbing), over an in-process client session."""

import asyncio
import json
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXPECTED_TOOLS = {
    "get_telemetry", "get_status", "arm", "disarm", "set_mode",
    "takeoff", "land", "get_mission", "upload_mission", "clear_mission",
}


def test_real_sdk_lists_tools_and_calls_through_guard(monkeypatch):
    from mcp import Client
    import ardupilot_mcp_server as srv

    mock = MagicMock()
    mock.connection_string = "/dev/ttyUSB0"  # not SITL: motion commands must be refused
    mock.master = object()
    mock.get_telemetry.return_value = {"ok": True}
    monkeypatch.setattr(srv, "client", mock)
    monkeypatch.delenv("VTOL_MCP_ALLOW_REAL_VEHICLE", raising=False)

    async def run():
        async with Client(srv.server) as c:
            tools = (await c.list_tools()).tools
            refused = await c.call_tool("arm", {})
            telem = await c.call_tool("get_telemetry", {})
            return tools, refused, telem

    tools, refused, telem = asyncio.run(run())
    assert {t.name for t in tools} == EXPECTED_TOOLS
    by_name = {t.name: t for t in tools}
    assert by_name["takeoff"].input_schema["required"] == ["altitude"]
    assert "Refused" in json.loads(refused.content[0].text)["error"]
    mock.arm.assert_not_called()
    assert json.loads(telem.content[0].text) == {"ok": True}
