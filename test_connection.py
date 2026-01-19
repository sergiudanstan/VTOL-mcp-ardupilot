#!/usr/bin/env python3
"""Test script to verify ArduPilot SITL connection."""

import time
from mavlink_client import MAVLinkClient


def main():
    print("ArduPilot SITL Connection Test")
    print("=" * 40)

    client = MAVLinkClient()
    print(f"Connecting to: {client.connection_string}")

    if not client.connect():
        print("FAILED: Could not connect to SITL")
        print("\nMake sure ArduPilot SITL is running:")
        print("  sim_vehicle.py -v ArduCopter --console --map")
        return

    print("SUCCESS: Connected to ArduPilot SITL")
    print()

    # Wait for telemetry to populate
    time.sleep(2)

    # Get status
    print("Vehicle Status:")
    print("-" * 40)
    status = client.get_status()
    print(f"  Mode:   {status['mode']}")
    print(f"  Armed:  {status['armed']}")
    print()

    # Get telemetry
    print("Telemetry:")
    print("-" * 40)
    telemetry = client.get_telemetry()

    print("  Attitude:")
    print(f"    Roll:  {telemetry['attitude']['roll']:.2f} rad")
    print(f"    Pitch: {telemetry['attitude']['pitch']:.2f} rad")
    print(f"    Yaw:   {telemetry['attitude']['yaw']:.2f} rad")

    print("  Position:")
    print(f"    Lat: {telemetry['position']['lat']:.6f}")
    print(f"    Lon: {telemetry['position']['lon']:.6f}")
    print(f"    Alt: {telemetry['position']['alt']:.1f} m")

    print("  Velocity:")
    print(f"    Airspeed:    {telemetry['velocity']['airspeed']:.1f} m/s")
    print(f"    Groundspeed: {telemetry['velocity']['groundspeed']:.1f} m/s")

    print("  Battery:")
    print(f"    Voltage:   {telemetry['battery']['voltage']:.1f} V")
    print(f"    Remaining: {telemetry['battery']['remaining']}%")
    print()

    # Get mission
    print("Mission:")
    print("-" * 40)
    mission = client.get_mission()
    print(f"  Waypoints: {len(mission)}")
    for wp in mission[:5]:  # Show first 5
        print(f"    [{wp['seq']}] lat={wp['lat']:.6f}, lon={wp['lon']:.6f}, alt={wp['alt']:.1f}")
    if len(mission) > 5:
        print(f"    ... and {len(mission) - 5} more")
    print()

    print("Connection test complete.")
    client.disconnect()


if __name__ == "__main__":
    main()
