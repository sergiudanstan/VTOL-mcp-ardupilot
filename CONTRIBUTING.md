# Contributing

Contributions are welcome. This is a single-maintainer project, so please open an issue
before starting anything substantial.

**Security problems do not belong in issues.** Follow [SECURITY.md](SECURITY.md).

## Branches, pull requests and releases

- `main` is the only long-lived branch and is protected: changes land through a pull
  request with the required checks green, commits on `main` are signed, and force-pushes
  are refused. Pull requests are squash-merged; GitHub deletes the branch on merge.
- Branch names: `<type>/<topic>` (`feat/`, `fix/`, `docs/`, `chore/`, `release/`);
  agents use `agent/<name>/<topic>`.
- A release is a pull request that sets the number in the `VERSION` file and moves
  `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md) to a dated version. After it merges, a
  signed `vX.Y.Z` tag on that commit triggers `release.yml`, which refuses to run if the
  tag, `VERSION` and the changelog disagree. Tags are never moved or deleted.

## Running it locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m pytest -q -rs            # unit tests; 4 SITL tests are skipped
SITL_RUNNING=1 python -m pytest -q # with ArduPilot SITL listening on udp:127.0.0.1:14550
python ardupilot_mcp_server.py     # the MCP server (stdio); see the README to register it
python dashboard.py                # http://localhost:8080
```

CI also runs `ruff check --select E9,F63,F7,F82` (syntax errors and undefined names only, because
the existing code does not follow ruff's wider default rules).
