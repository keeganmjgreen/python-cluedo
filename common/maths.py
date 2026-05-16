from __future__ import annotations

import abc
import dataclasses
import itertools
from collections.abc import Sequence

from common.agent_utils import AgentIndex, CaseFile
from common.cards import RumorCard
from common.consts import ExtraCards

Cnf = list[list[int]]
CardLocation = AgentIndex | CaseFile | ExtraCards


class BooleanStatement(abc.ABC):
    @abc.abstractmethod
    def to_string(self, player_names: list[str]) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def to_cnf(self, variables_to_lits: dict[CardIsInLocation, int]) -> Cnf:
        raise NotImplementedError


@dataclasses.dataclass
class CardIsInLocation(BooleanStatement):
    """A boolean variable representing whether the given `rumor_card` is in the given
    `location`.
    """

    rumor_card: RumorCard
    location: CardLocation

    def to_string(self, player_names: list[str]) -> str:
        location = (
            f"{player_names[self.location].capitalize()}'s hand"
            if isinstance(self.location, int)
            else self.location
        )
        return f"{self.rumor_card.name.title()} card is in {location}"

    def __hash__(self) -> int:
        return hash((self.location, self.rumor_card, type(self).__name__))

    def to_cnf(self, variables_to_lits: dict[CardIsInLocation, int]) -> Cnf:
        return [[variables_to_lits[self]]]


@dataclasses.dataclass
class Not(BooleanStatement):
    operand: CardIsInLocation

    def to_string(self, player_names: list[str]) -> str:
        return f"NOT ({self.operand.to_string(player_names)})"

    def __hash__(self) -> int:
        return hash((self.operand, type(self).__name__))

    def to_cnf(self, variables_to_lits: dict[CardIsInLocation, int]) -> Cnf:
        return [[-variables_to_lits[self.operand]]]


@dataclasses.dataclass
class _Multi(BooleanStatement, abc.ABC):
    operands: Sequence[CardIsInLocation]

    @abc.abstractmethod
    def to_string(self, player_names: list[str]) -> str:
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(tuple(set(self.operands)))


@dataclasses.dataclass
class And(_Multi):
    def to_string(self, player_names: list[str]) -> str:
        return " AND ".join([f"({e.to_string(player_names)})" for e in self.operands])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def to_cnf(self, variables_to_lits: dict[CardIsInLocation, int]) -> Cnf:
        return [[variables_to_lits[e]] for e in self.operands]


@dataclasses.dataclass
class Or(_Multi):
    def to_string(self, player_names: list[str]) -> str:
        return " OR ".join([f"({e.to_string(player_names)})" for e in self.operands])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def to_cnf(self, variables_to_lits: dict[CardIsInLocation, int]) -> Cnf:
        return [[variables_to_lits[e] for e in self.operands]]


@dataclasses.dataclass
class Xor(_Multi):
    def to_string(self, player_names: list[str]) -> str:
        return " XOR ".join([f"({e.to_string(player_names)})" for e in self.operands])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def to_cnf(self, variables_to_lits: dict[CardIsInLocation, int]) -> Cnf:
        combinations = list(
            itertools.combinations([-variables_to_lits[e] for e in self.operands], 2)
        )
        combinations = [list(c) for c in combinations]
        return [[variables_to_lits[e] for e in self.operands]] + combinations
