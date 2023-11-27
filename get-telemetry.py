import os
import csv
import requests
import urllib
from datetime import datetime, timedelta

MAX_REQUEST_SIZE_HOURS = 48
SECONDS_IN_HOUR = 3600.0
VOLTUS_API_URL = os.getenv("VOLTUS_API_URL", "https://api.voltus.co")
VOLTUS_API_KEY = os.getenv("VOLTUS_API_KEY", "secret")
SITE_ID = os.getenv("SITE_ID")

s = requests.Session()
s.headers.update({"X-Voltus-API-Key": VOLTUS_API_KEY, "Accept": "application/json"})


def compute_current_end_time(current_start_time, end_time):
    """
    helper function for get_telemetry.
    """
    interval = end_time - current_start_time
    if interval.total_seconds() / SECONDS_IN_HOUR > MAX_REQUEST_SIZE_HOURS:
        return current_start_time + timedelta(hours=MAX_REQUEST_SIZE_HOURS)
    else:
        return end_time


def get_telemetry(site_id, start_time, end_time):
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
        current_end = compute_current_end_time(current_start, end_time)

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
    if SITE_ID is None:
        raise Exception("SITE_ID environment variable is unset")
    if VOLTUS_API_KEY is None:
        raise Exception("VOLTUS_API_KEY environment variable is unset")

    start_time = datetime.utcnow() - timedelta(days=8)
    end_time = datetime.utcnow() - timedelta(days=1)

    readings = get_telemetry(SITE_ID, start_time, end_time)

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
