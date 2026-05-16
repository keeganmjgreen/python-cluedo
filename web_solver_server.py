from fastapi import FastAPI

from cluedo_assistant import run_cluedo_assistant, set_up_cluedo_assistant
from common.cards import RumorCard
from common.io.message_io import (
    BaseModel,
    GameHistoryExhaustedError,
    GameHistoryItem,
    Message,
    MessageIo,
)
from common.maths import CardLocation

app = FastAPI()


class ProbabilitiesData(BaseModel):
    matrix: list[list[float]]
    cols: list[str]
    rows: list[str]


class GameData(BaseModel):
    messages: list[Message]
    latest_probabilities_data: ProbabilitiesData | None


@app.post("/game-data/")
async def get_game_data(game_history: list[GameHistoryItem]) -> GameData:
    message_io = MessageIo(game_history=game_history)
    setup = None
    try:
        setup = set_up_cluedo_assistant(io=message_io)
        run_cluedo_assistant(setup, p_heatmap=True)
    except GameHistoryExhaustedError:
        pass
    if setup is not None and message_io.latest_probabilities is not None:
        matrix: dict[CardLocation, dict[RumorCard, float]] = {}
        for card_loc, probability in message_io.latest_probabilities.items():
            row = card_loc.location
            col = card_loc.rumor_card
            if row not in matrix:
                matrix[row] = {}
            matrix[row][col] = probability
        latest_probabilities_data = ProbabilitiesData(
            matrix=[list(ol.values()) for ol in matrix.values()],
            cols=[col.name.title() for col in next(iter(matrix.values())).keys()],
            rows=[
                f"{setup.player_names[row].capitalize()}'s hand"
                if isinstance(row, int)
                else row
                for row in matrix.keys()
            ],
        )
    else:
        latest_probabilities_data = None
    return GameData(
        messages=message_io.messages,
        latest_probabilities_data=latest_probabilities_data,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5005)
