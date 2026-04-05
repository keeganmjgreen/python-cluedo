import dataclasses
from typing import NamedTuple

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
class RumorCard:
    name: str

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.name.title()}"

    def __hash__(self) -> int:
        return hash(self.name)


class Room(RumorCard):
    pass


class Weapon(RumorCard):
    pass


class Character(RumorCard):
    pass


RUMOR_TYPES = [Character, Weapon, Room]

CHARACTERS = [Character(name=n) for n in CHARACTER_NAMES]
WEAPONS = [Weapon(name=n) for n in WEAPON_NAMES]
ROOMS = [Room(name=n) for n in ROOM_NAMES]

RUMORS = CHARACTERS + WEAPONS + ROOMS


class Crime(NamedTuple):
    character: Character
    weapon: Weapon
    room: Room


N_CASE_FILE_CARDS = len(Crime._fields)
