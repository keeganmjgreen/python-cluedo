from __future__ import annotations

import abc
import dataclasses
from collections.abc import Sequence
from typing import NamedTuple, Self

CHARACTER_NAMES = [
    "mustard",
    "plum",
    "green",
    "peacock",
    "scarlet",
    "white",
]
WEAPON_NAMES = [
    "knife",
    "candlestick",
    "pistol",
    "poison",
    "trophy",
    "rope",
    "bat",
    "ax",
    "dumbbell",
]
ROOM_NAMES = [
    "hall",
    "dining room",
    "kitchen",
    "patio",
    "observatory",
    "theater",
    "living room",
    "spa",
    "guest house",
]


@dataclasses.dataclass
class RumorCard(abc.ABC):
    name: str

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.name.title()}"

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    @abc.abstractmethod
    def instances(cls) -> Sequence[Self]:
        raise NotImplementedError


class Room(RumorCard):
    @classmethod
    def instances(cls) -> Sequence[Room]:
        return ROOMS


class Weapon(RumorCard):
    @classmethod
    def instances(cls) -> Sequence[Weapon]:
        return WEAPONS


class Character(RumorCard):
    @classmethod
    def instances(cls) -> Sequence[Character]:
        return CHARACTERS


RUMOR_TYPES: list[type[Character | Weapon | Room]] = [Character, Weapon, Room]

CHARACTERS: list[Character] = [Character(name=n) for n in CHARACTER_NAMES]
WEAPONS: list[Weapon] = [Weapon(name=n) for n in WEAPON_NAMES]
ROOMS: list[Room] = [Room(name=n) for n in ROOM_NAMES]

RUMORS: list[Character | Weapon | Room] = [*CHARACTERS, *WEAPONS, *ROOMS]


def parse_rumor(rumor_name: str) -> RumorCard | None:
    if rumor_name in CHARACTER_NAMES:
        return Character(name=rumor_name)
    elif rumor_name in WEAPON_NAMES:
        return Weapon(name=rumor_name)
    elif rumor_name in ROOM_NAMES:
        return Room(name=rumor_name)
    else:
        return None


class Crime(NamedTuple):
    character: Character
    weapon: Weapon
    room: Room


N_CASE_FILE_CARDS = len(Crime._fields)
