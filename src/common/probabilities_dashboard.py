import plotly.express as px
from dash import Dash, Input, Output, dcc, html

from src.common.agent_utils import agent_index_type
from src.common.probabilities_artifact_manager import ProbabilitiesArtifactManager

app = Dash(__name__)

field_titles = {
    "game_id": "Game ID",
    "agent_type": "Agent Type",
    "agent_index": "Agent Index",
    "turn_index": "Turn Index",
}

app.layout = html.Div(
    [
        html.H1(children="Probabilities Dashboard", style={"textAlign": "center"}),
        html.Div(
            [
                html.Div(
                    [
                        field_title,
                        dcc.Dropdown(
                            value="(Latest)",
                            id=f"{field_name}-dropdown-selection",
                        ),
                    ]
                )
                for field_name, field_title in field_titles.items()
            ]
        ),
        dcc.Graph(id="graph-content"),
        dcc.Interval(
            id="interval-component",
            interval=1000,  # In milliseconds.
            n_intervals=0,
        ),
    ]
)


@app.callback(
    Output("game_id-dropdown-selection", "options"),
    Input("game_id-dropdown-selection", "search_value"),
)
def update_options(search_value):
    probabilities_artifact_mgr = ProbabilitiesArtifactManager()
    df = probabilities_artifact_mgr.df
    return ["(Latest)"] + df["game_id"].unique().tolist()


@app.callback(
    Output("agent_type-dropdown-selection", "options"),
    Input("agent_type-dropdown-selection", "search_value"),
    Input("game_id-dropdown-selection", "value"),
)
def update_options(search_value, game_id):
    probabilities_artifact_mgr = ProbabilitiesArtifactManager()
    df = probabilities_artifact_mgr.df
    if game_id == "(Latest)":
        return ["(Latest)"]
    else:
        return ["(Latest)"] + df[df["game_id"] == game_id][
            "agent_type"
        ].unique().tolist()


@app.callback(
    Output("agent_index-dropdown-selection", "options"),
    Input("agent_index-dropdown-selection", "search_value"),
    Input("game_id-dropdown-selection", "value"),
    Input("agent_type-dropdown-selection", "value"),
)
def update_options(search_value, game_id, agent_type):
    probabilities_artifact_mgr = ProbabilitiesArtifactManager()
    df = probabilities_artifact_mgr.df
    return ["(Latest)"] + df[
        (df["game_id"] == game_id) & (df["agent_type"] == agent_type)
    ]["agent_index"].unique().tolist()


@app.callback(
    Output("turn_index-dropdown-selection", "options"),
    Input("agent_index-dropdown-selection", "search_value"),
    Input("game_id-dropdown-selection", "value"),
    Input("agent_type-dropdown-selection", "value"),
    Input("agent_index-dropdown-selection", "value"),
)
def update_options(search_value, game_id, agent_type, agent_index):
    probabilities_artifact_mgr = ProbabilitiesArtifactManager()
    df = probabilities_artifact_mgr.df
    return ["(Latest)"] + df[
        (df["game_id"] == game_id)
        & (df["agent_type"] == agent_type)
        & (df["agent_index"] == agent_index)
    ]["turn_index"].unique().tolist()


@app.callback(
    Output(component_id="graph-content", component_property="figure"),
    Input(component_id="interval-component", component_property="n_intervals"),
    *[
        Input(
            component_id=f"{field_name}-dropdown-selection", component_property="value"
        )
        for field_name in field_titles.keys()
    ],
)
def update_probabilities_heatmap(
    n: int,
    game_id: int,
    agent_type: str,
    agent_index: agent_index_type,
    turn_index: int,
):
    probabilities_artifact_mgr = ProbabilitiesArtifactManager()
    df = probabilities_artifact_mgr.df
    if game_id == "(Latest)":
        game_id = df["game_id"].iloc[-1]
    df = df[df["game_id"] == game_id]
    if agent_type == "(Latest)":
        agent_type = df["agent_type"].iloc[-1]
    df = df[df["agent_type"] == agent_type]
    if agent_index == "(Latest)":
        agent_index = df["agent_index"].iloc[-1]
    df = df[df["agent_index"] == agent_index]
    if turn_index == "(Latest)":
        turn_index = df["turn_index"].iloc[-1]
    probabilities_ser = probabilities_artifact_mgr.get_probabilities_ser(
        game_id,
        agent_type=agent_type,
        agent_index=agent_index,
        turn_index=turn_index,
    )
    probability_df = probabilities_ser.unstack()
    fig = px.imshow(probability_df.rename_axis(index="Player", columns="Rumor Card"))
    fig.update_xaxes(type="category")
    fig.update_yaxes(type="category")
    fig.update_layout(
        title=f"Approximate Probabilities | Game ID: {game_id:2.0f}, Turn Index: {turn_index:2.0f}, Agent Index: {agent_index}, Agent Type: {agent_type}"
    )
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
