import datetime
import requests
import time
import urllib
from typing import Optional

from dateutil import parser as date_parser

VOLTUS_API_URL = "https://sandbox.voltus.co"
VOLTUS_TEST_API_KEY = "secret"


def _send_dispatch_signal(customer_location_id: str, drop_by: Optional[int]):
    print(f"Sending dispatch signal to drop by {drop_by} to {customer_location_id}")


s = requests.Session()
s.headers.update(
    {"X-Voltus-API-Key": VOLTUS_TEST_API_KEY, "Accept": "application/json"}
)

url = urllib.parse.urljoin(VOLTUS_API_URL, "/2022-04-15/dispatches")
resp = s.get(url)
dispatches = resp.json()

# wait 10 seconds, then process the dispatches
time.sleep(10)
for dispatch in dispatches["dispatches"]:
    start_time = date_parser.parse(dispatch["start_time"])
    end_time = date_parser.parse(dispatch["end_time"])
    now = datetime.datetime.now(datetime.timezone.utc)
    if start_time <= now and end_time >= now:
        print("Dispatch is in progress")
        for site in dispatch["sites"]:
            _send_dispatch_signal(site["customer_location_id"], site["drop_by"])
