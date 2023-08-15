"""
Simplified polling processor which gets dispatches then waits to see if they're in progress
"""

import datetime
import os
import time

import requests
import urllib
from dateutil import parser as date_parser


VOLTUS_API_URL = os.getenv("VOLTUS_API_URL", "https://api.voltus.co")
VOLTUS_API_KEY = os.getenv("VOLTUS_API_KEY", "secret")

processed_dispatches = set()

s = requests.Session()
s.headers.update({"X-Voltus-API-Key": VOLTUS_API_KEY, "Accept": "application/json"})

url = urllib.parse.urljoin(VOLTUS_API_URL, "/2022-04-15/dispatches")
resp = s.get(url)
dispatches = resp.json()["dispatches"]


if __name__ == "__main__":
    while True:
        for dispatch_info in dispatches:
            if dispatch_info["id"] in processed_dispatches:
                continue
            start_time = date_parser.parse(dispatch_info["start_time"])
            end_time = (
                date_parser.parse(dispatch_info["end_time"])
                if dispatch_info.get("end_time")
                else None
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            if start_time <= now:
                if end_time is None or end_time >= now:
                    processed_dispatches.add(dispatch_info["id"])
                    print("Dispatch {} is in progress".format(dispatch_info["id"]))
                    if dispatch_info["authorized"] and not dispatch_info.get(
                        "cancelled"
                    ):
                        for site in dispatch_info["sites"]:
                            print(
                                "- Customer location {} should drop by {}".format(
                                    site["customer_location_id"], site["drop_by"]
                                )
                            )
                    else:
                        print("- Dispatch is not authorized or is cancelled, skipping")
                else:
                    print("Dispatch {} has ended".format(dispatch_info["id"]))

        time.sleep(1)
