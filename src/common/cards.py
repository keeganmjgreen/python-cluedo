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
RUMOR_NAMES = CHARACTER_NAMES + WEAPON_NAMES + ROOM_NAMES


class RumorCard:
    pass


@dataclasses.dataclass
class Room(RumorCard):
    name: str

    def __str__(self) -> str:
        return f"Room: {self.name.title()}"

    def __hash__(self) -> int:
        return hash(self.name)


@dataclasses.dataclass
class Weapon(RumorCard):
    name: str

    def __str__(self) -> str:
        return f"Weapon: {self.name.title()}"

    def __hash__(self) -> int:
        return hash(self.name)


@dataclasses.dataclass
class Character(RumorCard):
    name: str

    def __str__(self) -> str:
        return f"Character: {self.name.title()}"

    def __hash__(self) -> int:
        return hash(self.name)


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
