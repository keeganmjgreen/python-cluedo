import dataclasses
from collections.abc import Sequence
from time import sleep
from typing import cast

from common.cards import (
    CHARACTER_NAMES,
    ROOM_NAMES,
    RUMORS,
    WEAPON_NAMES,
    Character,
    Room,
    Weapon,
)
from common.consts import MIN_N_PLAYERS
from common.io.io import format_list


@dataclasses.dataclass
class TextIo:
    pause_seconds: float = 0.5

    def get_human_player_names(self) -> list[str]:
        self.print_(
            "Please provide the player names in turn order, beginning with the starting player."
        )
        current_player_num = 1
        player_names: list[str] = []

        while True:
            player_name = self.input_(
                f"Player {current_player_num} name{f' (<Enter> if no player {current_player_num})' if len(player_names) >= MIN_N_PLAYERS else ''}: ",
            )
            if player_name is None:
                n_players = len(player_names)
                if n_players >= MIN_N_PLAYERS:
                    break
                else:
                    self.print_(
                        f"There must be at least {MIN_N_PLAYERS} players.", end=" "
                    )
                    continue
            elif player_name.lower() in [n.lower() for n in player_names]:
                self.print_("Player names must be unique.", end=" ")
                continue
            else:
                player_names.append(player_name)
                current_player_num += 1
                continue

        return player_names

    def announce_turn(self, turn_index: int, player_name: str) -> None:
        self.print_(f"It's {player_name.capitalize()}'s turn.")

    def get_rumor_card[T: Character | Weapon | Room](
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T:
        if len(options) == 0:
            raise ValueError
        while True:
            rumor_name = self.input_(
                f"{prompt} ({format_list([o.name for o in options])}): ",
                prefix,
                lower=True,
            )
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

    def get_player_index(
        self, player_indexes: list[int], all_player_names: list[str]
    ) -> int | None:
        # TODO: Make more user-friendly?
        while True:
            player_name = self.input_(
                f"Enter player name (<Enter> for no player) ({format_list([all_player_names[i] for i in player_indexes], 'or')}): ",
                lower=True,
            )
            if player_name is None:
                return None
            elif player_name in [all_player_names[i].lower() for i in player_indexes]:
                return [n.lower() for n in all_player_names].index(player_name)
            else:
                self.print_("Invalid player.", end=" ")

    def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool:
        y = "Y" if default is True else "y"
        n = "N" if default is False else "n"
        while True:
            choice = self.input_(f"{prompt} ({y}/{n}): ", prefix, lower=True)
            if choice is None:
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

    def input_(
        self,
        prompt: str,
        prefix: str | None = None,
        pause: bool = True,
        lower: bool = False,
    ) -> str | None:
        self.print_(prompt, prefix, end="")
        result = input()
        if pause:
            sleep(self.pause_seconds)
        if lower:
            result = result.lower()
        return result or None
