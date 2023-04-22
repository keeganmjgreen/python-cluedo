from typing import Union

from src.common.agent_utils import BasePlayer
from src.common.cards import (
    CHARACTER_NAMES,
    ROOM_NAMES,
    RUMOR_TYPES,
    WEAPON_NAMES,
    Character,
    Crime,
    Room,
    RumorCard,
    Weapon,
)


class UserPlayer(BasePlayer):
    def make_guess(self) -> Crime:
        # TODO: Improve:
        guess = Crime(
            **{
                f: rt(name=self._input(f"{f}: "))
                for f, rt in zip(Crime._fields, RUMOR_TYPES)
            }
        )
        return guess

    def answer_guess(self, guess: Crime) -> Union[RumorCard, None]:
        rumor_options = set(guess) & set(self._rumor_cards)
        if len(rumor_options) == 0:
            return None
        else:
            # TODO: Improve:
            print([r.name for r in rumor_options])
            rumor_name = self._input("Choose which card to show: ")
            if rumor_name in CHARACTER_NAMES:
                return Character(name=rumor_name)
            elif rumor_name in WEAPON_NAMES:
                return Weapon(name=rumor_name)
            elif rumor_name in ROOM_NAMES:
                return Room(name=rumor_name)
            else:
                raise ValueError
