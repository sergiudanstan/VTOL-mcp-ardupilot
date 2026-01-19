"""MAVLink client for ArduPilot SITL communication."""

import os
import time
import threading
from typing import Optional
from pymavlink import mavutil


class MAVLinkClient:
    """Handles MAVLink connection and communication with ArduPilot."""

    def __init__(self, connection_string: Optional[str] = None):
        """Initialize MAVLink client.

        Args:
            connection_string: MAVLink connection string (e.g., 'udp:127.0.0.1:14550').
                             Defaults to MAVLINK_CONNECTION env var or 'udp:127.0.0.1:14550'.
        """
        self.connection_string = connection_string or os.environ.get(
            'MAVLINK_CONNECTION', 'udp:127.0.0.1:14550'
        )
        self.master: Optional[mavutil.mavlink_connection] = None
        self._telemetry = {}
        self._telemetry_lock = threading.Lock()
        self._running = False
        self._recv_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """Establish connection to MAVLink endpoint.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.master = mavutil.mavlink_connection(self.connection_string)
            self.master.wait_heartbeat(timeout=10)
            self._running = True
            self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._recv_thread.start()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Close the MAVLink connection."""
        self._running = False
        if self._recv_thread:
            self._recv_thread.join(timeout=2)
        if self.master:
            self.master.close()
            self.master = None

    def _receive_loop(self):
        """Background thread to receive and cache MAVLink messages."""
        while self._running and self.master:
            try:
                msg = self.master.recv_match(blocking=True, timeout=1)
                if msg:
                    msg_type = msg.get_type()
                    with self._telemetry_lock:
                        self._telemetry[msg_type] = msg.to_dict()
            except Exception:
                pass

    def get_telemetry(self) -> dict:
        """Get current telemetry data.

        Returns:
            Dictionary with attitude, position, velocity, and battery info.
        """
        with self._telemetry_lock:
            attitude = self._telemetry.get('ATTITUDE', {})
            gps = self._telemetry.get('GLOBAL_POSITION_INT', {})
            battery = self._telemetry.get('BATTERY_STATUS', {})
            vfr = self._telemetry.get('VFR_HUD', {})

        return {
            'attitude': {
                'roll': attitude.get('roll', 0),
                'pitch': attitude.get('pitch', 0),
                'yaw': attitude.get('yaw', 0),
            },
            'position': {
                'lat': gps.get('lat', 0) / 1e7 if gps.get('lat') else 0,
                'lon': gps.get('lon', 0) / 1e7 if gps.get('lon') else 0,
                'alt': gps.get('relative_alt', 0) / 1000 if gps.get('relative_alt') else 0,
            },
            'velocity': {
                'airspeed': vfr.get('airspeed', 0),
                'groundspeed': vfr.get('groundspeed', 0),
                'climb': vfr.get('climb', 0),
            },
            'battery': {
                'voltage': battery.get('voltages', [0])[0] / 1000 if battery.get('voltages') else 0,
                'remaining': battery.get('battery_remaining', -1),
            },
        }

    def get_status(self) -> dict:
        """Get vehicle status.

        Returns:
            Dictionary with mode, armed state, and system status.
        """
        with self._telemetry_lock:
            heartbeat = self._telemetry.get('HEARTBEAT', {})
            sys_status = self._telemetry.get('SYS_STATUS', {})

        mode_mapping = self.master.mode_mapping() if self.master else {}
        mode_num = heartbeat.get('custom_mode', 0)
        mode_name = 'UNKNOWN'
        for name, num in mode_mapping.items():
            if num == mode_num:
                mode_name = name
                break

        base_mode = heartbeat.get('base_mode', 0)
        armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

        return {
            'mode': mode_name,
            'armed': armed,
            'system_status': heartbeat.get('system_status', 0),
            'sensors_health': sys_status.get('onboard_control_sensors_health', 0),
        }

    def arm(self) -> bool:
        """Arm the vehicle.

        Returns:
            True if command accepted.
        """
        if not self.master:
            return False
        self.master.arducopter_arm()
        return self._wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)

    def disarm(self) -> bool:
        """Disarm the vehicle.

        Returns:
            True if command accepted.
        """
        if not self.master:
            return False
        self.master.arducopter_disarm()
        return self._wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM)

    def set_mode(self, mode: str) -> bool:
        """Set flight mode.

        Args:
            mode: Mode name (e.g., 'GUIDED', 'AUTO', 'LOITER').

        Returns:
            True if mode change successful.
        """
        if not self.master:
            return False
        mode_mapping = self.master.mode_mapping()
        if mode.upper() not in mode_mapping:
            return False
        mode_id = mode_mapping[mode.upper()]
        self.master.set_mode(mode_id)
        time.sleep(0.5)
        status = self.get_status()
        return status['mode'] == mode.upper()

    def takeoff(self, altitude: float) -> bool:
        """Command takeoff to specified altitude.

        Args:
            altitude: Target altitude in meters.

        Returns:
            True if command accepted.
        """
        if not self.master:
            return False
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0, 0, 0, 0, 0, 0, altitude
        )
        return self._wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF)

    def land(self) -> bool:
        """Command landing at current position.

        Returns:
            True if command accepted.
        """
        if not self.master:
            return False
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0, 0, 0, 0, 0, 0, 0, 0
        )
        return self._wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_LAND)

    def get_mission(self) -> list:
        """Download mission waypoints from vehicle.

        Returns:
            List of waypoint dictionaries.
        """
        if not self.master:
            return []

        self.master.waypoint_request_list_send()
        msg = self.master.recv_match(type='MISSION_COUNT', blocking=True, timeout=5)
        if not msg:
            return []

        waypoints = []
        for i in range(msg.count):
            self.master.waypoint_request_send(i)
            wp = self.master.recv_match(type='MISSION_ITEM', blocking=True, timeout=5)
            if wp:
                waypoints.append({
                    'seq': wp.seq,
                    'command': wp.command,
                    'lat': wp.x,
                    'lon': wp.y,
                    'alt': wp.z,
                    'param1': wp.param1,
                    'param2': wp.param2,
                    'param3': wp.param3,
                    'param4': wp.param4,
                })
        return waypoints

    def upload_mission(self, waypoints: list) -> bool:
        """Upload mission waypoints to vehicle.

        Args:
            waypoints: List of waypoint dicts with lat, lon, alt, command.

        Returns:
            True if upload successful.
        """
        if not self.master:
            return False

        self.master.waypoint_clear_all_send()
        time.sleep(0.5)

        self.master.waypoint_count_send(len(waypoints))
        msg = self.master.recv_match(type='MISSION_REQUEST', blocking=True, timeout=5)
        if not msg:
            return False

        for i, wp in enumerate(waypoints):
            self.master.mav.mission_item_send(
                self.master.target_system,
                self.master.target_component,
                i,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                wp.get('command', mavutil.mavlink.MAV_CMD_NAV_WAYPOINT),
                0, 1,
                wp.get('param1', 0),
                wp.get('param2', 0),
                wp.get('param3', 0),
                wp.get('param4', 0),
                wp.get('lat', 0),
                wp.get('lon', 0),
                wp.get('alt', 0)
            )
            if i < len(waypoints) - 1:
                self.master.recv_match(type='MISSION_REQUEST', blocking=True, timeout=5)

        ack = self.master.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
        return ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED

    def clear_mission(self) -> bool:
        """Clear all mission waypoints.

        Returns:
            True if clear successful.
        """
        if not self.master:
            return False
        self.master.waypoint_clear_all_send()
        ack = self.master.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
        return ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED

    def _wait_command_ack(self, command: int, timeout: float = 5) -> bool:
        """Wait for command acknowledgment.

        Args:
            command: MAVLink command ID.
            timeout: Timeout in seconds.

        Returns:
            True if command accepted.
        """
        if not self.master:
            return False
        ack = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=timeout)
        return ack and ack.command == command and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED
