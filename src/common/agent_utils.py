import abc
import dataclasses
from collections.abc import Sequence
from copy import deepcopy
from typing import Literal

from common.cards import RUMORS, Crime, RumorCard
from common.consts import EXTRA_CARDS, ExtraCards

CASE_FILE = "Case File"

type CaseFile = Literal["Case File"]

AgentIndex = int


class UnknownRumor:
    pass


@dataclasses.dataclass
class CardReveal:
    other_player_index: AgentIndex | ExtraCards
    rumor_card: RumorCard | UnknownRumor | None


@dataclasses.dataclass
class GameLogEntry:
    turn_index: int
    turn_player_index: AgentIndex
    guess: Crime
    card_reveals: list[CardReveal]


@dataclasses.dataclass
class BaseAgent(abc.ABC):
    agent_index: AgentIndex
    player_indices: list[AgentIndex]
    n_cards_per_player: int

    def __post_init__(self):
        self._game_log: list[GameLogEntry] = []

    def add_game_log_entry(
        self,
        turn_index: int,
        turn_player_index: AgentIndex = None,
        guess: Crime = None,
        card_reveals: list[CardReveal] = [],
    ) -> None:
        self._game_log.append(
            GameLogEntry(turn_index, turn_player_index, guess, card_reveals)
        )

    def shown_card(
        self,
        turn_index: int,
        other_player_index: AgentIndex | ExtraCards,
        rumor_card: RumorCard | UnknownRumor | None,
    ) -> None:
        self._game_log[turn_index].card_reveals.append(
            CardReveal(other_player_index, rumor_card)
        )

    def shown_extra_cards(
        self, turn_index: int, rumor_cards: Sequence[RumorCard]
    ) -> None:
        for rumor_card in rumor_cards:
            self.shown_card(
                turn_index=turn_index,
                other_player_index=EXTRA_CARDS,
                rumor_card=rumor_card,
            )

    @abc.abstractmethod
    def try_solving_crime(self) -> Crime | None:
        pass


class BaseObserver(BaseAgent, abc.ABC):
    pass


class BasePlayer(BaseAgent, abc.ABC):
    def __init__(
        self,
        rumor_cards: list[RumorCard],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._rumor_cards = rumor_cards

    @abc.abstractmethod
    def make_guess(self, turn_index: int | None = None) -> Crime:
        raise NotImplementedError

    @abc.abstractmethod
    def answer_guess(self, guess: Crime) -> RumorCard | None:
        raise NotImplementedError


class NaivePlayer(BasePlayer):
    def __init__(self, **kwargs):
        super().__init(**kwargs)
        self._remaining_possible_rumors = deepcopy(RUMORS)
        for rumor_card in self._rumor_cards:
            self._remaining_possible_rumors.remove(rumor_card)
