# ArduPilot MCP Server - Project Plan

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude Code   │────▶│   MCP Server     │────▶│  ArduPilot SITL │
│                 │◀────│ (ardupilot_mcp)  │◀────│   (MAVLink)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
   MCP Protocol           MAVLink Client            UDP/TCP
   (stdio/JSON)           (pymavlink)              Port 14550
```

## Components

### 1. MCP Server (`ardupilot_mcp_server.py`)
- Exposes 10 tools via MCP protocol
- Handles async tool calls
- Returns JSON responses

### 2. MAVLink Client (`mavlink_client.py`)
- Manages connection lifecycle
- Background thread for message receiving
- Caches telemetry data
- Sends commands with ACK handling

### 3. Connection Test (`test_connection.py`)
- Validates SITL connectivity
- Displays telemetry snapshot

## Data Flow

1. Claude sends tool request via MCP
2. Server parses request, calls MAVLink client
3. Client sends MAVLink message to SITL
4. SITL responds with data or ACK
5. Client returns structured data
6. Server formats JSON response
7. Claude receives tool result

## Security Considerations

- **Input Validation**: All user inputs validated before MAVLink transmission
- **Mode Whitelist**: Only valid ArduPilot modes accepted
- **Altitude Bounds**: Reject negative or extreme values
- **Coordinate Validation**: Lat/lon must be in valid ranges
- **Connection Isolation**: SITL-only by default (localhost)

## Roadmap

### Phase 1: Core Functionality (Complete)
- [x] MAVLink connection
- [x] Telemetry reading
- [x] Basic commands (arm, disarm, mode)
- [x] Mission management
- [x] MCP server integration

### Phase 2: Quality & Security
- [ ] Input validation layer
- [ ] Comprehensive test suite
- [ ] Error handling improvements
- [ ] Reconnection logic

### Phase 3: Extended Features
- [ ] Parameter read/write
- [ ] Geofence management
- [ ] Log download
- [ ] Real hardware support (with safety checks)

## Testing Strategy

### Unit Tests
- MAVLink client methods (mocked SITL)
- Input validation functions
- JSON response formatting

### Integration Tests
- Full tool calls with live SITL
- Connection/disconnection cycles
- Mission upload/download round-trip

### Security Tests
- Fuzzing mode names
- Boundary value testing
- Malformed input handling
