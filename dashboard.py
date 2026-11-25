#!/usr/bin/env python3
"""Web dashboard for ArduPilot MCP server."""

import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from mavlink_client import MAVLinkClient

# Global client instance
client = MAVLinkClient()
connected = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to SITL on startup."""
    global connected
    print("Connecting to ArduPilot SITL...")
    connected = client.connect()
    if connected:
        print("Connected to SITL")
    else:
        print("Warning: Could not connect to SITL")
    yield
    print("Disconnecting...")
    client.disconnect()


app = FastAPI(title="ArduPilot Dashboard", lifespan=lifespan)


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ArduPilot Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #00d4ff;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #0f3460;
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #0f3460;
        }
        .status-row:last-child { border-bottom: none; }
        .label { color: #888; }
        .value { font-weight: 600; font-family: monospace; }
        .connected { color: #00ff88; }
        .disconnected { color: #ff4444; }
        .armed { color: #ff8800; }
        .disarmed { color: #00ff88; }

        .controls {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        button {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:active { transform: translateY(0); }

        .btn-arm { background: #ff8800; color: #000; }
        .btn-disarm { background: #00ff88; color: #000; }
        .btn-mode { background: #0066ff; color: #fff; }
        .btn-takeoff { background: #9933ff; color: #fff; }
        .btn-land { background: #ff3366; color: #fff; }

        .mode-select {
            width: 100%;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #0f3460;
            background: #1a1a2e;
            color: #fff;
            margin-bottom: 10px;
        }

        .attitude-display {
            display: flex;
            justify-content: space-around;
            text-align: center;
        }
        .attitude-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #00d4ff;
        }
        .attitude-label {
            font-size: 0.8em;
            color: #888;
            margin-top: 5px;
        }

        .log {
            background: #0f0f1a;
            border-radius: 8px;
            padding: 10px;
            height: 150px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.85em;
        }
        .log-entry { padding: 3px 0; border-bottom: 1px solid #1a1a2e; }
        .log-time { color: #666; }
        .log-success { color: #00ff88; }
        .log-error { color: #ff4444; }
    </style>
</head>
<body>
    <h1>ArduPilot Dashboard</h1>

    <div class="grid">
        <div class="card">
            <h2>Connection Status</h2>
            <div class="status-row">
                <span class="label">Status</span>
                <span class="value" id="conn-status">Connecting...</span>
            </div>
            <div class="status-row">
                <span class="label">Endpoint</span>
                <span class="value">udp:127.0.0.1:14550</span>
            </div>
        </div>

        <div class="card">
            <h2>Vehicle Status</h2>
            <div class="status-row">
                <span class="label">Mode</span>
                <span class="value" id="mode">--</span>
            </div>
            <div class="status-row">
                <span class="label">Armed</span>
                <span class="value" id="armed">--</span>
            </div>
        </div>

        <div class="card">
            <h2>Attitude</h2>
            <div class="attitude-display">
                <div>
                    <div class="attitude-value" id="roll">0.0°</div>
                    <div class="attitude-label">Roll</div>
                </div>
                <div>
                    <div class="attitude-value" id="pitch">0.0°</div>
                    <div class="attitude-label">Pitch</div>
                </div>
                <div>
                    <div class="attitude-value" id="yaw">0.0°</div>
                    <div class="attitude-label">Yaw</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Position</h2>
            <div class="status-row">
                <span class="label">Latitude</span>
                <span class="value" id="lat">--</span>
            </div>
            <div class="status-row">
                <span class="label">Longitude</span>
                <span class="value" id="lon">--</span>
            </div>
            <div class="status-row">
                <span class="label">Altitude</span>
                <span class="value" id="alt">-- m</span>
            </div>
        </div>

        <div class="card">
            <h2>Velocity</h2>
            <div class="status-row">
                <span class="label">Airspeed</span>
                <span class="value" id="airspeed">-- m/s</span>
            </div>
            <div class="status-row">
                <span class="label">Groundspeed</span>
                <span class="value" id="groundspeed">-- m/s</span>
            </div>
            <div class="status-row">
                <span class="label">Climb Rate</span>
                <span class="value" id="climb">-- m/s</span>
            </div>
        </div>

        <div class="card">
            <h2>Battery</h2>
            <div class="status-row">
                <span class="label">Voltage</span>
                <span class="value" id="voltage">-- V</span>
            </div>
            <div class="status-row">
                <span class="label">Remaining</span>
                <span class="value" id="battery">--%</span>
            </div>
        </div>

        <div class="card">
            <h2>Controls</h2>
            <select class="mode-select" id="mode-select">
                <option value="STABILIZE">STABILIZE</option>
                <option value="GUIDED">GUIDED</option>
                <option value="AUTO">AUTO</option>
                <option value="LOITER">LOITER</option>
                <option value="RTL">RTL</option>
                <option value="LAND">LAND</option>
            </select>
            <div class="controls">
                <button class="btn-mode" onclick="setMode()">Set Mode</button>
                <button class="btn-arm" onclick="arm()">ARM</button>
                <button class="btn-disarm" onclick="disarm()">DISARM</button>
                <button class="btn-takeoff" onclick="takeoff()">TAKEOFF</button>
                <button class="btn-land" onclick="land()">LAND</button>
            </div>
        </div>

        <div class="card">
            <h2>Command Log</h2>
            <div class="log" id="log"></div>
        </div>
    </div>

    <script>
        let ws;

        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onopen = () => {
                document.getElementById('conn-status').textContent = 'Connected';
                document.getElementById('conn-status').className = 'value connected';
                log('Connected to dashboard', 'success');
            };

            ws.onclose = () => {
                document.getElementById('conn-status').textContent = 'Disconnected';
                document.getElementById('conn-status').className = 'value disconnected';
                log('Disconnected from dashboard', 'error');
                setTimeout(connect, 2000);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDisplay(data);
            };
        }

        function updateDisplay(data) {
            if (data.status) {
                document.getElementById('mode').textContent = data.status.mode;
                const armedEl = document.getElementById('armed');
                armedEl.textContent = data.status.armed ? 'ARMED' : 'DISARMED';
                armedEl.className = 'value ' + (data.status.armed ? 'armed' : 'disarmed');
            }

            if (data.telemetry) {
                const t = data.telemetry;
                document.getElementById('roll').textContent = (t.attitude.roll * 57.3).toFixed(1) + '°';
                document.getElementById('pitch').textContent = (t.attitude.pitch * 57.3).toFixed(1) + '°';
                document.getElementById('yaw').textContent = (t.attitude.yaw * 57.3).toFixed(1) + '°';

                document.getElementById('lat').textContent = t.position.lat.toFixed(6);
                document.getElementById('lon').textContent = t.position.lon.toFixed(6);
                document.getElementById('alt').textContent = t.position.alt.toFixed(1) + ' m';

                document.getElementById('airspeed').textContent = t.velocity.airspeed.toFixed(1) + ' m/s';
                document.getElementById('groundspeed').textContent = t.velocity.groundspeed.toFixed(1) + ' m/s';
                document.getElementById('climb').textContent = t.velocity.climb.toFixed(1) + ' m/s';

                document.getElementById('voltage').textContent = t.battery.voltage.toFixed(1) + ' V';
                document.getElementById('battery').textContent = t.battery.remaining + '%';
            }

            if (data.response) {
                log(JSON.stringify(data.response), data.response.success ? 'success' : 'error');
            }
        }

        function log(msg, type = '') {
            const logEl = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${type}">${msg}</span>`;
            logEl.insertBefore(entry, logEl.firstChild);
        }

        function sendCommand(cmd, params = {}) {
            ws.send(JSON.stringify({ command: cmd, ...params }));
        }

        function setMode() {
            const mode = document.getElementById('mode-select').value;
            sendCommand('set_mode', { mode });
            log(`Setting mode to ${mode}...`);
        }

        function arm() {
            sendCommand('arm');
            log('Arming...');
        }

        function disarm() {
            sendCommand('disarm');
            log('Disarming...');
        }

        function takeoff() {
            const alt = prompt('Enter takeoff altitude (meters):', '10');
            if (alt) {
                sendCommand('takeoff', { altitude: parseFloat(alt) });
                log(`Taking off to ${alt}m...`);
            }
        }

        function land() {
            sendCommand('land');
            log('Landing...');
        }

        connect();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML."""
    return DASHBOARD_HTML


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()

    async def send_updates():
        """Send telemetry updates periodically."""
        while True:
            try:
                data = {
                    "status": client.get_status(),
                    "telemetry": client.get_telemetry(),
                }
                await websocket.send_json(data)
                await asyncio.sleep(0.2)  # 5 Hz update rate
            except Exception:
                break

    update_task = asyncio.create_task(send_updates())

    try:
        while True:
            data = await websocket.receive_json()
            cmd = data.get("command")
            response = {"success": False, "message": "Unknown command"}

            if cmd == "arm":
                success = client.arm()
                response = {"success": success, "message": "Armed" if success else "Arm failed"}

            elif cmd == "disarm":
                success = client.disarm()
                response = {"success": success, "message": "Disarmed" if success else "Disarm failed"}

            elif cmd == "set_mode":
                mode = data.get("mode", "")
                success = client.set_mode(mode)
                response = {"success": success, "message": f"Mode set to {mode}" if success else "Mode change failed"}

            elif cmd == "takeoff":
                altitude = data.get("altitude", 10)
                success = client.takeoff(altitude)
                response = {"success": success, "message": f"Taking off to {altitude}m" if success else "Takeoff failed"}

            elif cmd == "land":
                success = client.land()
                response = {"success": success, "message": "Landing" if success else "Land failed"}

            await websocket.send_json({"response": response})

    except WebSocketDisconnect:
        pass
    finally:
        update_task.cancel()


if __name__ == "__main__":
    print("Starting ArduPilot Dashboard...")
    print("Open http://localhost:8080 in your browser")
    uvicorn.run(app, host="127.0.0.1", port=8080)
