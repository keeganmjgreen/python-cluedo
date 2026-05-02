import abc
from collections.abc import Sequence
from typing import Any

from common.cards import RUMORS, Character, Room, RumorCard, Weapon
from common.consts import GameVariant


class AbstractIo(abc.ABC):
    @abc.abstractmethod
    def get_human_player_names(self) -> list[str]:
        raise NotImplementedError

    _PLAYER_NAMES_PROMPT = (
        "Please provide the player names in turn order (counterclockwise), "
        "beginning with the starting player."
    )

    @abc.abstractmethod
    def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def get_extra_cards(self, n_extra_cards: int) -> list[RumorCard]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_game_variant(self) -> GameVariant:
        raise NotImplementedError

    _GAME_VARIANT_PROMPT = (
        "Which game variant would you like to play? "
        "This determines whether players reveal rumor cards to the current player "
        "starting directly on their left (standard Cluedo), on their right, or both "
        "sides. "
    )

    @abc.abstractmethod
    def announce_turn(self, turn_index: int, player_name: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_rumor_card[T: Character | Weapon | Room](
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def get_player_index(
        self, player_indexes: list[int], all_player_names: list[str]
    ) -> int | None:
        raise NotImplementedError

    @abc.abstractmethod
    def print_(self, msg: str, prefix: str | None = None, end: str = "\n") -> None:
        raise NotImplementedError


def format_list(items: list[Any], sep: str = "or") -> str:
    if len(items) == 1:
        return f"{items[0]}"
    if len(items) == 2:
        return f"{items[0]} {sep} {items[1]}"
    return ", ".join(items[:-1]) + f", {sep} " + items[-1]
