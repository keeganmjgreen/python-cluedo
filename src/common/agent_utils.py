import abc
import dataclasses
from copy import deepcopy
from typing import List, Union

from src.common.cards import RUMORS, Crime, RumorCard

CASE_FILE = "Case File"
EXTRA_CARDS = "Extra Cards"


@dataclasses.dataclass
class UnknownRumor(RumorCard):
    pass


@dataclasses.dataclass
class CardReveal:
    other_player_index: int
    rumor_card: Union[None, RumorCard, UnknownRumor]


agent_index_type = int


@dataclasses.dataclass
class GameLogEntry:
    turn_index: int
    turn_player_index: agent_index_type
    guess: Crime
    card_reveals: List[CardReveal]


@dataclasses.dataclass
class BaseAgent(abc.ABC):
    agent_index: Union[agent_index_type, None]
    player_indices: List[agent_index_type]
    n_cards_per_player: int

    def __post_init__(self):
        self._game_log: List[GameLogEntry] = []

    def add_game_log_entry(
        self,
        turn_index: int,
        turn_player_index: int = None,
        guess: Crime = None,
        card_reveals: List[CardReveal] = [],
    ) -> None:
        self._game_log.append(
            GameLogEntry(turn_index, turn_player_index, guess, card_reveals)
        )

    def shown_card(
        self, turn_index: int, other_player_index: int, rumor_card: RumorCard
    ) -> None:
        self._game_log[turn_index].card_reveals.append(
            CardReveal(other_player_index, rumor_card)
        )

    def shown_extra_cards(self, turn_index: int, rumor_cards: List[RumorCard]) -> None:
        for rumor_card in rumor_cards:
            self.shown_card(
                turn_index=turn_index,
                other_player_index=EXTRA_CARDS,
                rumor_card=rumor_card,
            )

    @abc.abstractmethod
    def _try_solving_crime(self) -> Union[None, Crime]:
        pass


class BaseObserver(BaseAgent, abc.ABC):
    pass


class BasePlayer(BaseAgent, abc.ABC):
    def __init__(
        self,
        rumor_cards: List[RumorCard],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._rumor_cards = rumor_cards

    @abc.abstractmethod
    def make_guess(self) -> Crime:
        pass

    @abc.abstractmethod
    def answer_guess(self, guess: Crime) -> Union[RumorCard, None]:
        pass


class NaivePlayer(BasePlayer):
    def __init__(self, **kwargs):
        super().__init(**kwargs)
        self._remaining_possible_rumors = deepcopy(RUMORS)
        for rumor_card in self._rumor_cards:
            self._remaining_possible_rumors.remove(rumor_card)
