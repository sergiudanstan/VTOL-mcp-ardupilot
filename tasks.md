# Tasks

## In Progress
- [ ] Add comprehensive test suite
- [ ] Implement input validation

## Completed
- [x] Create project structure
- [x] Implement MAVLink client
- [x] Implement MCP server with 10 tools
- [x] Create connection test script
- [x] Set up Python 3.12 venv
- [x] Create private GitHub repository
- [x] Write README documentation

## Backlog

### High Priority
- [ ] Add input validation for all tool parameters
- [ ] Add pytest test suite
- [ ] Handle SITL disconnection gracefully
- [ ] Add connection timeout configuration

### Medium Priority
- [ ] Add parameter read/write tools
- [ ] Implement geofence tools
- [ ] Add servo output monitoring
- [ ] Support multiple vehicle connections

### Low Priority
- [ ] Add log download capability
- [ ] Create web dashboard for monitoring
- [ ] Support real hardware connections
- [ ] Add authentication for remote connections

## Test Cases to Implement

### Quality Tests
- [ ] `test_connection_lifecycle` - connect/disconnect/reconnect
- [ ] `test_telemetry_parsing` - validate data extraction
- [ ] `test_command_ack` - verify command acknowledgments
- [ ] `test_mission_roundtrip` - upload then download
- [ ] `test_timeout_handling` - graceful failure
- [ ] `test_mcp_responses` - valid JSON structure

### Security Tests
- [ ] `test_mode_validation` - reject invalid modes
- [ ] `test_altitude_bounds` - reject bad altitudes
- [ ] `test_coordinate_validation` - validate lat/lon
- [ ] `test_connection_string` - sanitize URLs
