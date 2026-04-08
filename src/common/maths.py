from __future__ import annotations

import abc
import dataclasses
import itertools
from collections.abc import Sequence

from common.agent_utils import AgentIndex, CaseFile
from common.cards import RumorCard
from common.consts import ExtraCards

type CNF = list[list[int]]


class BooleanStatement(abc.ABC):
    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def to_cnf(self, variable_indices: dict[CardIsInLocation, int]) -> CNF:
        raise NotImplementedError


@dataclasses.dataclass
class CardIsInLocation(BooleanStatement):
    """A boolean variable representing whether the given `rumor_card` is in the given
    `location`.
    """

    rumor_card: RumorCard
    location: AgentIndex | CaseFile | ExtraCards

    def __str__(self) -> str:
        return f"player {self.location} has {self.rumor_card.name} card"

    def __hash__(self) -> int:
        return hash((self.location, self.rumor_card, type(self).__name__))

    def to_cnf(self, variable_indices: dict[CardIsInLocation, int]) -> CNF:
        return [[variable_indices[self]]]


@dataclasses.dataclass
class Not(BooleanStatement):
    operand: CardIsInLocation

    def __str__(self) -> str:
        return f"¬({self.operand})"

    def __hash__(self) -> int:
        return hash((self.operand, type(self).__name__))

    def to_cnf(self, variable_indices: dict[CardIsInLocation, int]) -> CNF:
        return [[-variable_indices[self.operand]]]


@dataclasses.dataclass
class _Multi(BooleanStatement, abc.ABC):
    operands: Sequence[CardIsInLocation]

    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(tuple(set(self.operands)))


@dataclasses.dataclass
class And(_Multi):
    def __str__(self) -> str:
        return " ^ ".join([f"({e})" for e in self.operands])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def to_cnf(self, variable_indices: dict[CardIsInLocation, int]) -> CNF:
        return [[variable_indices[e]] for e in self.operands]


@dataclasses.dataclass
class Or(_Multi):
    def __str__(self) -> str:
        return " v ".join([f"({e})" for e in self.operands])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def to_cnf(self, variable_indices: dict[CardIsInLocation, int]) -> CNF:
        return [[variable_indices[e] for e in self.operands]]


@dataclasses.dataclass
class Xor(_Multi):
    def __str__(self) -> str:
        return " ⨁ ".join([f"({e})" for e in self.operands])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def to_cnf(self, variable_indices: dict[CardIsInLocation, int]) -> CNF:
        combinations = list(
            itertools.combinations([-variable_indices[e] for e in self.operands], 2)
        )
        combinations = [list(c) for c in combinations]
        return [[variable_indices[e] for e in self.operands]] + combinations
