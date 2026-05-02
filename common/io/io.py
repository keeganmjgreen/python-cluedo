from collections.abc import Sequence
from typing import Any, Protocol

from common.cards import RUMORS, Character, Room, RumorCard, Weapon


class AbstractIo(Protocol):
    def get_human_player_names(self) -> list[str]: ...

    def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool: ...

    def get_extra_cards(self, n_extra_cards: int) -> list[RumorCard]: ...

    def announce_turn(self, turn_index: int, player_name: str) -> None: ...

    def get_rumor_card[T: Character | Weapon | Room](
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T: ...

    def get_player_index(
        self, player_indexes: list[int], all_player_names: list[str]
    ) -> int | None: ...

    def print_(self, msg: str, prefix: str | None = None, end: str = "\n") -> None: ...


def format_list(items: list[Any], sep: str = "or") -> str:
    if len(items) == 1:
        return f"{items[0]}"
    if len(items) == 2:
        return f"{items[0]} {sep} {items[1]}"
    return ", ".join(items[:-1]) + f", {sep} " + items[-1]
