from collections.abc import Sequence

from common.agent_utils import BasePlayer
from common.cards import (
    CHARACTER_NAMES,
    ROOM_NAMES,
    RUMOR_TYPES,
    RUMORS,
    WEAPON_NAMES,
    Character,
    Crime,
    Room,
    RumorCard,
    Weapon,
)


class UserPlayer(BasePlayer):
    def try_solving_crime(self) -> Crime | None:
        while True:
            print(
                f"{self._prefix}: Do you want to try solving the crime? (y/N): ", end=""
            )
            choice = input().lower()
            if choice == "":
                choice = "n"
            if choice.strip() in ["y", "yes"]:
                return self._get_crime()
            elif choice.strip() in ["n", "no"]:
                return None
            print(f"{self._prefix}: Invalid choice.")

    def make_guess(self, turn_index: int | None = None) -> Crime:
        print(f"{self._prefix}: It's your turn to make a guess.")
        return self._get_crime()

    def answer_guess(self, guess: Crime) -> RumorCard | None:
        options = set(guess) & set(self.rumor_cards)
        if len(options) == 0:
            return None
        if len(options) == 1:
            return options.pop()
        else:
            return self._get_rumor_card(
                "Select a rumor card in answer to the guess", list(options)
            )

    def _get_crime(self) -> Crime:
        guess = Crime(
            **{
                f: self._get_rumor_card(f"Select a {f}", rt.instances())
                for f, rt in zip(Crime._fields, RUMOR_TYPES, strict=True)
            }  # type: ignore
        )
        return guess

    def _get_rumor_card(
        self, prompt: str, options: Sequence[RumorCard] | None = None
    ) -> RumorCard:
        if options is None:
            options = RUMORS
        if len(options) == 0:
            raise ValueError
        while True:
            rumor_name = input(
                f"{self._prefix}: {prompt} ({', '.join(o.name for o in options)}): "
            )
            if rumor_name in CHARACTER_NAMES:
                rumor = Character(name=rumor_name)
            elif rumor_name in WEAPON_NAMES:
                rumor = Weapon(name=rumor_name)
            elif rumor_name in ROOM_NAMES:
                rumor = Room(name=rumor_name)
            else:
                print(f"{self._prefix}: Invalid rumor.")
                continue
            if rumor in options:
                return rumor
            print(f"{self._prefix}: Invalid rumor.")

    @property
    def _prefix(self) -> str:
        return f"Player {self.agent_index}"
