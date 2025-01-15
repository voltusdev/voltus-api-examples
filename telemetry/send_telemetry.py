import dataclasses
import os
import sys
from typing import List, Union

import requests


VOLTUS_API_URL = os.getenv("VOLTUS_API_URL", "https://api.voltus.co/2022-04-15")
VOLTUS_API_KEY = os.getenv("VOLTUS_API_KEY")

s = requests.Session()
s.headers.update({"X-Voltus-API-Key": VOLTUS_API_KEY, "Accept": "application/json"})

@dataclasses.dataclass
class TelemetryReading:
    interval_seconds: int
    meter_id: str
    timestamp: str
    units: str
    value: float

@dataclasses.dataclass
class ControllableLoadReading:
    interval_seconds: int
    site_id: str
    timestamp: str
    units: str
    value: float

def _send_telemetry(url: str, datatype: str, readings: Union[List[TelemetryReading], List[ControllableLoadReading]]):
    try:
        r = s.post(url, json={
            datatype: [dataclasses.asdict(reading) for reading in readings]
        })
        if r.status_code != 200:
            sys.stderr.write(f"Failed to send telemetry: {r.text}\n")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Failed to send telemetry: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 7:
        sys.stderr.write("Usage: python send_telemetry.py <telemetry_type> <interval_seconds> <meter_or_site_id> <timestamp> <units> <value>")
        sys.exit(1)

    if VOLTUS_API_KEY is None:
        sys.stderr.write("VOLTUS_API_KEY environment variable is unset\n")
        sys.exit(1)

    telemetry_type = sys.argv[1]
    reading_class = None
    if telemetry_type == "telemetry":
        url = f"{VOLTUS_API_URL}/telemetry"
        reading_class = TelemetryReading
    elif telemetry_type == "controllable_load":
        url = f"{VOLTUS_API_URL}/telemetry/controllable-load"
        reading_class = ControllableLoadReading
    else:
        sys.stderr.write("Invalid telemetry type. Must be 'telemetry' or 'controllable_load'\n")
        sys.exit(1)

    # Create a telemetry reading object
    reading = reading_class(
        int(sys.argv[2]), # interval seconds
        sys.argv[3], # site or meter id
        timestamp=sys.argv[4], 
        units=sys.argv[5], 
        value=float(sys.argv[6]) 
    )

    # Attempt to send it
    _send_telemetry(url, telemetry_type, [reading])
