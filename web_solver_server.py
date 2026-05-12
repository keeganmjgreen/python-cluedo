from fastapi import FastAPI

from cluedo_assistant import cluedo_assistant
from common.io.message_io import (
    BaseModel,
    GameHistoryExhaustedError,
    GameHistoryItem,
    Message,
    MessageIo,
)

app = FastAPI()


class GameData(BaseModel):
    messages: list[Message]


@app.post("/game-data/")
async def get_game_data(game_history: list[GameHistoryItem]) -> GameData:
    message_io = MessageIo(game_history=game_history)
    try:
        cluedo_assistant(io=message_io)
    except GameHistoryExhaustedError:
        pass
    return GameData(messages=message_io.messages)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5005)
