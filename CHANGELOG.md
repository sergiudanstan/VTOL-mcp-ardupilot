# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-11-26

### Security
- Motion commands (`arm`, `takeoff`, `set_mode`, `upload_mission`) are refused unless
  `MAVLINK_CONNECTION` is UDP/TCP to localhost; `VTOL_MCP_ALLOW_REAL_VEHICLE=1` overrides.
- `takeoff` and mission waypoint altitudes above `VTOL_MCP_MAX_ALT_M` (default 120 m) are rejected.
- The dashboard WebSocket rejects connections with a foreign `Origin` header and applies the same limits.

## [0.1.0] - 2026-11-25

First tagged release. An MCP server that lets Claude read telemetry from, and send commands to,
an ArduPilot SITL vehicle over MAVLink (ten tools: telemetry, status, arm, disarm, set mode,
takeoff, land, and mission get, upload and clear), plus a local web dashboard for live telemetry
and commands.

### Added
- Unit tests and a ruff check run in CI on every push and pull request.
- CI, CodeQL, OpenSSF Scorecard and a tag-triggered release workflow with build provenance and
  a CycloneDX SBOM; Dependabot for actions and pip.
- `SECURITY.md`, `CONTRIBUTING.md`, this changelog and a `VERSION` file.

[Unreleased]: https://github.com/sergiudanstan/VTOL-mcp-ardupilot/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/sergiudanstan/VTOL-mcp-ardupilot/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/sergiudanstan/VTOL-mcp-ardupilot/releases/tag/v0.1.0
