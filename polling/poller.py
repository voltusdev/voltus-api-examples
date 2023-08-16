"""
Skeleton program which continually polls for new dispatches
"""

import os
import urllib
import datetime
import time
from typing import Dict

import requests
from dateutil import parser as date_parser


VOLTUS_API_URL = os.getenv("VOLTUS_API_URL", "https://api.voltus.co")
VOLTUS_API_KEY = os.getenv("VOLTUS_API_KEY", "secret")
POLLING_INTERVAL_SECONDS = 30

s = requests.Session()
s.headers.update({"X-Voltus-API-Key": VOLTUS_API_KEY, "Accept": "application/json"})
managed_dispatches: Dict[str, Dict] = {}  # dispatch id -> dispatch info
cancelled_dispatches = set()


def create_dispatch(dispatch_info: Dict):
    # TODO: Fill in with your company-specific logic
    #       Remember that this could get called twice if the service gets restarted
    #       Remember that end_time could be None
    #       sites could have one sites, many sites, or all of your sites
    print(
        "Dispatch with ID {} starting at {} and ending at {} for sites {} created".format(
            dispatch_info["id"],
            dispatch_info["start_time"],
            dispatch_info.get("end_time", "not specified"),
            dispatch_info["sites"],
        )
    )


def update_dispatch(dispatch_info: Dict):
    # TODO: Fill in with your company-specific logic
    #       start_time and end_time can change to be earlier or later
    #       Remember that this could get called twice if the service is restarted or the request otherwise fails
    print(
        "Dispatch with ID {} starting at {} and ending at {} for sites {} updated".format(
            dispatch_info["id"],
            dispatch_info["start_time"],
            dispatch_info.get("end_time", "not specified"),
            dispatch_info["sites"],
        )
    )


def cancel_dispatch(dispatch_info: Dict):
    # TODO: Fill in with your company-specific logic to cancel this dispatch, likely by ID
    #       Remember that this could get called twice if the service is restarted
    print("Dispatch with ID {} cancelled".format(dispatch_info["id"]))


if __name__ == "__main__":
    while True:
        start_time = datetime.datetime.now(datetime.timezone.utc)

        url = urllib.parse.urljoin(VOLTUS_API_URL, "/2022-04-15/dispatches")
        resp = s.get(url)
        resp.raise_for_status()  # raise an exception if request fails
        dispatches = resp.json()
        for dispatch_info in dispatches["dispatches"]:
            # convert start/end time to proper datetime
            dispatch_info["start_time"] = date_parser.parse(dispatch_info["start_time"])
            if "end_time" in dispatch_info and dispatch_info["end_time"] is not None:
                dispatch_info["end_time"] = date_parser.parse(dispatch_info["end_time"])
            else:
                dispatch_info["end_time"] = None

            dispatch_id = dispatch_info["id"]
            now = datetime.datetime.now(datetime.timezone.utc)

            # if we've already cancelled this dispatch, skip it
            if dispatch_id in cancelled_dispatches:
                continue

            # send a cancelled message if the dispatch is over or not authorized
            # regardless of whether we know about it or not (to protect against
            # this service restarting or similar), as long as it has not been
            # previously marked as cancelled
            if (
                dispatch_info.get("end_time") and dispatch_info["end_time"] < now
            ) or not dispatch_info["authorized"]:
                cancel_dispatch(dispatch_info)
                cancelled_dispatches.add(dispatch_id)
                managed_dispatches.pop(dispatch_id, None)
            # if this dispatch hasn't been seen before, create it
            elif dispatch_id not in managed_dispatches:
                create_dispatch(dispatch_info)
                managed_dispatches[dispatch_id] = dispatch_info
            # otherwise, update it
            else:
                if managed_dispatches[dispatch_id] != dispatch_info:
                    update_dispatch(dispatch_info)
                    managed_dispatches[dispatch_id].update(dispatch_info)

        # sleep for 30 seconds minus however long it took to process the dispatches
        elapsed = datetime.datetime.now(datetime.timezone.utc) - start_time
        time.sleep(max(0, POLLING_INTERVAL_SECONDS - elapsed.total_seconds()))
