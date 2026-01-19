"""Unit tests for MAVLink client."""

import sys
import os
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mavlink_client import MAVLinkClient


class TestMAVLinkClientConnection:
    """Test connection lifecycle."""

    def test_client_initialization(self):
        """Test client initializes with default connection string."""
        client = MAVLinkClient()
        assert client.connection_string == 'udp:127.0.0.1:14550'
        assert client.master is None

    def test_client_custom_connection(self):
        """Test client accepts custom connection string."""
        client = MAVLinkClient('tcp:192.168.1.100:5760')
        assert client.connection_string == 'tcp:192.168.1.100:5760'

    def test_client_env_connection(self, monkeypatch):
        """Test client reads from environment variable."""
        monkeypatch.setenv('MAVLINK_CONNECTION', 'udp:10.0.0.1:14551')
        client = MAVLinkClient()
        assert client.connection_string == 'udp:10.0.0.1:14551'

    @pytest.mark.skipif(
        os.environ.get('SITL_RUNNING') != '1',
        reason='SITL not running (set SITL_RUNNING=1 to enable)'
    )
    def test_connect_to_sitl(self):
        """Test actual connection to SITL."""
        client = MAVLinkClient()
        assert client.connect() is True
        assert client.master is not None
        client.disconnect()
        assert client.master is None


class TestMAVLinkClientTelemetry:
    """Test telemetry data retrieval."""

    def test_telemetry_structure(self):
        """Test telemetry returns correct structure."""
        client = MAVLinkClient()
        # Without connection, should return zeros
        telemetry = client.get_telemetry()

        assert 'attitude' in telemetry
        assert 'position' in telemetry
        assert 'velocity' in telemetry
        assert 'battery' in telemetry

        assert 'roll' in telemetry['attitude']
        assert 'pitch' in telemetry['attitude']
        assert 'yaw' in telemetry['attitude']

        assert 'lat' in telemetry['position']
        assert 'lon' in telemetry['position']
        assert 'alt' in telemetry['position']

    def test_status_structure(self):
        """Test status returns correct structure."""
        client = MAVLinkClient()
        status = client.get_status()

        assert 'mode' in status
        assert 'armed' in status
        assert 'system_status' in status


class TestMAVLinkClientCommands:
    """Test command methods."""

    def test_arm_without_connection(self):
        """Test arm fails gracefully without connection."""
        client = MAVLinkClient()
        assert client.arm() is False

    def test_disarm_without_connection(self):
        """Test disarm fails gracefully without connection."""
        client = MAVLinkClient()
        assert client.disarm() is False

    def test_set_mode_without_connection(self):
        """Test set_mode fails gracefully without connection."""
        client = MAVLinkClient()
        assert client.set_mode('GUIDED') is False

    def test_takeoff_without_connection(self):
        """Test takeoff fails gracefully without connection."""
        client = MAVLinkClient()
        assert client.takeoff(10) is False

    def test_land_without_connection(self):
        """Test land fails gracefully without connection."""
        client = MAVLinkClient()
        assert client.land() is False


class TestMAVLinkClientMission:
    """Test mission management."""

    def test_get_mission_without_connection(self):
        """Test get_mission returns empty list without connection."""
        client = MAVLinkClient()
        mission = client.get_mission()
        assert mission == []

    def test_upload_mission_without_connection(self):
        """Test upload_mission fails without connection."""
        client = MAVLinkClient()
        waypoints = [{'lat': 0, 'lon': 0, 'alt': 10}]
        assert client.upload_mission(waypoints) is False

    def test_clear_mission_without_connection(self):
        """Test clear_mission fails without connection."""
        client = MAVLinkClient()
        assert client.clear_mission() is False


@pytest.mark.skipif(
    os.environ.get('SITL_RUNNING') != '1',
    reason='SITL not running (set SITL_RUNNING=1 to enable)'
)
class TestMAVLinkClientIntegration:
    """Integration tests requiring SITL."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Set up connected client for each test."""
        self.client = MAVLinkClient()
        connected = self.client.connect()
        assert connected, "Failed to connect to SITL"
        yield
        self.client.disconnect()

    def test_get_telemetry_live(self):
        """Test telemetry retrieval from live SITL."""
        import time
        time.sleep(2)  # Wait for telemetry to populate
        telemetry = self.client.get_telemetry()
        # Position should have non-zero values if SITL is initialized
        assert isinstance(telemetry['attitude']['roll'], (int, float))

    def test_get_status_live(self):
        """Test status retrieval from live SITL."""
        import time
        time.sleep(1)
        status = self.client.get_status()
        assert status['mode'] in ['STABILIZE', 'MANUAL', 'GUIDED', 'AUTO', 'LOITER', 'UNKNOWN']
        assert isinstance(status['armed'], bool)

    def test_set_mode_guided(self):
        """Test setting mode to GUIDED."""
        result = self.client.set_mode('GUIDED')
        # May fail if pre-arm checks not met, but shouldn't raise
        assert isinstance(result, bool)
