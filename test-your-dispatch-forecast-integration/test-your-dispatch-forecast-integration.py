# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair==6.2.2",
#     "marimo>=0.23.11",
#     "pandas==3.0.3",
#     "python-dateutil==2.9.0.post0",
#     "pytz==2026.2",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="columns")

with app.setup(hide_code=True):
    import json
    import textwrap
    import warnings
    from datetime import datetime, timedelta

    import altair as alt
    import marimo as mo
    import pandas as pd
    import pytz
    from dateutil.tz import tzlocal

    warnings.filterwarnings("ignore", category=UserWarning)

    READABLE_TIME_FORMAT = "%I:%M %p"
    READABLE_TIME_FORMAT_SECONDS = "%I:%M:%S %p"

    def get_now_notification_time():
        return datetime.now().replace(second=0, microsecond=0)  # Round down by ~one minute

    def get_now_rounded_5min_notification_time():
        return pd.Timestamp(get_now_notification_time()).ceil("5min").to_pydatetime()

    def parse_timestamp(timestamp_str):
        return pd.to_datetime(timestamp_str).to_pydatetime().astimezone(None).replace(tzinfo=None)

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

    def floor_utc_hour(timestamp):
        utc = timestamp.replace(tzinfo=tzlocal()).astimezone(pytz.utc)
        return utc.replace(minute=0, second=0, microsecond=0).astimezone(tzlocal()).replace(tzinfo=None)

    def ceil_utc_hour(timestamp):
        hour_start = floor_utc_hour(timestamp)
        return hour_start if hour_start == timestamp else hour_start + timedelta(hours=1)

    def scenario_to_json_payload(scenario) -> str:
        payload = {
            "name": scenario["name"],
            "scenario_type": "custom",
            "sites": scenario["sites"],
            "dispatch_forecasts": scenario["dispatch_forecasts"],
        }
        if scenario["dispatches"]:
            payload["dispatches"] = scenario["dispatches"]

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, object):
                if isinstance(object, datetime):
                    return datetime_to_json(object)

                return json.JSONEncoder.default(self, object)

        return json.dumps(payload, cls=DateTimeEncoder, indent=2)

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

    def get_curl(url, headers):
        headers = " ".join([f"--header '{key}: {val}'" for key, val in headers.items()])
        return f"curl --request GET --url '{url}' {headers}"

    DISPATCH_FORECAST_TUTORIAL_URL = "https://api.voltus.co/docs/"  # Placeholder until the dispatch forecast tutorial is published
    SANDBOX_URL = "https://sandbox.voltus.co/2022-04-15"

    default_tick_interval = 10
    default_site_id = "kd1k"
    default_site_name = "My Site"
    default_site_customer_location_id = "example-location-id"
    default_api_key = "YOUR_SANDBOX_API_KEY"
    default_notification_time = datetime_to_json_local(get_now_notification_time())

    tick_interval_input = mo.ui.number(
        label="Tick Interval (minutes between forecast updates)",
        value=default_tick_interval,
        start=1,
        full_width=True,
    )
    site_id_input = mo.ui.text(label="Site ID", value=default_site_id, full_width=True)
    site_name_input = mo.ui.text(label="Site Name", value=default_site_name, full_width=True)
    site_customer_location_id_input = mo.ui.text(
        label="Site Customer Location ID",
        value=default_site_customer_location_id,
        full_width=True,
    )
    program_1_name_input = mo.ui.text(label="Program 1 Name", value="Program One", full_width=True)
    program_1_id_input = mo.ui.number(label="Program 1 ID", value=1, full_width=True)
    program_2_name_input = mo.ui.text(label="Program 2 Name", value="Program Two", full_width=True)
    program_2_id_input = mo.ui.number(label="Program 2 ID", value=2, full_width=True)

    notification_time_input = mo.ui.text(placeholder="2020-12-30T13:00:00Z", full_width=True)
    set_now_notification_time_button = mo.ui.run_button(label="Set Notification Time To Now")
    set_now_notification_time_rounded_button = mo.ui.run_button(label="Set Notification Time To Now (round up 5 min)")


@app.cell(hide_code=True)
def _():
    mo.md(f"""
    Use these scenarios to test how your EMS handles dispatch forecasts in the sandbox. For an overview of how to use dispatch forecasts in your EMS, see the [Voltus API documentation]({DISPATCH_FORECAST_TUTORIAL_URL}).

    **Before you start**: You need a sandbox API key for `sandbox.voltus.co`. If you don't have one, email your Voltus Account Manager or Project Engineer. Use it in place of `{default_api_key}` in the example curl requests below.
    """)
    return


@app.cell(hide_code=True)
def _(inputs):
    mo.md(f"""
    <h1>Customization</h1>

    To customize test scenarios below, modify the following fields:

    {inputs}
    """)
    return


@app.cell(hide_code=True)
def _(FORECAST_SCENARIOS, display_scenarios, tick_interval):
    mo.vstack([mo.md(f"""
    # Forecast Scenarios

    Each scenario below combines dispatch forecasts with dispatches. Create it via the `POST /scenarios` endpoint, using the provided curl request and your sandbox API key. Then poll `GET /dispatch_forecasts` and `GET /dispatches` while the scenario plays out, and check that your EMS does what the scenario expects.

    A scenario holds a list of forecast updates, each with a `published_time`. `GET /dispatch_forecasts` returns, for each site and program, the latest update published before the request time.
    The forecasts returned in this sandbox have the same characteristics as those in production. If the scenario has a dispatch for a given site and program, the forecast has a dispatch likelihood of 1 for every interval overlapping the dispatch. Intervals with no forecast have a dispatch likelihood of 0.

    Forecast intervals are hourly, but these scenarios include updates to the forecasts that are published {tick_interval} minutes apart (configurable with the Tick Interval above), so you can see the forecast change while testing. Dispatches start up to a few hours after you create the scenario.

    **Tip**: Scenario times are based on the Notification Time above. Set it to now right before you create a scenario. When you POST a scenario, the previous scenario is overwritten, so to restart a scenario, set the Notification Time to now and POST it again.

    **Passing the tests**: You must monitor your systems to ensure they meet the expected result for each scenario. Voltus will not be able to monitor the output of your system.
    """), display_scenarios(FORECAST_SCENARIOS)])
    return


@app.cell(column=1, hide_code=True)
def define_scenarios():
    METHOD = "POST"
    URL = f"{SANDBOX_URL}/scenarios"
    HEADERS = {"X-Voltus-API-Key": default_api_key, "Content-Type": "application/json"}

    tick_interval = tick_interval_input.value
    tick = timedelta(minutes=tick_interval)

    PROGRAM_1 = {
        "name": program_1_name_input.value,
        "id": int(program_1_id_input.value),
        "timezone": "US/Pacific",
        "market": "CAISO",
        "program_type": "capacity",
    }

    PROGRAM_2 = {
        "name": program_2_name_input.value,
        "id": int(program_2_id_input.value),
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
    if set_now_notification_time_rounded_button.value:
        NOTIFICATION_TIME = get_now_rounded_5min_notification_time()

    SITE = {
        "id": site_id_input.value,
        "name": site_name_input.value,
        "customer_location_id": site_customer_location_id_input.value,
        "commitment": 1000,
    }

    inputs = mo.vstack(
        [
            mo.hstack([tick_interval_input, ""], justify="start"),
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
            mo.hstack([program_1_name_input, program_1_id_input, program_2_name_input, program_2_id_input], justify="start"),
        ],
        gap=1,
    )

    def get_dispatch_state(
        published_time,
        creation_time,
        start_time,
        end_time,
        program,
        modification_number=0,
        authorized=True,
        test=False,
    ):
        return {
            "published_time": published_time,
            "dispatch": {
                "authorized": authorized,
                "test": test,
                "creation_time": creation_time,
                "start_time": start_time,
                "end_time": end_time,
                "modification_number": modification_number,
                "sites": [SITE],
                "program": program,
            },
        }

    def get_dispatch(published_time, start_time, end_time, program):
        return {
            "states": [
                get_dispatch_state(
                    published_time=published_time,
                    creation_time=published_time,
                    start_time=start_time,
                    end_time=end_time,
                    program=program,
                )
            ]
        }

    def get_hour_starts(first_hour_start, hours):
        return [first_hour_start + timedelta(hours=i) for i in range(hours)]

    def get_window_hour_starts(last_hour_end):
        """Hour starts from the hour holding the notification time to two hours past `last_hour_end`."""
        first_hour_start = floor_utc_hour(NOTIFICATION_TIME)
        hours = int((last_hour_end - first_hour_start) / timedelta(hours=1)) + 2
        return get_hour_starts(first_hour_start, hours)

    def get_dispatch_forecast(published_time, program, window_hour_starts, likelihood_by_hour_start):
        return {
            "site_id": SITE["id"],
            "published_time": published_time,
            "program": program,
            "dispatch_forecast": [
                {
                    "interval_seconds": 3600,
                    "interval_end": hour_start + timedelta(hours=1),
                    "likelihood": likelihood_by_hour_start.get(hour_start, 0),
                }
                for hour_start in window_hour_starts
            ],
        }

    def get_block_forecasts(published_times, likelihoods, program, block_hour_starts, window_hour_starts):
        return [
            get_dispatch_forecast(
                published_time,
                program,
                window_hour_starts,
                {hour_start: likelihood for hour_start in block_hour_starts},
            )
            for published_time, likelihood in zip(published_times, likelihoods)
        ]

    T = NOTIFICATION_TIME

    test_one_dispatch_published = T + 3 * tick
    test_one_block = get_hour_starts(ceil_utc_hour(test_one_dispatch_published) + timedelta(hours=1), 2)
    test_one_window = get_window_hour_starts(test_one_block[-1] + timedelta(hours=1))

    test_two_block = get_hour_starts(ceil_utc_hour(T + 2 * tick) + timedelta(hours=1), 2)
    test_two_window = get_window_hour_starts(test_two_block[-1] + timedelta(hours=1))

    test_three_block_1 = get_hour_starts(ceil_utc_hour(T + 2 * tick) + timedelta(hours=1), 1)
    test_three_block_2 = get_hour_starts(test_three_block_1[-1] + timedelta(hours=3), 1)
    test_three_window = get_window_hour_starts(test_three_block_2[-1] + timedelta(hours=1))

    test_four_dispatch_start = ceil_utc_hour(T + tick)
    test_four_window = get_window_hour_starts(test_four_dispatch_start + timedelta(hours=1))

    FORECAST_SCENARIOS = [
        {
            "name": "Forecast Test 1: Forecast Precedes a Dispatch",
            "description": f"""
                The likelihood of a dispatch in a two-hour block rises with each forecast update, then a dispatch overlapping the block is published.

                API Behavior: Forecast updates are published {tick_interval} minutes apart, with a likelihood of 0.2, then 0.5, then 0.8 for the block. {tick_interval} minutes after the last update, a dispatch is published overlapping the block's first and second hours. At that point, the dispatch forecast reads 1 for both hours, since the dispatch overlaps each of them.
                """,
            "expected_result_description": """
                Your EMS prepares for the block as the likelihood rises, for example by charging the battery. It discharges only once the dispatch appears in `GET /dispatches`, and only for the dispatch's start and end times.
                """,
            "sites": [SITE],
            "dispatch_forecasts": get_block_forecasts([T, T + tick, T + 2 * tick], [0.2, 0.5, 0.8], PROGRAM_1, test_one_block, test_one_window),
            "dispatches": {
                "Dispatch": get_dispatch(test_one_dispatch_published, test_one_block[0] + timedelta(minutes=25), test_one_block[0] + timedelta(minutes=65), PROGRAM_1)
            },
        },
        {
            "name": "Forecast Test 2: False Alarm",
            "description": f"""
                The likelihood of a dispatch in a two-hour block rises and stays high, but no dispatch is published.

                API Behavior: Forecast updates are published {tick_interval} minutes apart, with a likelihood of 0.3, then 0.6, then 0.8 for the block. No dispatch is published.
                """,
            "expected_result_description": """
                Your EMS may prepare for the block, for example by charging the battery, but never discharges for it. A high likelihood is not a dispatch.
                """,
            "sites": [SITE],
            "dispatch_forecasts": get_block_forecasts([T, T + tick, T + 2 * tick], [0.3, 0.6, 0.8], PROGRAM_1, test_two_block, test_two_window),
            "dispatches": {},
        },
        {
            "name": "Forecast Test 3: Two Programs on One Site",
            "description": f"""
                Two programs forecast a likely dispatch on the same site, an hour each, with two hours between them. A dispatch is then published for each.

                API Behavior: At the notification time, one forecast is published for each program, with a likelihood of 0.7 for that program's hour. `GET /dispatch_forecasts` returns one series per program. {tick_interval} minutes later, a dispatch in Program 1 is published for 15 to 45 minutes past its hour, and {tick_interval} minutes after that, a dispatch in Program 2 is published for the whole of its hour. Each reads 1 for its hour in its own program's series.
                """,
            "expected_result_description": """
                Your EMS takes both programs' forecasts into account. The battery participates in both dispatches and recharges in the two hours between them.
                """,
            "sites": [SITE],
            "dispatch_forecasts": get_block_forecasts([T], [0.7], PROGRAM_1, test_three_block_1, test_three_window)
            + get_block_forecasts([T], [0.7], PROGRAM_2, test_three_block_2, test_three_window),
            "dispatches": {
                "Dispatch 1": get_dispatch(T + tick, test_three_block_1[0] + timedelta(minutes=15), test_three_block_1[0] + timedelta(minutes=45), PROGRAM_1),
                "Dispatch 2": get_dispatch(T + 2 * tick, test_three_block_2[0], test_three_block_2[0] + timedelta(hours=1), PROGRAM_2),
            },
        },
        {
            "name": "Forecast Test 4: Dispatch With a Zero Forecast",
            "description": f"""
                The forecast says a dispatch is unlikely, then a dispatch is published anyway.

                API Behavior: At the notification time, a forecast is published with a likelihood of 0 for every hour. {tick_interval} minutes later, a 30-minute dispatch starting 10 minutes into the next whole hour is published, and `GET /dispatch_forecasts` reads 1 for that hour.
                """,
            "expected_result_description": """
                Your EMS responds to the dispatch as it would without a forecast. Dispatches are the source of truth, whatever the forecast said.
                """,
            "sites": [SITE],
            "dispatch_forecasts": [get_dispatch_forecast(T, PROGRAM_1, test_four_window, {})],
            "dispatches": {
                "Dispatch": get_dispatch(T + tick, test_four_dispatch_start + timedelta(minutes=10), test_four_dispatch_start + timedelta(minutes=40), PROGRAM_1)
            },
        },
    ]
    return (
        FORECAST_SCENARIOS,
        HEADERS,
        METHOD,
        SITE,
        URL,
        inputs,
        tick_interval,
    )


@app.cell(hide_code=True)
def _(HEADERS, METHOD, SITE, URL, get_forecast_charts, get_timeline):
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

    def display_scenario(scenario):
        timeline = "\n".join(f"- {to_readable_time(time, seconds=False)}: {', '.join(labels)}" for time, labels in get_timeline(scenario).items())

        curl = scenario_to_curl(scenario, URL, HEADERS, METHOD).replace("\n", " ")
        get_headers = {"X-Voltus-API-Key": default_api_key}
        forecasts_curl = get_curl(f"{SANDBOX_URL}/dispatch_forecasts?site_id={SITE['id']}", get_headers)
        dispatches_curl = get_curl(f"{SANDBOX_URL}/dispatches", get_headers)

        checking = [
            "Poll the forecast while the scenario plays out. Each response should match the chart above at that time:",
            textwrap.dedent(code_block(forecasts_curl, type="sh")),
        ]
        if scenario["dispatches"]:
            checking += [
                "Once a dispatch is published, it is also returned by `GET /dispatches`:",
                textwrap.dedent(code_block(dispatches_curl, type="sh")),
            ]

        # Sections are joined unindented: a multi-line value inside an indented template breaks the markdown.
        sections = [
            style,
            "**Description**",
            textwrap.dedent(scenario["description"]).strip(),
            timeline,
            "Each line is what one forecast update gives each hour. The shaded span is the dispatch: once it's published, every hour it overlaps reads 1.",
            mo.as_html(get_forecast_charts(scenario)).text,
            "**Expected Result**",
            textwrap.dedent(scenario["expected_result_description"]).strip(),
            "**Creating the Test**",
            scrollable_code_block(curl, type="sh", height=250),
            f"/// details | Request payload\n\n```json\n{scenario_to_json_payload(scenario)}\n```\n\n///",
            "**Checking the Results**",
            *checking,
        ]
        return "\n\n".join(sections)

    def display_scenarios(scenarios):
        return mo.accordion(
            {f"<h2 class='inline'>{scenario['name']}</h2>": make_text_black(display_scenario(scenario)) for scenario in scenarios},
            multiple=True,
        )

    def make_text_black(string):
        return f"""<div style="color: black">

    {str_to_md_to_html_text(string)}

    </div>
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
        return scrollable_block(code_block(string, type), height=height)

    # Add the style here, so other cells render it
    mo.md(style)
    return (display_scenarios,)


@app.cell(hide_code=True)
def get_forecast_charts():
    REVISION_COLORS = ["#86b6ef", "#2a78d6", "#104281"]
    DISPATCH_COLOR = "#eb6834"
    NOW_COLOR = "#52514e"
    GRID_COLOR = "#e1e0d9"
    AXIS_COLOR = "#c3c2b7"
    LABEL_COLOR = "#898781"

    def get_timeline(scenario):
        """Labels of what happens in the scenario, by time, in time order."""
        labels_by_time = {}

        def add(time, label):
            labels_by_time.setdefault(time, []).append(label)

        for forecast in scenario["dispatch_forecasts"]:
            highest = max(forecast["dispatch_forecast"], key=lambda interval: interval["likelihood"])
            if highest["likelihood"] == 0:
                summary = "likelihood 0 for every hour"
            else:
                summary = f"highest likelihood {highest['likelihood']}"
            add(forecast["published_time"], f"Forecast published for {forecast['program']['name']} ({summary})")

        for dispatch_name, dispatch in scenario["dispatches"].items():
            for state in dispatch["states"]:
                program_name = state["dispatch"]["program"]["name"]
                add(state["published_time"], f"{dispatch_name} published for {program_name}")
                add(state["dispatch"]["start_time"], f"{dispatch_name} starts")
                add(state["dispatch"]["end_time"], f"{dispatch_name} ends")

        return dict(sorted(labels_by_time.items()))

    def get_forecast_chart(scenario, program, now):
        forecasts = sorted(
            [forecast for forecast in scenario["dispatch_forecasts"] if forecast["program"]["id"] == program["id"]],
            key=lambda forecast: forecast["published_time"],
        )
        revision_labels = [f"Published {to_readable_time(forecast['published_time'], seconds=False)}" for forecast in forecasts]

        likelihood_rows = []
        for label, forecast in zip(revision_labels, forecasts):
            for interval in forecast["dispatch_forecast"]:
                hour_start = interval["interval_end"] - timedelta(hours=1)
                for time in [hour_start, interval["interval_end"]]:
                    likelihood_rows.append(
                        {
                            "time": time,
                            "hour_start": hour_start,
                            "hour_end": interval["interval_end"],
                            "likelihood": interval["likelihood"],
                            "label": label,
                        }
                    )
        likelihoods = pd.DataFrame(likelihood_rows)
        time_domain = [likelihoods["time"].min(), likelihoods["time"].max()]
        hour_ticks = [
            alt.DateTime(year=time.year, month=time.month, date=time.day, hours=time.hour, minutes=time.minute)
            for time in sorted(likelihoods["time"].unique())
        ]

        dispatches = pd.DataFrame(
            [
                {
                    "start": state["dispatch"]["start_time"],
                    "end": state["dispatch"]["end_time"],
                    "label": f"Dispatch, published {to_readable_time(state['published_time'], seconds=False)}",
                }
                for dispatch in scenario["dispatches"].values()
                for state in dispatch["states"]
                if state["dispatch"]["authorized"] and state["dispatch"]["program"]["id"] == program["id"]
            ],
            columns=["start", "end", "label"],
        )

        color_domain = revision_labels + list(dispatches["label"])
        color_range = REVISION_COLORS[-len(revision_labels) :] + [DISPATCH_COLOR] * len(dispatches)
        color = alt.Color(
            "label:N",
            scale=alt.Scale(domain=color_domain, range=color_range),
            legend=alt.Legend(title=None, orient="top", direction="horizontal", symbolType="stroke", symbolOpacity=1, symbolStrokeWidth=2, labelLimit=0, labelColor="#52514e"),
        )

        def time_x(field):
            return alt.X(
                f"{field}:T",
                title=None,
                scale=alt.Scale(domain=time_domain),
                axis=alt.Axis(format="%-I:%M %p", values=hour_ticks, grid=False),
            )

        dispatch_layer = (
            alt.Chart(dispatches)
            .mark_rect(opacity=0.15)
            .encode(
                x=time_x("start"),
                x2="end:T",
                color=color,
                tooltip=[
                    alt.Tooltip("label:N", title=" "),
                    alt.Tooltip("start:T", format=READABLE_TIME_FORMAT, title="from"),
                    alt.Tooltip("end:T", format=READABLE_TIME_FORMAT, title="to"),
                ],
            )
        )

        line_layer = (
            alt.Chart(likelihoods)
            .mark_line(strokeWidth=2, strokeJoin="round", strokeCap="round")
            .encode(
                x=time_x("time"),
                y=alt.Y("likelihood:Q", title="Likelihood", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(tickCount=5, gridColor=GRID_COLOR)),
                color=color,
                order="time:T",
                detail="label:N",
            )
        )

        hover_layer = (
            alt.Chart(likelihoods.drop_duplicates(["label", "hour_start"]))
            .transform_calculate(hour_middle="toDate(datum.hour_start) + 30 * 60 * 1000")
            .mark_point(size=400, filled=True, opacity=0.001)
            .encode(
                x=time_x("hour_middle"),
                y="likelihood:Q",
                tooltip=[
                    alt.Tooltip("label:N", title="forecast"),
                    alt.Tooltip("hour_start:T", format=READABLE_TIME_FORMAT, title="from"),
                    alt.Tooltip("hour_end:T", format=READABLE_TIME_FORMAT, title="to"),
                    alt.Tooltip("likelihood:Q", title="likelihood"),
                ],
            )
        )

        layers = [dispatch_layer, line_layer, hover_layer]
        if time_domain[0] <= now <= time_domain[1]:
            now_data = pd.DataFrame([{"time": now, "text": f"Now ({to_readable_time(now, seconds=False)})"}])
            now_rule = alt.Chart(now_data).mark_rule(color=NOW_COLOR, strokeWidth=1).encode(x=time_x("time"))
            now_text = (
                alt.Chart(now_data)
                .mark_text(align="left", baseline="top", dx=4, y=2, color=NOW_COLOR, fontSize=11)
                .encode(x=time_x("time"), text="text:N")
            )
            layers += [now_rule, now_text]

        return alt.layer(*layers).properties(
            width=600,
            height=160,
            title={"text": f"{program['name']} (program {program['id']})", "anchor": "start", "fontWeight": "normal", "color": "#0b0b0b"},
        )

    def get_forecast_charts(scenario):
        """One chart per program: the likelihood each forecast update gives each hour, with dispatches shaded."""
        programs_by_id = {forecast["program"]["id"]: forecast["program"] for forecast in scenario["dispatch_forecasts"]}
        now = get_now_notification_time()
        charts = [get_forecast_chart(scenario, program, now) for program in programs_by_id.values()]
        return (
            alt.vconcat(*charts)
            .resolve_scale(color="independent")
            .configure_view(stroke=None)
            .configure_axis(domainColor=AXIS_COLOR, tickColor=AXIS_COLOR, labelColor=LABEL_COLOR, titleColor=LABEL_COLOR)
        )

    return get_forecast_charts, get_timeline


if __name__ == "__main__":
    app.run()
