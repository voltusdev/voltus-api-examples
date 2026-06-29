# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair==6.2.2",
#     "marimo>=0.23.11",
#     "numpy==2.4.6",
#     "pandas==3.0.3",
#     "python-dateutil==2.9.0.post0",
#     "pytz==2026.2",
#     "requests==2.34.2",
# ]
# ///
import marimo

__generated_with = "0.23.11"
app = marimo.App(width="columns")

with app.setup(hide_code=True):
    import copy
    import json
    import textwrap
    import warnings
    from datetime import datetime, timedelta

    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    import pytz
    import requests
    from dateutil.tz import tzlocal

    warnings.filterwarnings("ignore", category=UserWarning)

    READABLE_TIME_FORMAT = "%I:%M %p"
    READABLE_TIME_FORMAT_SECONDS = "%I:%M:%S %p"
    TIME_FORMAT_12 = "%I:%M"

    def get_now_notification_time():
        return datetime.now().replace(second=0, microsecond=0)  # Round down by ~one minute

    def get_now_rounded_5min_notification_time():
        return pd.Timestamp(get_now_notification_time()).ceil("5min").to_pydatetime()

    def parse_timestamp(timestamp_str):
        return pd.to_datetime(timestamp_str).to_pydatetime().astimezone(None).replace(tzinfo=None)

    def to_readable_timestamp(timestamp):
        return timestamp.replace(tzinfo=tzlocal()).strftime("%Y-%m-%d %H:%M:%S")

    def to_readable_time(timestamp, seconds=True):
        if seconds or timestamp.second != 0:
            format = READABLE_TIME_FORMAT_SECONDS
        else:
            format = READABLE_TIME_FORMAT
        return timestamp.replace(tzinfo=tzlocal()).strftime(format)

    def datetime_to_json(timestamp):
        web_api_format = "%Y-%m-%dT%H:%M:%SZ"
        return timestamp.replace(tzinfo=tzlocal()).astimezone(pytz.utc).strftime(web_api_format)

    def datetime_to_json_local(timestamp):
        return timestamp.replace(tzinfo=tzlocal()).isoformat()

    def scenario_to_json_payload(scenario) -> str:
        if "production_payload" in scenario:
            payload = scenario["production_payload"]
        else:
            payload = {
                "name": scenario["name"],
                "scenario_type": "custom",
                "dispatches": scenario["dispatches"],
            }

            if scenario.get("setpoints_timeseries") is not None:
                payload["setpoints_timeseries"] = scenario["setpoints_timeseries"]

        # TODO (nit): Remove end_time if unspecified
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, object):
                if isinstance(object, datetime):
                    return datetime_to_json(object)

                return json.JSONEncoder.default(self, object)

        payload_str = json.dumps(payload, cls=DateTimeEncoder, indent=2)

        return payload_str

    def scenario_to_curl(scenario, url, headers, method):
        headers = "\n".join([f"--header '{key}: {val}'" for key, val in headers.items()])
        curl = f"""
    curl \
      --request {method} \
      --url {url} \
      {headers}
      --data '
    {scenario_to_json_payload(scenario)}
    '
    """
        return curl

    DISPLAY_SETPOINTS = False
    DEBUG_MODE = False
    DISPLAY_STATIC_TIME_OPTION = False

    MAX_LOAD = 1 * 1000.0
    BASELINE = MAX_LOAD
    default_setpoint = 0.5 * 1000.0 if DISPLAY_SETPOINTS else 0
    default_scenario_length = 20
    default_site_id = "kd1k"
    default_site_name = "My Site"
    default_site_customer_location_id = "example-location-id"
    default_api_key = "YOUR_SANDBOX_API_KEY"
    default_notification_time = datetime_to_json_local(get_now_notification_time())
    default_url = "https://sandbox.voltus.co/2022-04-15/scenarios"
    production_url = "https://api.voltus.co/2022-04-15/dispatches"
    production_api_key_placeholder = "YOUR_PRODUCTION_API_KEY"

    scenario_length_input = mo.ui.number(
        label="Dispatch Length (minutes)",
        value=default_scenario_length,
        full_width=True,
    )
    setpoint_input = mo.ui.number(label="Setpoint Value (kw)", value=default_setpoint, full_width=True)
    site_id_input = mo.ui.text(label="Site ID", value=default_site_id, full_width=True)
    site_name_input = mo.ui.text(label="Site Name", value=default_site_name, full_width=True)
    site_customer_location_id_input = mo.ui.text(
        label="Site Customer Location ID",
        value=default_site_customer_location_id,
        full_width=True,
    )

    notification_time_input = mo.ui.text(placeholder="2020-12-30T13:00:00Z", full_width=True)
    set_now_notification_time_button = mo.ui.run_button(label="Set Notification Time To Now")
    set_now_notification_time_rounded_button = mo.ui.run_button(label="Set Notification Time To Now (round up 5 min)")
    set_static_notification_time_button = mo.ui.run_button(label="Set Notification Time To Static")

    host_input = mo.ui.text(label="URL", value=default_url, full_width=True)
    key_input = mo.ui.text(label="API Key", value=default_api_key, full_width=False)


@app.cell(hide_code=True)
def _(inputs):
    mo.md(f"""
    <h1 style="margin-top: 0">Customization</h1>

    To customize test scenarios below, modify the following fields

    {inputs}
    """)
    return


@app.cell(hide_code=True)
def _(wait_until_loaded):
    mo.md(f"""
    #Step 1: Get a Sandbox Key

    Email your Voltus Account Manager or Project Engineer to get a Sandbox API key for use with `sandbox.voltus.co`. 

    Use this key in place of `{default_api_key}` in the example curl requests below.

    {wait_until_loaded()}
    """)
    return


@app.cell(hide_code=True)
def _(INTEGRATION_TESTS, display_scenarios, wait_until_loaded):
    mo.md(f"""
    # Step 2: Sandbox Integration Tests

    A dispatch scenario consists of one or more dispatches being created and updated on `sandbox.voltus.co`. For each integration test, you will create a dispatch scenario via the `POST scenario` endpoint, using the provided curl requests.

    For other uses of the sandbox environment that do not require a sandbox key see [Sandbox Public Credentials](https://api.voltus.co/docs/concepts/public-credentials).

    **Passing the tests**: You must monitor your systems to ensure they meet the passing criteria for each test. 
    Voltus will not be able to monitor the output of your system and whether it matches expectations. For step 4, you will provide the logs showing the outputs of these tests.

    **Tip**: When you POST a scenario, the previous scenario is overwritten. To "cancel" a scenario, create a new scenario with 'Notification Time' set a year in the past.


    {display_scenarios(INTEGRATION_TESTS)}

    {wait_until_loaded()}
    """)
    return


@app.cell(hide_code=True)
def _(CURTAILING_SCENARIOS, display_scenarios):
    mo.md(rf"""
    # Step 3: Sandbox Curtailing Test

    {display_scenarios(CURTAILING_SCENARIOS)}
    """)
    return


@app.cell(hide_code=True)
def _(wait_until_loaded):
    mo.md(f"""
    # Step 4: Get a Production Key

    Email your Voltus Account Manager or Project Engineer with the results from Step 1 (logs) and Step 2 (proof of energy drop). They will issue you a production API key.

    {wait_until_loaded()}
    """)
    return


@app.cell(hide_code=True)
def _(PRODUCTION_INTEGRATION_TEST, display_scenarios):
    mo.md(f"""
    # Step 5: Production Self-Scheduled Integration Test

    {display_scenarios(PRODUCTION_INTEGRATION_TEST, url=production_url, headers={"X-Voltus-API-Key": production_api_key_placeholder})}
    """)
    return


@app.cell(hide_code=True)
def _(DV, display_scenarios):
    mo.md(f"""
    # Step 6: Production Dispatch Verification (DV)

    {display_scenarios(DV, display_payload=False)}
    """)
    return


@app.cell(column=1, hide_code=True)
def define_scenarios():
    API_KEY = key_input.value
    METHOD = "POST"
    URL = f"{host_input.value}"
    HEADERS = {"X-Voltus-API-Key": API_KEY, "Content-Type": "application/json"}

    NO_LOAD_COMMITMENT = BASELINE
    NO_LOAD = 0

    LOAD = setpoint_input.value
    COMMITMENT = BASELINE - LOAD

    HALF_COMMITMENT = BASELINE * 0.5
    HALF_LOAD = BASELINE - HALF_COMMITMENT

    NEGATIVE_LOAD_COMMITMENT = BASELINE * 1.1
    NEGATIVE_LOAD_SETPOINT = BASELINE - NEGATIVE_LOAD_COMMITMENT

    # In practice this is 24 hours (24*60), but shortening for readability
    UNKNOWN_END_TIME_SETPOINTS_DURATION_MINUTES = 90

    scenario_length = scenario_length_input.value
    setpoint_delay_minutes = 0.5

    PROGRAM = {
        "name": "A Program",
        "id": 5555,
        "timezone": "US/Pacific",
        "market": "CAISO",
        "program_type": "capacity",
    }

    ANCILLARY_PROGRAM = {
        "name": "A Different Program",
        "id": 1111,
        "timezone": "US/Pacific",
        "market": "CAISO",
        "program_type": "ancillary_services",
    }

    if notification_time_input.value:
        NOTIFICATION_TIME = parse_timestamp(notification_time_input.value)
    else:
        NOTIFICATION_TIME = parse_timestamp(default_notification_time)
    if set_now_notification_time_button.value:
        NOTIFICATION_TIME = get_now_notification_time()
    if set_static_notification_time_button.value:
        NOTIFICATION_TIME = datetime(2020, 12, 1, 12, 0, 0, tzinfo=pytz.utc).astimezone(None).replace(tzinfo=None)
    if set_now_notification_time_rounded_button.value:
        NOTIFICATION_TIME = get_now_rounded_5min_notification_time()

    SITE = {
        "id": site_id_input.value,
        "name": site_name_input.value,
        "customer_location_id": site_customer_location_id_input.value,
        "commitment": COMMITMENT,
    }

    inputs = mo.vstack(
        [
            mo.hstack(
                [scenario_length_input, ""],
                justify="start",
            ),
            mo.vstack(
                [
                    f"Notification Time: {to_readable_time(NOTIFICATION_TIME, seconds=False)} local ({datetime_to_json_local(NOTIFICATION_TIME)})",
                    mo.hstack(
                        [
                            notification_time_input,
                            set_now_notification_time_button,
                            set_now_notification_time_rounded_button,
                        ],
                        justify="start",
                        wrap=True,
                    ),
                ]
            ),
            mo.hstack(
                [site_id_input, site_name_input, site_customer_location_id_input, ""],
                justify="start",
            ),
            *([setpoint_input] if DISPLAY_SETPOINTS else []),
            *((host_input, key_input) if DEBUG_MODE else []),
        ],
        gap=1,
    )

    def sites_with_commitment(commitment):
        return [
            {
                "id": SITE["id"],
                "name": SITE["name"],
                "customer_location_id": SITE["customer_location_id"],
                "commitment": commitment,
            }
        ]

    def get_dispatch_state(
        published_time,
        creation_time,
        start_time,
        end_time,
        sites=None,
        program=PROGRAM,
        modification_number=0,
        authorized=True,
        test=False,
        metadata=None,
    ):
        if sites is None:
            sites = sites_with_commitment(COMMITMENT)
        dispatch_state = {
            "published_time": published_time,
            "dispatch": {
                "authorized": authorized,
                "test": test,
                "creation_time": creation_time,
                "start_time": start_time,
                "end_time": end_time,
                "modification_number": modification_number,
                "sites": sites,
                "program": program,
            },
        }

        if metadata is not None:
            dispatch_state["dispatch"]["metadata"] = metadata

        if dispatch_state["dispatch"]["end_time"] is None:
            del dispatch_state["dispatch"]["end_time"]
        return dispatch_state

    def get_basic_dispatch_states(dispatch_duration, commitment, start=NOTIFICATION_TIME, **kwargs):
        return [
            get_dispatch_state(
                published_time=start,
                creation_time=start,
                start_time=start,
                end_time=start + timedelta(minutes=dispatch_duration),
                sites=sites_with_commitment(commitment),
                **kwargs,
            )
        ]

    def get_ancillary_dispatch_states(
        dispatch_duration,
        commitment=COMMITMENT,
        start=NOTIFICATION_TIME,
        sites=None,
        **kwargs,
    ):
        if sites is None:
            sites = sites_with_commitment(commitment)
        dispatch_no_end = get_dispatch_state(
            published_time=start,
            creation_time=start,
            start_time=start,
            end_time=None,
            sites=sites,
            modification_number=0,
            **kwargs,
        )
        dispatch_with_end = copy.deepcopy(dispatch_no_end)
        end_time = start + timedelta(minutes=dispatch_duration)
        dispatch_with_end["published_time"] = end_time
        dispatch_with_end["dispatch"]["end_time"] = end_time
        dispatch_with_end["dispatch"]["modification_number"] = 1
        return [dispatch_no_end, dispatch_with_end]

    def get_dispatches_basic(dispatch_duration, commitment=COMMITMENT, start_offset_minutes=0):
        start = NOTIFICATION_TIME + timedelta(minutes=start_offset_minutes)
        return {"Dispatch": {"states": get_basic_dispatch_states(dispatch_duration, commitment, start=start)}}

    def get_dispatches_ancillary(dispatch_duration=10, commitment=COMMITMENT, **kwargs):
        return {"Dispatch": {"states": get_ancillary_dispatch_states(dispatch_duration, commitment, **kwargs)}}

    def get_dispatches_two(
        dispatch_duration,
        minutes_between_dispatches,
        commitment_1=COMMITMENT,
        commitment_2=COMMITMENT,
        ancillary=True,
        dispatch_duration_2=None,
        program_1=PROGRAM,
        program_2=ANCILLARY_PROGRAM,
    ):
        dispatch_1_start = NOTIFICATION_TIME
        dispatch_2_start = dispatch_1_start + timedelta(minutes=dispatch_duration + minutes_between_dispatches)
        if dispatch_duration_2 is None:
            dispatch_duration_2 = dispatch_duration
        if ancillary:
            return {
                "Dispatch 1": {
                    "states": get_ancillary_dispatch_states(
                        dispatch_duration,
                        commitment_1,
                        dispatch_1_start,
                        program=program_1,
                    )
                },
                "Dispatch 2": {
                    "states": get_ancillary_dispatch_states(
                        dispatch_duration_2,
                        commitment_2,
                        dispatch_2_start,
                        program=program_2,
                    )
                },
            }
        else:
            return {
                "Dispatch 1": {
                    "states": get_basic_dispatch_states(
                        dispatch_duration,
                        commitment_1,
                        dispatch_1_start,
                        program=program_1,
                    )
                },
                "Dispatch 2": {
                    "states": get_basic_dispatch_states(
                        dispatch_duration_2,
                        commitment_2,
                        dispatch_2_start,
                        program=program_2,
                    )
                },
            }

    def get_setpoints(first_timestamp, duration, value):
        setpoints = []
        current_time = first_timestamp
        increments = 1
        n_intervals = int(duration)
        for _ in range(0, n_intervals):
            setpoints.append(
                {
                    "timestamp": current_time,
                    "interval_seconds": 60,
                    "units": "kW",
                    "value": round(value, 3),
                }
            )
            current_time += timedelta(minutes=increments)
        return setpoints

    def generate_setpoints_timeseries(
        config,
        padding_until_offset=None,  ## Time that we no longer generate a bunch of trailing setpoints
        padding_total_minutes=UNKNOWN_END_TIME_SETPOINTS_DURATION_MINUTES,
    ):
        if len(config) == 0:
            return []

        notification_time = NOTIFICATION_TIME
        negative_infinity_time = datetime.min
        padding_until = NOTIFICATION_TIME + timedelta(minutes=padding_until_offset) if padding_until_offset is not None else negative_infinity_time

        timeseries_list = []
        duration_so_far = 0
        accumulated_setpoints = []
        current_time = notification_time + timedelta(minutes=1)  # Add one minute for interval-end
        for ts_config in config:
            published_time = notification_time + timedelta(minutes=duration_so_far)
            if ts_config.get("published_offset_minutes"):
                published_time = notification_time + timedelta(minutes=ts_config.get("published_offset_minutes"))
            if ts_config.get("timestamp_offset_minutes") is not None:
                current_time = notification_time + timedelta(minutes=1 + ts_config.get("timestamp_offset_minutes"))
                duration_so_far = 0
            duration = ts_config["duration_minutes"]
            if duration == 0:
                continue
            duration_so_far += duration
            value = ts_config["value"]
            these_setpoints = get_setpoints(current_time, duration, value)
            accumulated_setpoints += these_setpoints
            current_time += timedelta(minutes=duration)

            setpoints = accumulated_setpoints.copy()

            # Add setpoints if there's still padding
            if published_time < padding_until:
                setpoints += get_setpoints(
                    first_timestamp=current_time,
                    duration=padding_total_minutes - duration_so_far,
                    value=value,
                )

            timeseries_list.append(
                {
                    "site_id": SITE["id"],
                    "published_time": published_time,
                    "setpoints": setpoints,
                }
            )

        if published_time is not None and published_time < padding_until:
            timeseries_list.append(
                {
                    "site_id": SITE["id"],
                    "published_time": padding_until,
                    "setpoints": accumulated_setpoints,
                }
            )

        return timeseries_list

    def get_expected_load(load_config, expected_load_padding=2):
        for _ in range(expected_load_padding):  # add padding
            first_padding = (load_config[0][0] - 5, load_config[0][1])
            last_padding = (load_config[-1][0] + 5, load_config[-1][1])
            load_config = (
                [
                    first_padding,
                ]
                + load_config
                + [
                    last_padding,
                ]
            )

        expected_load = [
            {
                "time": NOTIFICATION_TIME + timedelta(minutes=time_offset),
                "value": value,
                "label": "Expected Power Use",
            }
            for time_offset, value in load_config
        ]

        return expected_load

    def get_expected_setpoints(setpoints_config: list[tuple[int, int]]):
        # setpoints_config = [(time_offset_minutes, kw_value)]
        expected_setpoints = [
            {
                "time": NOTIFICATION_TIME + timedelta(minutes=time_offset),
                "value": value,
                "label": "Expected Setpoints",
            }
            for time_offset, value in setpoints_config
        ]

        return expected_setpoints

    curtailing_test_length = max(scenario_length, 10)
    CURTAILING_SCENARIOS = [
        {
            "name": f"Sandbox Curtailing Test ({curtailing_test_length} min)",
            "description": """
                A sandbox dispatch that **fully curtails the site load**. 

                You will likely need to temporarily connect your production software integration to sandbox to complete this test.
                """,
            "dispatches": get_dispatches_ancillary(curtailing_test_length),
            "expected_result_description": "Site load should curtail fully. When complete, tell Voltus when you created the scenario and when the site power use dropped for Voltus to confirm you are ready for the next step.",
            "expected_result": get_expected_load(
                [
                    (0, MAX_LOAD),
                    (10, LOAD),
                    (curtailing_test_length, LOAD),
                    (curtailing_test_length + 10, MAX_LOAD),
                ]
            ),
        }
    ]
    if DISPLAY_SETPOINTS:
        # TODO (setpoints): This isn't right for the ramp up
        CURTAILING_SCENARIOS = [
            {
                "name": f"Custom Curtailing Test ({int(LOAD / 1000)} MW, {scenario_length} min)",
                "dispatches": get_dispatches_ancillary(scenario_length, COMMITMENT),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {
                            "value": LOAD,
                            "duration_minutes": scenario_length,
                        }
                    ],
                    padding_until_offset=scenario_length,
                ),
                "expected_result_description": "Site load should hit setpoint. When complete, tell Voltus when you created the scenario and when the site dropped for Voltus to confirm you are ready for the next step.",
                "expected_result": get_expected_load(
                    [(0, MAX_LOAD)] + [(i, LOAD) for i in np.linspace(10, scenario_length, int(scenario_length / 5) - 1)] + [(scenario_length + 10, MAX_LOAD)]
                ),
            }
        ]

    PRODUCTION_INTEGRATION_TEST = {
        "name": "Production Integration Test",
        "description": """
            A **production** test dispatch. 

            Created with the production `POST /dispatches` endpoint. 

            Dispatches created through this endpoint will have `test=true`. You should use the dispatch `test` field to distinguish between a Voltus-initiated dispatch and a dispatch created through this endpoint. 

            This creates an "Integration Test" dispatch in production. 
            This type of dispatch will not trigger any customer communications such as email, SMS, or phone calls.
            """,
        "expected_result_description": "Confirm you can see a dispatch in production with your production credentials. Send Voltus a screenshot of your service's logs showing the dispatch.",
        "create_test_description": """
            This creates a real dispatch in production. **Only run this if you are sure how your site will respond to a production dispatch from Voltus.**

            When you send the following request, a new dispatch will be created by Voltus in production. 

            The new dispatch will be returned in the response to `GET /dispatches`, and will also be available at its ID-specific path. 
            """,
        "dispatches": get_dispatches_basic(scenario_length),
        "production_payload": {
            "start_time": NOTIFICATION_TIME,
            "end_time": NOTIFICATION_TIME + timedelta(minutes=scenario_length),
        },
    }
    if DISPLAY_SETPOINTS:
        PRODUCTION_INTEGRATION_TEST["description"] += """
    NOTE: This does not create setpoints.
    """

    DV = {
        "name": "Production Dispatch Verification (DV)",
        "description": """Voltus-scheduled production dispatch verification.""",
        "dispatches": get_dispatches_basic(curtailing_test_length),
        "expected_result": get_expected_load(
            [
                (0, MAX_LOAD),
                (10, LOAD),
                (curtailing_test_length, LOAD),
                (curtailing_test_length + 10, MAX_LOAD),
            ]
        ),
        "create_test_description": """
            When you have passed all the above steps, coordinate with your Account Manager to schedule a Dispatch Verification dispatch in production. 
            """,
    }
    if DISPLAY_SETPOINTS:
        # TODO (setpoints): This isn't right for the ramp up
        # TODO (setpoints): This should show variations every 5-min
        dv_dispatch_1_duration = 30
        dv_dispatch_2_duration = 30
        dv_minutes_between_dispatches = 25
        dv_dispatch_2_start_offset = dv_dispatch_1_duration + dv_minutes_between_dispatches

        DV["dispatches"] = get_dispatches_two(
            dv_dispatch_1_duration,
            minutes_between_dispatches=dv_minutes_between_dispatches,
            commitment_1=COMMITMENT,
            commitment_2=NEGATIVE_LOAD_COMMITMENT,
            dispatch_duration_2=dv_dispatch_2_duration,
        )
        DV["setpoints_timeseries"] = generate_setpoints_timeseries(
            [
                {
                    "published_offset_minutes": setpoint_delay_minutes,
                    "value": LOAD,
                    "duration_minutes": dv_dispatch_1_duration,
                }
            ],
            padding_until_offset=dv_dispatch_1_duration + setpoint_delay_minutes,
        ) + generate_setpoints_timeseries(
            [
                {
                    "published_offset_minutes": setpoint_delay_minutes,
                    "value": LOAD,
                    "duration_minutes": dv_dispatch_1_duration,
                },
                {
                    "timestamp_offset_minutes": dv_dispatch_2_start_offset,
                    "published_offset_minutes": setpoint_delay_minutes + dv_dispatch_2_start_offset,
                    "value": NEGATIVE_LOAD_SETPOINT,
                    "duration_minutes": dv_dispatch_2_duration,
                },
            ],
            padding_until_offset=dv_dispatch_2_start_offset + dv_dispatch_2_duration + setpoint_delay_minutes,
        )
        DV["expected_result"] = get_expected_load(
            [(0, MAX_LOAD)]
            + [(i, LOAD) for i in np.linspace(10, scenario_length, int(scenario_length / 5) - 1)]
            + [(scenario_length + 10, MAX_LOAD)]  # TODO (setpoints): Add next dispatch
        )
        DV["create_test_description"] = """
            When you have passed all the above steps, coordinate with your Account Manager to schedule a Dispatch Verification in production. 
            Voltus engineers will simulate setpoints from the market.
            """
    return (
        API_KEY,
        COMMITMENT,
        CURTAILING_SCENARIOS,
        DV,
        HALF_COMMITMENT,
        HALF_LOAD,
        HEADERS,
        LOAD,
        METHOD,
        NOTIFICATION_TIME,
        NO_LOAD,
        NO_LOAD_COMMITMENT,
        PRODUCTION_INTEGRATION_TEST,
        SITE,
        URL,
        generate_setpoints_timeseries,
        get_dispatch_state,
        get_dispatches_ancillary,
        get_dispatches_basic,
        get_dispatches_two,
        get_setpoints,
        inputs,
        scenario_length,
        setpoint_delay_minutes,
        sites_with_commitment,
    )


@app.cell(hide_code=True)
def integration_tests(
    COMMITMENT,
    HALF_COMMITMENT,
    HALF_LOAD,
    LOAD,
    NOTIFICATION_TIME,
    NO_LOAD,
    NO_LOAD_COMMITMENT,
    SITE,
    generate_setpoints_timeseries,
    get_dispatch_state,
    get_dispatches_ancillary,
    get_dispatches_basic,
    get_dispatches_two,
    get_setpoints,
    scenario_length,
    setpoint_delay_minutes,
    sites_with_commitment,
):
    INTEGRATION_TESTS = [
        {
            "name": "Integration Test 1. Basic Dispatch",
            "description": """
            A basic dispatch. Start and end times will be provided immediately.

            API Behavior: At `published_time`, a dispatch will be issued that starts at `start_time` and has an end time of `end_time`.
        """,
            "expected_result_description": "Your client sends a signal to both sites to be fully curtailed in time for the start time and begins to ramp up after the end time is reached.",
            "dispatches": get_dispatches_basic(scenario_length),
        },
        {
            "name": "Integration Test 2. Ancillary Services Dispatch",
            "description": """
                A typical ancillary service dispatch, 
                where the end time is not initially provided and the start time is in the recent past.
                After ten minutes from the dispatch start time, 
                the end time will be added as an update to the dispatch to end the dispatch immediately.

                API Behavior:
                A dispatch that starts now will be created immediately.
                10 minutes later, a dispatch update will be issued that has an end time of now.

                This scenario also includes a sample `metadata` object to verify that your integration tolerates optional dispatch metadata. You can ignore this field unless Voltus tells you otherwise.
                """,
            "expected_result_description": """
                Your client immediately sends a signal to sites to curtail immediately.
                When the dispatch update arrives 10 minutes later, 
                your client sends a signal to the site to ramp up immediately.
                """,
            "dispatches": get_dispatches_ancillary(scenario_length, metadata={"sandbox": True}),
        },
        {
            "name": "Integration Test 3. Two Dispatches",
            "description": """
                Two ancillary services dispatches with some time in between.
                """,
            "expected_result_description": """
                Your client immediately sends a signal to both sites to curtail immediately.
                When the dispatch update arrives 10 minutes later, 
                your client sends a signal to the sites to ramp up immediately.

                Your client does the same thing for the second dispatch.
                """,
            "dispatches": get_dispatches_two(scenario_length, minutes_between_dispatches=5),
        },
        {
            "name": "Integration Test 4. Cancelled Dispatch",
            "description": "Dispatch that starts in the future, and is cancelled before it starts with `authorized=False`.",
            "expected_result_description": "Do not curtail the site",
            "dispatches": {
                "Dispatch": {
                    "states": [
                        get_dispatch_state(
                            published_time=NOTIFICATION_TIME,
                            creation_time=NOTIFICATION_TIME,
                            start_time=NOTIFICATION_TIME + timedelta(minutes=scenario_length),
                            end_time=NOTIFICATION_TIME + timedelta(minutes=scenario_length + scenario_length),
                            modification_number=0,
                        ),
                        get_dispatch_state(
                            published_time=NOTIFICATION_TIME + timedelta(minutes=scenario_length / 2),
                            creation_time=NOTIFICATION_TIME,
                            start_time=NOTIFICATION_TIME + timedelta(minutes=scenario_length),
                            end_time=NOTIFICATION_TIME + timedelta(minutes=scenario_length + scenario_length),
                            modification_number=1,
                            authorized=False,
                        ),
                    ]
                }
            },
        },
    ]

    if DISPLAY_SETPOINTS:
        INTEGRATION_TESTS = [
            # TODO (setpoints): Make the "Expected Behavior" have "expected setpoint" graphs for integration tests (not "expected load") - right now it's very confusing, especially in cases with fallback behavior expected
            # TODO (setpoints): Add a test that checks for extra setpoints before or after the dispatch, to deal with the case of 5 min rounding up and down at the end
            # TODO (setpoints): Add a test that checks for negative setpoints
            # TODO (setpoints): Add an error-checking test with setpoints for a non-abutting dispatch where the setpoints abutt, and confirm setpoints are left-inclusive and right-exclusive
            # TODO (setpoints): Remove duplicate tests
            # TODO (setpoints): Add a test with 5-minute updates
            # TODO (setpoints): there should be a way to download the expected outputs
            {
                "name": "Integration Test 1: Common: Briefly Missing Setpoints at Start",
                "likelihood": "Common - expected for some programs",
                "description": """Unavailable setpoints at dispatch start, but they appear within 1 minute. i.e. for the first 30 minutes, the setpoints endpoint returns an empty array.

            First setpoints returned are for 24 hours. 4 mins into dispatch, end_time is set to now. Within a minute, setpoints after end_time are removed.
            """,
                "expected_result_description": "Do nothing, then match setpoint when it arrives",
                "dispatches": get_dispatches_ancillary(4),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {
                            "value": NO_LOAD,
                            "duration_minutes": 2,
                            "published_offset_minutes": setpoint_delay_minutes,
                        },
                        {"value": HALF_LOAD, "duration_minutes": 2},
                    ],
                    padding_until_offset=4 + setpoint_delay_minutes,
                    padding_total_minutes=15,
                ),
            },
            {
                "name": "Integration Test 2: Common: No Setpoints at All",
                "likelihood": "Common - expected for some programs",
                "description": "No setpoints for the duration of dispatch.",
                "expected_result_description": "Execute commitment fallback by 5 minutes into dispatch: load minus commitment",
                "setpoints_timeseries": generate_setpoints_timeseries([]),
                "dispatches": get_dispatches_ancillary(10),
            },
            {
                "name": "Integration Test 3: Simplified: Single Dispatch",
                "likelihood": "Unlikely - simplified case for testing",
                "description": "Valid setpoints available immediately and throughout",
                "expected_result_description": "Match setpoints as scheduled",
                "dispatches": get_dispatches_basic(scenario_length),
                "setpoints_timeseries": generate_setpoints_timeseries([{"value": LOAD, "duration_minutes": scenario_length}]),
            },
            {
                "name": "Integration Test 4: Simplified: Single Dispatch In the Future",
                "likelihood": "Unlikely - simplified case for testing",
                "description": "Dispatch that starts some time in the future",
                "expected_result_description": "Match setpoints as scheduled",
                "dispatches": {
                    "Dispatch": {
                        "states": [
                            get_dispatch_state(
                                published_time=NOTIFICATION_TIME,
                                creation_time=NOTIFICATION_TIME,
                                start_time=NOTIFICATION_TIME + timedelta(minutes=10),
                                end_time=NOTIFICATION_TIME + timedelta(minutes=10 + scenario_length),
                                sites=sites_with_commitment(COMMITMENT),
                                modification_number=0,
                            )
                        ]
                    }
                },
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {
                            "value": LOAD,
                            "duration_minutes": scenario_length,
                            "timestamp_offset_minutes": 10,
                            "published_offset_minutes": setpoint_delay_minutes,
                        },
                    ]
                ),
            },
            {
                "name": "Integration Test 5: Simplified: Abutting Dispatches",
                "likelihood": "Unlikely - simplified case for testing",
                "description": """
                            Dispatch 1: Start_time is now and end time added at end time.

                            Dispatch 2: Start_time is the same as Dispatch 1 end_time.
                            """,
                "expected_result_description": "Maintain Dispatch #1's last known level until #2's setpoints arrive",
                "dispatches": get_dispatches_two(10, minutes_between_dispatches=0),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {"value": NO_LOAD, "duration_minutes": 10},
                        {
                            "value": HALF_LOAD,
                            "duration_minutes": 10,
                            "published_offset_minutes": 10,
                        },
                    ]
                ),
            },
            {
                "name": "Integration Test 6: Error handling: Missing Setpoints at Start (> 5 min)",
                "likelihood": "Unlikely - error handling",
                "description": "Unavailable setpoints at dispatch start, but they appear after 15 minutes",
                "expected_result_description": "Execute commitment fallback within 5 minutes. By minute 5, the site should be operating at 'load minus commitment'. Later, setpoint appears. Match setpoint on arrival",
                "dispatches": get_dispatches_basic(25),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {
                            "published_offset_minutes": 15,
                            "value": NO_LOAD,
                            "duration_minutes": 25,
                        },
                    ]
                ),
            },
            {
                "name": "Integration Test 7: Error Handling: Non-abutting dispatch",
                "description": "Dispatch #1 is a normal dispatch with setpoints available. After it ends, a non-abutting Dispatch #2 is created but no setpoints are available.",
                "expected_result_description": 'Treat dispatch #2 as "No Setpoints at All". Do NOT use the setpoint from Dispatch #1',
                "dispatches": get_dispatches_two(
                    5,
                    minutes_between_dispatches=3,
                    commitment_1=NO_LOAD_COMMITMENT,
                    commitment_2=HALF_COMMITMENT,
                ),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {"value": NO_LOAD, "duration_minutes": 5},
                    ]
                ),
            },
            {
                "name": "Integration Test 8: Error handling: Incomplete setpoints at start",
                "description": "Setpoints available at dispatch start, but first few intervals are missing. e.g. 5 minute dispatch with array of 3 setpoints covering the last 3 minutes",
                "expected_result_description": "Match first available setpoint, achieving the load drop at the dispatch start time",
                "dispatches": get_dispatches_basic(5),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {
                            "value": NO_LOAD,
                            "duration_minutes": 3,
                            "timestamp_offset_minutes": 2,
                        },
                    ],
                ),
            },
            {
                "name": "Integration Test 9: Error handling: Incomplete setpoints at end",
                "likelihood": "Unlikely - error handling",
                "description": "Setpoints available at dispatch start, but last few intervals are missing.",
                "expected_result_description": "Hold last available setpoint level until dispatch end time.",
                "dispatches": get_dispatches_ancillary(5),
                "setpoints_timeseries": generate_setpoints_timeseries(
                    [
                        {"value": NO_LOAD, "duration_minutes": 3},
                    ]
                ),
            },
            {
                "name": "Integration Test 10: Error handling: Missing Setpoints at End",
                "likelihood": "Unlikely - error handling",
                "description": "Complete setpoints at dispatch start, but setpoints disappear part-way through the dispatch and don't reappear.",
                "expected_result_description": "Hold last known setpoint until dispatch ends",
                "dispatches": get_dispatches_ancillary(5),
                "setpoints_timeseries": [
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME,
                        "setpoints": get_setpoints(NOTIFICATION_TIME + timedelta(minutes=1), 153, LOAD),
                    },
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME + timedelta(minutes=3),
                        "setpoints": [],
                    },
                ],
            },
            {
                "name": "Integration Test 11: Error handling: Intermittently available setpoints",
                "likelihood": "Unlikely - error handling",
                "description": "Complete setpoints at dispatch start, but setpoints disappear part-way through the dispatch, and reappear after a few minutes.",
                "expected_result_description": "Hold last known setpoint while setpoints are unavailable, pick up new setpoints when they reappear",
                "dispatches": get_dispatches_basic(10),
                "setpoints_timeseries": [
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME,
                        "setpoints": get_setpoints(NOTIFICATION_TIME + timedelta(minutes=1), 10, HALF_LOAD),
                    },
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME + timedelta(minutes=2),
                        "setpoints": [],
                    },
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME + timedelta(minutes=8),
                        "setpoints": get_setpoints(NOTIFICATION_TIME + timedelta(minutes=1), 5, HALF_LOAD) + get_setpoints(NOTIFICATION_TIME + timedelta(minutes=6), 5, NO_LOAD),
                    },
                ],
            },
            # TODO (setpoints): Are we sure this is what we want and not use commitment?
            {
                "name": "Integration Test 12: Error handling: Abutting Dispatches - Intermittently available setpoints",
                "likelihood": "Unlikely - error handling",
                "description": "Two abutting dispatches with setpoints. Setpoints become completely unavailable before Dispatch #1 ends, and become available after Dispatch #2 starts.",
                "expected_result_description": "Maintain Dispatch #1's last known level until #2's setpoints arrive",
                "dispatches": get_dispatches_two(
                    10,
                    minutes_between_dispatches=0,
                    commitment_1=COMMITMENT,
                    commitment_2=NO_LOAD_COMMITMENT,
                    ancillary=False,
                ),
                "setpoints_timeseries": [
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME,
                        "setpoints": get_setpoints(NOTIFICATION_TIME + timedelta(minutes=1), 10, LOAD),
                    },
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME + timedelta(minutes=4),
                        "setpoints": [],
                    },
                    {
                        "site_id": SITE["id"],
                        "published_time": NOTIFICATION_TIME + timedelta(minutes=15),
                        "setpoints": get_setpoints(NOTIFICATION_TIME, 10, HALF_LOAD) + get_setpoints(NOTIFICATION_TIME + timedelta(minutes=11), 10, NO_LOAD),
                    },
                ],
            },
        ]
    return (INTEGRATION_TESTS,)


@app.cell(hide_code=True)
def post_scenario_buttons(API_KEY, CURTAILING_SCENARIOS, INTEGRATION_TESTS):
    ALL_SCENARIOS = {scenario["name"]: scenario for scenario in INTEGRATION_TESTS + CURTAILING_SCENARIOS if DEBUG_MODE}
    post_scenario_buttonas_dict = {}
    disabled = API_KEY == "" or API_KEY == default_api_key
    disabled_warning = ": Enter an API Key First. "
    label = f"POST Scenario{disabled_warning if disabled else ' '}(Not available from marimo.app)"
    POST_SCENARIO_BUTTONS = mo.ui.dictionary({name: mo.ui.run_button(label=label, disabled=disabled) for name in ALL_SCENARIOS.keys()})
    return ALL_SCENARIOS, POST_SCENARIO_BUTTONS


@app.cell(hide_code=True)
def display_scenarios(
    ALL_SCENARIOS,
    HEADERS,
    METHOD,
    POST_SCENARIO_BUTTONS,
    URL,
):
    style = r"""
    <style>
        :root {
            --marimo-heading-font:  system-ui, Segoe UI, Roboto, sans-serif;
            --marimo-text-font:  system-ui, Segoe UI, Roboto, sans-serif;
            --marimo-monospace-font: SFMono-Regular, Menlo, Monaco, monospace;
            --font-weight-medium: normal;
        }
        h1 {
            margin-top: 1em;
            margin-bottom: 0.2em;
            font-weight: 700 !important;
        }
        .markdown h3 {
            margin-bottom: 0.2em !important;
            margin-top: 0.4em !important;
            padding-bottom: 0 !important;
        }
        .markdown .paragraph {
            margin-block: 0.2em 1em !important;
            padding-bottom: 0em;
            padding-right: 4em;
        }
        p.admonition-title {
            margin-block-end: 0;
        }
        pre {
            margin-top:0px !important;
            margin-bottom:0px !important;
            margin-block: 0px;
        }
        pre:not(.custom-code-block) {
            background-color: #f6f8fa;
        }
        .scroll-container pre {
            margin: 0 0 0 0 !important;
        }
        .scroll-container {
            overflow-y: scroll; 
            margin: 1rem 0;
        }
        summary {
            padding: 0.4rem !important;
        }
        .px-1 { 
            padding-inline: 0; /* Sets the padding of the marimo notebook to 0 so embedding doesn't have extra padding */
        }
        .sm\:pt-8 { 
            padding-top: 0 !important; /* so embedding doesn't have extra padding at the top */
        }
    </style>
    """
    POST_SCENARIO_RESPONSES = {}

    def send_request(name):
        scenario = ALL_SCENARIOS[name]
        scenario_str = scenario_to_json_payload(scenario)
        r = requests.Request(METHOD, url=URL, data=scenario_str, headers=HEADERS)
        req = r.prepare()
        response = requests.Session().send(req)
        try:
            response_text = f"{response.status_code}: {response.json()}"
        except:
            response_text = f"{response.status_code}: {response.text}"
        POST_SCENARIO_RESPONSES[name] = response_text
        return response_text

    for name, button in POST_SCENARIO_BUTTONS.items():
        if button.value:
            send_request(name)

    def qa_send_all_requests():
        for scenario in ALL_SCENARIOS:
            send_request(scenario)
        return POST_SCENARIO_RESPONSES

    # For internal QA on notebook only
    should_send_all_requests = False
    if should_send_all_requests:
        print(qa_send_all_requests())
    return POST_SCENARIO_RESPONSES, style


@app.cell(hide_code=True)
def _(
    HEADERS,
    METHOD,
    POST_SCENARIO_BUTTONS,
    POST_SCENARIO_RESPONSES,
    URL,
    get_charts,
    get_dispatch_annotations,
    style,
):
    def display_scenario(scenario, display_payload=True, url=URL, headers=HEADERS):
        description = scenario.get("description", "") + "\n\n"
        if scenario.get("likelihood"):
            description += f"**Likelihood**: {scenario['likelihood']}\n"

        time_details = ""
        _, annotations_by_time = get_dispatch_annotations(scenario)
        for time, labels in annotations_by_time.items():
            time_details += f"- {to_readable_time(time, seconds=True)}: {', '.join(labels)}\n"
        time_details = time_details[:-1]

        setpoints_charts, expected_load_chart = get_charts(scenario)

        create_test_description = textwrap.dedent(scenario.get("create_test_description", ""))
        if display_payload:
            post_scenario_response = POST_SCENARIO_RESPONSES.get(scenario["name"], "")
            if post_scenario_response:
                post_scenario_response = f"""Request response: {code_block(post_scenario_response)}\n\n"""

            curl = scenario_to_curl(scenario, url, headers, METHOD).replace("\n", " ")
            create_test_description += f"""
    {scrollable_code_block(curl, type="sh", height=250)}

    {POST_SCENARIO_BUTTONS.get(scenario["name"], "")}

    {post_scenario_response}
                    """

        if url != URL:
            create_test_description = wrap_warning(create_test_description)

        description = f"""{style}

    **Description**

    {textwrap.dedent(description)}


    /// details | Details

    {code_block_no_background(time_details)}

    {mo.as_html(setpoints_charts)}

    ///

    **Expected Result**

    {textwrap.dedent(scenario.get("expected_result_description", ""))}

    {mo.as_html(expected_load_chart) if expected_load_chart else ""}


    **Creating the Test**

    {create_test_description}

    """
        return description

    def display_scenarios(scenarios, display_payload=True, url=URL, headers=HEADERS):
        if isinstance(scenarios, dict):
            scenarios = [scenarios]

        scenarios_displayed = f"""

    {
            mo.accordion(
                {f"<h2 class='inline'>{scenario['name']}</h2>": make_text_black(display_scenario(scenario, display_payload, url, headers)) for scenario in scenarios},
                multiple=True,
            )
        }
        """
        return scenarios_displayed

    def code_block_no_background(md_string):
        return f"""<pre class='custom-code-block'>{md_string}</pre>"""

    def make_text_black(string):
        return f"""<div style="color: black">

    {str_to_md_to_html_text(string)}

    </div>
    """

    def wrap_warning(string):
        return f"""            
    /// attention | Warning

    {string}

    ///
    """

    def scrollable_block(string, height=200):
        return f"""<div class="scroll-container" style="max-height: {height}px">{str_to_md_to_html_text(string)}</div>"""

    def code_block(string, type="raw"):
        return f"""

    ```{type}
    {string}
    ```

    """

    def str_to_md_to_html_text(string):
        return mo.as_html(mo.md(string)).text

    def scrollable_code_block(string, type, height=200):
        # md.accordion removes the line breaks in code blocks. But we decided we like this more visually anyways.
        # If we change our minds, we can try `mo.md(f'{mo.md(block).text}')` from this ticket https://github.com/marimo-team/marimo/issues/6363
        return scrollable_block(code_block(string, type), height=height)

    def wait_until_loaded():
        return ""

    # Add the style here, so other cells render it
    mo.md(style)
    return display_scenarios, wait_until_loaded


@app.cell(hide_code=True)
def get_charts():
    def get_charts(scenario):
        """
        To pan graph: Press Cmd (Mac) or Ctrl (Windows) and drag

        To zoom graph: Press Cmd (Mac) or Ctrl (Windows) and scroll
        """
        all_dispatch_annotations, all_dispatch_annotations_by_time = get_dispatch_annotations(scenario, None)

        all_labels = list(all_dispatch_annotations["label"].unique()) + ["Current Time"]
        if scenario.get("setpoints_timeseries", None) is not None:
            all_labels.append("Setpoint Before Current Time")
            all_labels.append("Setpoint After Current Time")
        LIGHT_BLUE = "#6fd4f6"
        LIGHT_PURPLE = "#e272f3"
        LIGHT_GREEN = "#3d9715"
        ORANGE = "#ff9900"
        LIGHT_ORANGE = "#c07300"
        colorMap = {
            "Current Time": "black",
            "Setpoint Before Current Time": LIGHT_ORANGE,
            "Setpoint After Current Time": ORANGE,
            "Dispatch Start": LIGHT_BLUE,
            "Dispatch End": LIGHT_BLUE,
            "Dispatch 1 Start": LIGHT_BLUE,
            "Dispatch 1 End": LIGHT_BLUE,
            "Dispatch 2 Start": LIGHT_PURPLE,
            "Dispatch 2 End": LIGHT_PURPLE,
            "Expected Power Use": LIGHT_GREEN,
        }
        colorDomain = [label for label in colorMap.keys() if label in all_labels]
        colorRange = [colorMap[label] for label in colorDomain]

        # Find min and max kW and time
        min_time_minutes = 15
        all_values = [0, MAX_LOAD * 0.8, MAX_LOAD * 1.05]
        all_times = [
            min(all_dispatch_annotations_by_time.keys()) - timedelta(minutes=10),
            max(all_dispatch_annotations_by_time.keys()) + timedelta(minutes=10),
            min(all_dispatch_annotations_by_time.keys()) + timedelta(minutes=min_time_minutes),
        ]
        for ts in scenario.get("setpoints_timeseries", []):
            for sp in ts.get("setpoints", []):
                all_values.append(sp["value"])
                all_times.append(sp["timestamp"])
        for d in scenario.get("expected_result", []):
            all_values.append(d["value"])
            all_times.append(d["time"])
        y_min = min(all_values)
        y_max = max(all_values)
        time_min = min(all_times)
        time_max = max(all_times)
        y_padding = 0
        time_padding = 0

        min_width = 150
        max_width = 750
        max_time_minutes = 90
        scenario_length_minutes = (time_max - time_min).total_seconds() / 60
        width = int(
            np.interp(  # Interpolate width based on scenario length
                scenario_length_minutes,
                [min_time_minutes, max_time_minutes],
                [min_width, max_width],
            )
        )

        charts = []
        relevant_times = list(all_dispatch_annotations_by_time.keys())
        for current_time in relevant_times:
            setpoints = get_current_setpoints(current_time, scenario.get("setpoints_timeseries", []))
            dispatch_annotations, _ = get_dispatch_annotations(scenario, current_time)
            setpoint_data = pd.DataFrame(
                [{"time": sp["timestamp"], "value": sp["value"]} for sp in setpoints],
                columns=["time", "value"],
            )
            setpoint_data["label"] = setpoint_data["time"].apply(lambda time: "Setpoint Before Current Time" if time <= current_time else "Setpoint After Current Time")

            setpoints_chart = (
                alt.Chart(setpoint_data)
                .mark_circle(size=60, opacity=1)
                .encode(
                    x=alt.X(
                        "time:T",
                        title="",
                        axis=alt.Axis(format=TIME_FORMAT_12),
                        scale=alt.Scale(
                            padding=time_padding,
                            domain=[pd.to_datetime(time_min), pd.to_datetime(time_max)],
                        ),
                    ),
                    y=alt.Y(
                        "value:Q",
                        title="kW",
                        scale=alt.Scale(domain=[y_min, y_max], padding=y_padding),
                    ),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(domain=colorDomain, range=colorRange),
                        legend=alt.Legend(title=""),
                    ),
                    tooltip=[
                        alt.Tooltip("label:N", title=" "),
                        alt.Tooltip("time:T", format=READABLE_TIME_FORMAT, title="time"),
                        alt.Tooltip("value:Q", title="kw"),
                    ],
                )
            )

            # Nit (UI): Make dispatches have a semitransparent color instead - use mark_rect with a 'start' and 'stop' value
            annotations_chart = (
                alt.Chart(dispatch_annotations)
                .mark_rule(opacity=1, strokeWidth=4)
                .encode(
                    x="time:T",
                    color=alt.Color("label:N", scale=alt.Scale(domain=colorDomain, range=colorRange)),
                    strokeDash=alt.condition(
                        alt.datum.type == "Current Time",
                        alt.value([5, 5]),  # [dash_length, gap_length]
                        alt.value([0]),  # line
                    ),
                    tooltip=[
                        alt.Tooltip("label:N", title=" "),
                        alt.Tooltip("time:T", format=READABLE_TIME_FORMAT_SECONDS, title="time"),
                    ],
                )
            )

            title = f"""API State at {to_readable_time(current_time)} ({", ".join(all_dispatch_annotations_by_time[current_time])})"""
            chart = (
                alt.layer(annotations_chart, setpoints_chart)
                .resolve_scale(color="shared")
                .properties(
                    width=width,
                    height=50,
                    title={"text": title, "anchor": "start"},
                )
            )
            charts.append(chart)

        all_charts = alt.vconcat(*charts).resolve_scale(x="shared", y="shared", color="shared").resolve_legend(color="shared")

        if scenario.get("expected_result"):
            expected_load = pd.DataFrame(scenario["expected_result"])

            load_labels = ["Expected Power Use"]
            loadColorDomain = [label for label in colorMap.keys() if label in load_labels]
            loadColorRange = [colorMap[label] for label in loadColorDomain]

            title = "Expected Power Use"
            expected_load_chart = (
                alt.Chart(expected_load)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "time:T",
                        title="",
                        axis=alt.Axis(format=TIME_FORMAT_12),
                        scale=alt.Scale(
                            padding=time_padding,
                            domain=[pd.to_datetime(time_min), pd.to_datetime(time_max)],
                        ),
                    ),
                    y=alt.Y(
                        "value:Q",
                        title="kW",
                        scale=alt.Scale(domain=[y_min, y_max], padding=y_padding),
                    ),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(domain=loadColorDomain, range=loadColorRange),
                        legend=alt.Legend(title=" "),
                    ),
                    strokeDash=alt.value([4, 4]),
                    tooltip=[
                        alt.Tooltip("label:N", title=" "),
                        alt.Tooltip("time:T", format=READABLE_TIME_FORMAT, title="timestamp"),
                        alt.Tooltip("value:Q", title="value"),
                    ],
                )
                .properties(
                    width=width,
                    height=100,
                    title=title,
                )
                .configure_point(size=60)
            )
        else:
            expected_load_chart = None
        return all_charts, expected_load_chart

    def get_current_setpoints(current_time, setpoints_timeseries):
        setpoints = []
        latest_time_found = datetime.min  # The smallest date that exists in python
        for ts in setpoints_timeseries:
            if ts["published_time"] <= current_time and ts["published_time"] > latest_time_found:
                setpoints = ts["setpoints"]
                latest_time_found = ts["published_time"]
        return setpoints

    def get_dispatch_annotations(scenario, current_time=None):
        # Gets all times at which things happen in the scenario
        # If `current_time` is specified, only returns dispatch annotations that are known at the `current_time`
        def add_annotation(time, label, type, dispatch=None):
            annotations.append({"time": time, "label": label, "type": type, "dispatch": dispatch})

        annotations = []

        for dispatch_name, dispatch in scenario["dispatches"].items():
            sorted_dispatch_states = sorted(
                dispatch["states"],
                key=lambda state: state["published_time"],
            )
            # currently visible dispatch state
            latest_published_time_found = datetime.min
            latest_dispatch_state_i = None
            for i, dispatch_state in enumerate(sorted_dispatch_states):
                published_time = dispatch_state["published_time"]
                if latest_published_time_found < published_time and (current_time is None or published_time <= current_time):
                    latest_dispatch_state_i = i

            if latest_dispatch_state_i is not None:
                latest_dispatch_state = sorted_dispatch_states[latest_dispatch_state_i]
                add_annotation(
                    time=latest_dispatch_state["dispatch"]["creation_time"],
                    label=f"{dispatch_name} Create",
                    type="Creation Time",
                    dispatch=dispatch_name,
                )
                add_annotation(
                    time=latest_dispatch_state["dispatch"]["start_time"],
                    label=f"{dispatch_name} Start",
                    type="Start Time",
                    dispatch=dispatch_name,
                )
                end_time = latest_dispatch_state["dispatch"].get("end_time")
                if end_time:
                    add_annotation(
                        time=end_time,
                        label=f"{dispatch_name} End",
                        type="End Time",
                        dispatch=dispatch_name,
                    )

                # Dispatch Update annotations
                has_more_than_one_update = len(dispatch["states"]) > 2
                if current_time is None and len(dispatch["states"]) > 1:
                    for i, dispatch_state in enumerate(
                        sorted(
                            dispatch["states"],
                            key=lambda state: state["published_time"],
                        )
                    ):
                        if i >= 1:
                            add_annotation(
                                time=dispatch_state["published_time"],
                                label=f"{dispatch_name} Update{f' {i}' if has_more_than_one_update else ''}",
                                type="Dispatch Update",
                                dispatch=dispatch_name,
                            )
                elif current_time is not None and (latest_dispatch_state["dispatch"]["creation_time"] != latest_dispatch_state["published_time"]):
                    add_annotation(
                        time=latest_dispatch_state["published_time"],
                        label=f"{dispatch_name} Update{f' {latest_dispatch_state_i}' if has_more_than_one_update else ''}",
                        type="Dispatch Update",
                        dispatch=dispatch_name,
                    )

        if current_time:
            add_annotation(current_time, "Current Time", "Current Time")

        for i, ts in enumerate(scenario.get("setpoints_timeseries", [])):
            add_annotation(ts["published_time"], f"Publish Time {i + 1}", "Publish Time")

        annotations_df = pd.DataFrame(annotations, columns=["time", "label", "type", "dispatch"])
        annotations_df = annotations_df.fillna('')

        # Get annotations grouped by time in format of:
        # {
        #  datetime('2025-08-05 22:50:00'): ['Notification Time', 'Dispatch Create', 'Dispatch Start', 'Publish Time 1'],
        #  datetime('2025-08-05 22:52:00'): ['Publish Time 2']
        # }
        annotations_by_time = {}
        for time, group in annotations_df.groupby("time"):
            annotations_by_time[time.to_pydatetime()] = group["label"].tolist()
        return annotations_df, annotations_by_time

    return get_charts, get_dispatch_annotations


if __name__ == "__main__":
    app.run()
