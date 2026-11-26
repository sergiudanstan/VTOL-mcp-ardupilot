#!/usr/bin/env python3
"""MCP server for ArduPilot SITL integration."""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mavlink_client import MAVLinkClient
from safety import check_command

# Initialize server and MAVLink client
server = Server("ardupilot-mcp")
client = MAVLinkClient()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available ArduPilot tools."""
    return [
        Tool(
            name="get_telemetry",
            description="Get vehicle telemetry (attitude, position, velocity, battery)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_status",
            description="Get vehicle status (mode, armed state, system status)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="arm",
            description="Arm the vehicle motors",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="disarm",
            description="Disarm the vehicle motors",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="set_mode",
            description="Set flight mode (GUIDED, AUTO, LOITER, STABILIZE, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Flight mode name (e.g., GUIDED, AUTO, LOITER)",
                    }
                },
                "required": ["mode"],
            },
        ),
        Tool(
            name="takeoff",
            description="Command takeoff to specified altitude (requires GUIDED mode and armed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "altitude": {
                        "type": "number",
                        "description": "Target altitude in meters",
                    }
                },
                "required": ["altitude"],
            },
        ),
        Tool(
            name="land",
            description="Command landing at current position",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_mission",
            description="Download current mission waypoints from vehicle",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="upload_mission",
            description="Upload mission waypoints to vehicle",
            inputSchema={
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "description": "List of waypoints with lat, lon, alt, and optional command",
                        "items": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                                "alt": {"type": "number"},
                                "command": {"type": "integer"},
                            },
                            "required": ["lat", "lon", "alt"],
                        },
                    }
                },
                "required": ["waypoints"],
            },
        ),
        Tool(
            name="clear_mission",
            description="Clear all mission waypoints from vehicle",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    # Refuse unsafe motion commands before touching the vehicle
    refusal = check_command(name, client.connection_string, arguments)
    if refusal:
        return [TextContent(type="text", text=json.dumps({"success": False, "error": refusal}, indent=2))]

    # Ensure connected
    if not client.master:
        if not client.connect():
            return [TextContent(type="text", text="Failed to connect to ArduPilot SITL")]

    result = None

    if name == "get_telemetry":
        result = client.get_telemetry()

    elif name == "get_status":
        result = client.get_status()

    elif name == "arm":
        success = client.arm()
        result = {"success": success, "message": "Armed" if success else "Arm failed"}

    elif name == "disarm":
        success = client.disarm()
        result = {"success": success, "message": "Disarmed" if success else "Disarm failed"}

    elif name == "set_mode":
        mode = arguments.get("mode", "")
        success = client.set_mode(mode)
        result = {"success": success, "mode": mode if success else "Mode change failed"}

    elif name == "takeoff":
        altitude = arguments.get("altitude", 10)
        success = client.takeoff(altitude)
        result = {"success": success, "altitude": altitude if success else "Takeoff failed"}

    elif name == "land":
        success = client.land()
        result = {"success": success, "message": "Landing" if success else "Land failed"}

    elif name == "get_mission":
        waypoints = client.get_mission()
        result = {"waypoint_count": len(waypoints), "waypoints": waypoints}

    elif name == "upload_mission":
        waypoints = arguments.get("waypoints", [])
        success = client.upload_mission(waypoints)
        result = {"success": success, "uploaded": len(waypoints) if success else 0}

    elif name == "clear_mission":
        success = client.clear_mission()
        result = {"success": success, "message": "Mission cleared" if success else "Clear failed"}

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
