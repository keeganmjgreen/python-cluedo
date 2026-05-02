from enum import Enum
from typing import Literal

type ExtraCards = Literal["Extra Cards"]

EXTRA_CARDS = "Extra Cards"
MIN_N_PLAYERS = 2


class GameVariant(Enum):
    LEFT_PLAYERS_REVEAL = "left players reveal"
    RIGHT_PLAYERS_REVEAL = "right players reveal"
    BOTH_SIDES_REVEAL = "both sides reveal"
