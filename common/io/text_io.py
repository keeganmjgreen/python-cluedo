import dataclasses
from collections.abc import Sequence
from time import sleep
from typing import cast

from common.cards import (
    RUMORS,
    Character,
    Room,
    RumorCard,
    Weapon,
    parse_rumor,
)
from common.consts import MIN_N_PLAYERS, GameVariant
from common.io.io import AbstractIo, format_list


@dataclasses.dataclass
class TextIo(AbstractIo):
    pause_seconds: float = 0.5

    def get_human_player_names(self) -> list[str]:
        self.print_(self._PLAYER_NAMES_PROMPT)
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

    def get_extra_cards(self, n_extra_cards: int) -> list[RumorCard]:
        extra_cards = []
        # TODO: Select from list narrowed down by observer.
        options = RUMORS
        extra_cards: list[RumorCard] = []
        for i in range(n_extra_cards):
            extra_card = self.get_rumor_card(
                prompt=f"Enter extra card #{i + 1}/{n_extra_cards}",
                options=options,
            )
            extra_cards.append(extra_card)
            options = [o for o in options if o != extra_card]
        return extra_cards

    def get_game_variant(self) -> GameVariant:
        options = [gv.value for gv in GameVariant]
        while True:
            option = self.input_(
                f"{self._GAME_VARIANT_PROMPT} "
                f"({format_list([f'{i + 1} = {o}' for i, o in enumerate(options)])}): "
            )
            if option is None:
                self.print_("Invalid number.", end=" ")
                continue
            try:
                number = int(option)
            except ValueError:
                self.print_("Invalid number.", end=" ")
                continue
            if number < 1 or number > len(options):
                self.print_("Invalid number.", end=" ")
                continue
            return GameVariant(options[number - 1])

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
            if rumor_name is None or (rumor_card := parse_rumor(rumor_name)) is None:
                self.print_("Invalid rumor.", prefix, end=" ")
                continue
            if rumor_card in options:
                return cast(T, rumor_card)
            self.print_("Invalid option.", prefix, end=" ")

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
