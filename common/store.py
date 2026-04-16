from threading import Lock

import pandas as pd

from common.maths import CardIsInLocation

AGENT = "agent"
TURN_INDEX = "turn_index"
CARD_LOCATION = "card_location"
RUMOR_CARD = "rumor_card"
APPROX_PROBABILITY = "approx_probability"

_probabilities_df = pd.DataFrame(
    columns=[AGENT, TURN_INDEX, CARD_LOCATION, RUMOR_CARD, APPROX_PROBABILITY]
)
_lock = Lock()


def get_probabilities_df() -> pd.DataFrame:
    with _lock:
        return _probabilities_df.copy()


def append_probabilities(
    agent: str,
    turn_index: int,
    probabilities: dict[CardIsInLocation, float],
) -> None:
    global _probabilities_df
    append_df = pd.DataFrame(
        [
            {
                AGENT: str(agent),
                TURN_INDEX: turn_index,
                CARD_LOCATION: (
                    f"Player {v.location}"
                    if isinstance(v.location, int)
                    else v.location
                ),
                RUMOR_CARD: str(v.rumor_card),
                APPROX_PROBABILITY: p,
            }
            for v, p in probabilities.items()
        ]
    )
    with _lock:
        _probabilities_df = pd.concat([_probabilities_df, append_df])
