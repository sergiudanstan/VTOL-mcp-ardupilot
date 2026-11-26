"""Safety guards: refuse motion commands to a non-SITL vehicle, clamp altitude.

Environment:
    VTOL_MCP_ALLOW_REAL_VEHICLE=1  allow motion commands on serial / non-local links.
    VTOL_MCP_MAX_ALT_M             altitude ceiling in meters (default 120).
"""

import math
import os
from typing import Optional

ALLOW_REAL_ENV = "VTOL_MCP_ALLOW_REAL_VEHICLE"
MAX_ALT_ENV = "VTOL_MCP_MAX_ALT_M"
DEFAULT_MAX_ALT_M = 120.0

# Tools that move or may move the vehicle. Read-only tools, disarm, land and
# clear_mission are deliberately not gated.
MOTION_COMMANDS = frozenset({"arm", "takeoff", "set_mode", "upload_mission"})

_NETWORK_SCHEMES = {"udp", "udpin", "udpout", "tcp", "tcpin", "tcpout"}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_sitl_connection(connection: str) -> bool:
    """True only for UDP/TCP to a loopback host. Everything else (serial, remote
    hosts, wildcard binds, unparseable strings) is treated as a real vehicle."""
    conn = (connection or "").strip()
    scheme, sep, rest = conn.partition(":")
    if not sep or scheme.lower() not in _NETWORK_SCHEMES:
        # Bare "host:port" is UDP in pymavlink, but anything not explicit is refused.
        return False
    if rest.startswith("["):  # [::1]:14550
        host = rest[1:].split("]", 1)[0]
    else:
        host = rest.rsplit(":", 1)[0] if ":" in rest else rest
    host = host.strip().lower()
    return host in _LOCAL_HOSTS or (host.startswith("127.") and _is_ipv4(host))


def _is_ipv4(host: str) -> bool:
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() and int(p) <= 255 for p in parts)


def real_vehicle_allowed() -> bool:
    return os.environ.get(ALLOW_REAL_ENV) == "1"


def max_altitude_m() -> float:
    """Configured ceiling; an invalid or non-positive value falls back to the default."""
    raw = os.environ.get(MAX_ALT_ENV)
    if raw is None:
        return DEFAULT_MAX_ALT_M
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MAX_ALT_M
    return value if math.isfinite(value) and value > 0 else DEFAULT_MAX_ALT_M


def check_altitude(altitude, what: str = "altitude") -> Optional[str]:
    """Return an error message if altitude is not a finite number in (0, max]."""
    if isinstance(altitude, bool) or not isinstance(altitude, (int, float)) or not math.isfinite(altitude):
        return f"Refused: {what} must be a finite number."
    ceiling = max_altitude_m()
    if altitude > ceiling:
        return (f"Refused: {what} {altitude} m is above the {ceiling:g} m ceiling "
                f"({MAX_ALT_ENV}).")
    return None


def check_command(name: str, connection: str, arguments: Optional[dict] = None) -> Optional[str]:
    """Return an error message if the command must be refused, else None."""
    arguments = arguments or {}
    if name not in MOTION_COMMANDS:
        return None
    if not is_sitl_connection(connection) and not real_vehicle_allowed():
        return (f"Refused: '{name}' is a motion command and the connection '{connection}' is "
                f"not a local SITL link. Set {ALLOW_REAL_ENV}=1 to allow commanding a real vehicle.")
    if name == "takeoff":
        alt = arguments.get("altitude", 10)
        err = check_altitude(alt, "takeoff altitude")
        if err:
            return err
        if alt <= 0:
            return "Refused: takeoff altitude must be positive."
    elif name == "upload_mission":
        waypoints = arguments.get("waypoints", [])
        if not isinstance(waypoints, list):
            return "Refused: waypoints must be a list."
        for i, wp in enumerate(waypoints):
            if not isinstance(wp, dict):
                return f"Refused: waypoint {i} must be an object."
            err = check_altitude(wp.get("alt", 0), f"waypoint {i} altitude")
            if err:
                return err
    return None
