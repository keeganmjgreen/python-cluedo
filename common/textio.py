import dataclasses
from collections.abc import Sequence
from time import sleep
from typing import Any, cast

from common.cards import (
    CHARACTER_NAMES,
    ROOM_NAMES,
    RUMORS,
    WEAPON_NAMES,
    Character,
    Room,
    Weapon,
)


@dataclasses.dataclass
class TextIo:
    pause_seconds: float = 0.5

    def get_rumor_card[T: Character | Weapon | Room](
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T:
        if len(options) == 0:
            raise ValueError
        while True:
            rumor_name = self.input_(
                f"{prompt} ({format_list([o.name for o in options])}): ", prefix
            ).lower()
            if rumor_name in CHARACTER_NAMES:
                rumor = Character(name=rumor_name)
            elif rumor_name in WEAPON_NAMES:
                rumor = Weapon(name=rumor_name)
            elif rumor_name in ROOM_NAMES:
                rumor = Room(name=rumor_name)
            else:
                self.print_("Invalid rumor.", prefix, end=" ")
                continue
            if rumor in options:
                return cast(T, rumor)
            self.print_("Invalid rumor.", prefix, end=" ")

    def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool:
        y = "Y" if default is True else "y"
        n = "N" if default is False else "n"
        while True:
            choice = self.input_(f"{prompt} ({y}/{n}): ", prefix).lower()
            if choice == "":
                choice = "y" if default is True else "n"
            if choice.strip() in ["y", "yes"]:
                return True
            elif choice.strip() in ["n", "no"]:
                return False
            self.print_("Invalid choice.", prefix)

    def print_(self, msg: str, prefix: str | None = None, end: str = "\n") -> None:
        if prefix is not None:
            msg = f"{prefix}: {msg}"
        print(msg, end=end)
        if end == "\n":
            sleep(self.pause_seconds)

    def input_(self, prompt: str, prefix: str | None = None, pause: bool = True) -> str:
        self.print_(prompt, prefix, end="")
        result = input()
        if pause:
            sleep(self.pause_seconds)
        return result


def format_list(items: list[Any], sep: str = "or") -> str:
    if len(items) == 2:
        return f"{items[0]} {sep} {items[1]}"
    return ", ".join(items[:-1]) + f", {sep} " + items[-1]
