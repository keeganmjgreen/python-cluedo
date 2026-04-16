import logging
import threading
from time import sleep

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

from common import store
from common.agent_utils import CASE_FILE
from common.cards import RUMORS
from common.consts import EXTRA_CARDS
from common.store import (
    AGENT,
    APPROX_PROBABILITY,
    CARD_LOCATION,
    RUMOR_CARD,
    TURN_INDEX,
)

logging.getLogger("werkzeug").setLevel(logging.ERROR)

FONT_FAMILY = "Helvetica Neue, Helvetica, Arial, sans-serif"
UPDATE_FREQ_MS = 200


app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1(children="Python-Cluedo Dashboard", style={"textAlign": "center"}),
        html.Div(
            [
                "Bot (Default: Latest)",
                dcc.Dropdown(value="(Latest)", id="agent-dropdown-selection"),
                "Turn (Default: Latest)",
                dcc.Dropdown(value="(Latest)", id="turn_index-dropdown-selection"),
            ]
        ),
        dcc.Graph(id="graph-content"),
        dcc.Interval(id="interval-component", interval=UPDATE_FREQ_MS, n_intervals=0),
    ],
    style={"fontFamily": FONT_FAMILY},
)


@app.callback(
    Output("agent-dropdown-selection", "options"),
    Input(component_id="interval-component", component_property="n_intervals"),
    Input("agent-dropdown-selection", "search_value"),
)
def update_options(n, search_value):
    df = store.get_probabilities_df()
    return ["(Latest)"] + df[AGENT].unique().tolist()


@app.callback(
    Output("turn_index-dropdown-selection", "options"),
    Input(component_id="interval-component", component_property="n_intervals"),
    Input("agent-dropdown-selection", "search_value"),
    Input("agent-dropdown-selection", "value"),
)
def update_options(n, search_value, agent):
    df = store.get_probabilities_df()
    return ["(Latest)"] + df[df[AGENT] == agent][TURN_INDEX].unique().tolist()


@app.callback(
    Output(component_id="graph-content", component_property="figure"),
    Input(component_id="interval-component", component_property="n_intervals"),
    Input(component_id="agent-dropdown-selection", component_property="value"),
    Input(component_id="turn_index-dropdown-selection", component_property="value"),
)
def update_probabilities_heatmap(n: int, agent: str, turn_index: int):
    df = store.get_probabilities_df()
    if len(df) > 0:
        if agent in ["(Latest)", None]:
            agent = df[AGENT].iloc[-1]
        df = df[df[AGENT] == agent]
        if turn_index in ["(Latest)", None]:
            turn_index = df[TURN_INDEX].iloc[-1]
        probabilities_ser = (
            df.set_index([AGENT, TURN_INDEX])
            .loc[agent, turn_index]
            .set_index([CARD_LOCATION, RUMOR_CARD])[APPROX_PROBABILITY]
        )
        probability_df = probabilities_ser.unstack()
        title = f"Approximate Probabilities | Turn {turn_index}, Bot {agent}"
    else:
        probability_df = pd.DataFrame(index=[CASE_FILE, EXTRA_CARDS])
        title = "Start the game to see probabilities."
    probability_df = probability_df.reindex(
        columns=[str(r) for r in RUMORS], fill_value=0
    )
    probability_df = probability_df.rename_axis(
        index="Card Location", columns="Rumor Card"
    )
    fig = px.imshow(probability_df, range_color=(0, 1))
    fig.update_xaxes(type="category")
    fig.update_yaxes(type="category")
    fig.update_layout(title=title, font_family=FONT_FAMILY)
    return fig


def run_dashboard() -> threading.Thread:
    thread = threading.Thread(target=app.run, daemon=True)  # type: ignore
    thread.start()
    sleep(0.1)
    input("\n=== Open the dashboard at the above URL and press Enter once open ===\n")
    return thread
