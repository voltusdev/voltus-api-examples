import json
import os
import urllib
import datetime
from typing import Dict

import requests
from dateutil import parser as date_parser
from flask import Flask, request

VOLTUS_API_URL = os.getenv("VOLTUS_API_URL", "https://api.voltus.co")
VOLTUS_API_KEY = os.getenv("VOLTUS_API_KEY", "secret")


app = Flask(__name__)

requests_session = requests.Session()
requests_session.headers.update(
    {"X-Voltus-API-Key": VOLTUS_API_KEY, "Accept": "application/json"}
)


def get_dispatch_info(url: str):
    url = urllib.parse.urljoin(VOLTUS_API_URL, url)
    r = requests_session.get(url)
    r.raise_for_status()  # raise an exception if request fails
    return r.json()


def dispatch_program(command: str, dispatch_info: Dict):
    ## TODO - shares function with all docs
    dispatch_info["start_time"] = date_parser.parse(dispatch_info["start_time"])
    if "end_time" in dispatch_info and dispatch_info["end_time"] is not None:
        dispatch_info["end_time"] = date_parser.parse(dispatch_info["end_time"])
    else:
        dispatch_info["end_time"] = None

    if command == "dispatch.create":
        return create_dispatch(dispatch_info)
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        if (
            (dispatch_info.get("end_time") and dispatch_info["end_time"] < now)
            or not dispatch_info["authorized"]
        ):
            return cancel_dispatch(dispatch_info)
        else:
            return update_dispatch(dispatch_info)


def create_dispatch(dispatch_info):
    # TODO: Fill in with your company-specific logic
    #       Remember that this could get called twice if the first time you return a non-200 response
    #       Remember that end_time could be None
    #       sites could have one sites, many sites, or all of your sites
    return (
        "Dispatch with ID {} starting at {} and ending at {} for sites {} created".format(
            dispatch_info["id"],
            dispatch_info["start_time"],
            dispatch_info["end_time"],
            dispatch_info["sites"],
        ),
        200,
    )


def update_dispatch(dispatch_info):
    # TODO: Fill in with your company-specific logic
    #       start_time and end_time can change to be earlier or later
    #       Remember that this could get called twice if the first time you return a non-200 response, so it's possible that the dispatch is already up-to-date
    return (
        "Dispatch with ID {} starting at {} and ending at {} for sites {} updated".format(
            dispatch_info["id"],
            dispatch_info["start_time"],
            dispatch_info["end_time"],
            dispatch_info["sites"],
        ),
        200,
    )


def cancel_dispatch(dispatch_info):
    # TODO: Fill in with your company-specific logic to cancel this dispatch, likely by ID
    #       Remember that this could get called twice if the first time you return a non-200 response, so it's possible that the dispatch is already cancelled
    return "Dispatch with ID {} cancelled".format(dispatch_info["id"]), 200


@app.post("/dispatch-listener")
def dispatch_listener():
    webhook_info = json.loads(request.data)
    if webhook_info["event"]["name"] == "" and webhook_info["resource"] == "":
        return "Hello webhook!", 200
    dispatch_info = get_dispatch_info(webhook_info["resource"])
    return dispatch_program(webhook_info["event"]["name"], dispatch_info)


if __name__ == "__main__":
    app.run()
