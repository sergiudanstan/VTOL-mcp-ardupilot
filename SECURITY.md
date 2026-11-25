# Security Policy

This project is an [MCP](https://modelcontextprotocol.io) server (`ardupilot_mcp_server.py`, stdio) and
a small web dashboard (`dashboard.py`). Both send MAVLink commands (arm, disarm, set mode, takeoff,
land, mission upload and clear) to whatever vehicle `MAVLINK_CONNECTION` points at. It is built and
tested for ArduPilot **SITL** (a simulator). Nothing here has been validated against a real aircraft,
and it must not be used to command one.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Current |

Single maintainer; only the latest release receives fixes.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.** Report it privately:
**[Report a vulnerability](https://github.com/sergiudanstan/VTOL-mcp-ardupilot/security/advisories/new)**
(Security, Advisories, Report a vulnerability).

| Stage | Target |
|---|---|
| Acknowledgement | within 3 business days |
| Triage | within 10 business days |
| Fix, or a documented decision not to fix | within 90 days |

These are best-effort targets from a single unpaid maintainer, not a contractual SLA.
There is no bug bounty; credit is offered in the advisory and changelog.

## Scope and known limitations

What an attacker could reach, from reading the code:

- **MCP tools.** The server trusts its MCP client completely and has no authentication of its own.
  `takeoff` forwards `altitude` to the vehicle without a range check, and `upload_mission` forwards
  waypoint fields (`lat`, `lon`, `alt`, `command`, `param1`..`param4`) as given, including an
  arbitrary MAVLink `command` number. `set_mode` is checked against the vehicle's own mode table.
  Whoever controls the model's tool calls (for example through prompt injection in other content in
  the same session) controls the vehicle.
- **Dashboard.** It binds to `127.0.0.1:8080` only and has no login. The WebSocket at `/ws`
  accepts `arm`, `disarm`, `set_mode`, `takeoff` and `land`, and the code does not check the
  `Origin` header, so a web page opened in a browser on the same machine can in principle open that
  socket. This has not been exploited or tested here; treat it as a real risk. Run the dashboard only
  while you use it, and never change the bind address to a non-loopback one.
- **Connection string.** `MAVLINK_CONNECTION` accepts any pymavlink endpoint, including serial devices
  and remote TCP/UDP hosts. Setting it to a real flight controller is outside what this project supports.
- **Tests.** `tests/test_input_validation.py` exercises validator functions defined inside the test file;
  the shipped server does not call them. They are not evidence that the server validates input.

In scope: command injection or arbitrary file or process access through the server or dashboard,
bypassing the loopback-only binding, and anything in this repository's workflows that could publish a
release not built from `main`.

Out of scope: vulnerabilities in ArduPilot, pymavlink, the `mcp` SDK, FastAPI or uvicorn (report
upstream), and the physical or flight safety of any real vehicle.

## Supply chain

CI runs the unit tests and a ruff check on every push, `pip-audit` on `requirements.txt` and on the
hash-pinned CI toolchain, CodeQL, and `zizmor` on the workflows. `requirements.txt` uses version
ranges, not a lockfile, so installs are not reproducible. Actions are pinned to full commit SHAs and
kept current by Dependabot. Releases attach a source archive and a CycloneDX SBOM of the runtime
environment resolved at release time, both with Sigstore build provenance:

```
gh attestation verify VTOL-mcp-ardupilot-v0.1.0.tar.gz --repo sergiudanstan/VTOL-mcp-ardupilot
```
