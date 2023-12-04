import os
import sys
import csv
import requests
import urllib
from datetime import datetime, timedelta

MAX_REQUEST_SIZE_HOURS = 48
SECONDS_IN_HOUR = 3600.0
VOLTUS_API_URL = os.getenv("VOLTUS_API_URL", "https://api.voltus.co")
VOLTUS_API_KEY = os.getenv("VOLTUS_API_KEY")

s = requests.Session()
s.headers.update({"X-Voltus-API-Key": VOLTUS_API_KEY, "Accept": "application/json"})


def _get_telemetry(site_id: str, start_time: datetime, end_time: datetime):
    """
    returns a list of telemetry readings, each one being represented as a dictionary with the following fields:
    {
        "site_id": "aSiteID",
        "meter_id": "aMeterID",
        "interval_seconds": 30,
        "timestamp": "1970-01-01T00:00:00Z",
        "value": 10,
        "units": "kw"
    }
    """
    if start_time > end_time:
        raise Exception("end time cannot be before start time")

    readings = []  # will contain all telemetry readings

    current_start = start_time
    while current_start != end_time:
        # compute end_time for request in this loop
        current_end = end_time
        interval = end_time - current_start
        if interval.total_seconds() / SECONDS_IN_HOUR > MAX_REQUEST_SIZE_HOURS:
            current_end = current_start + timedelta(hours=MAX_REQUEST_SIZE_HOURS)

        # make request
        path_params = {
            "start_time": current_start.replace(microsecond=0).isoformat() + "Z",
            "end_time": current_end.replace(microsecond=0).isoformat() + "Z",
            "site_id": site_id,
            "interval_seconds": 30,
        }

        url = urllib.parse.urljoin(VOLTUS_API_URL, "/2022-04-15/telemetry/kw")
        resp = s.get(url, params=path_params)
        resp.raise_for_status()  # raise an exception if request fails

        json = resp.json()

        for site in json["data"]["sites"]:
            site_id = site["site_id"]
            for meter in site["meters"]:
                meter_id = meter["meter_id"]
                for reading in meter["telemetry"]:
                    reading["site_id"] = site_id
                    reading["meter_id"] = meter_id
                    readings.append(reading)

        # setup next iteration
        current_start = current_end

    return readings


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write(f"USAGE: {os.path.basename(sys.argv[0])} <site id>\n")
        sys.exit(1)
    if VOLTUS_API_KEY is None:
        sys.stderr.write("VOLTUS_API_KEY environment variable is unset")
        sys.exit(1)

    start_time = datetime.utcnow() - timedelta(days=8)
    end_time = datetime.utcnow() - timedelta(days=1)
    site_id = sys.argv[1]

    readings = _get_telemetry(site_id, start_time, end_time)

    # write readings to csv
    with open("readings.csv", "w") as csvfile:
        fieldnames = [
            "site_id",
            "meter_id",
            "interval_seconds",
            "timestamp",
            "value",
            "units",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for reading in readings:
            writer.writerow(reading)
