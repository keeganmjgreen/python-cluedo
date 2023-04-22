from __future__ import annotations

import abc
import dataclasses
import itertools
from typing import List, Union

import numpy as np
import pandas as pd

cnf_type = List[List[int]]


@dataclasses.dataclass
class ProbabilityEvent:
    @property
    def variables(self) -> List[ProbabilityVariable]:
        return [ProbabilityVariable(event=self)]

    def evaluate_probability(self, probability_values: pd.Series) -> float:
        return probability_values[self.variables[0]]

    def math_str(self):
        return str(ProbabilityExpression(event=self))

    def to_cnf(self, variable_indices: pd.Series, inverse: bool):
        variable_index = variable_indices.loc[self.variables[0]]
        return [[variable_index if not inverse else -variable_index]]


class Variable(abc.ABC):
    @property
    def variables(self) -> List[Variable]:
        return [self]


@dataclasses.dataclass
class ProbabilityVariable(Variable):
    event: ProbabilityEvent

    def __str__(self):
        return f"P({self.event})"

    def __hash__(self) -> int:
        return hash(self.event)


@dataclasses.dataclass
class MultiEvent(ProbabilityEvent):
    events: List[ProbabilityEvent]

    def __hash__(self) -> int:
        return hash(tuple(set(self.events)))

    @property
    def variables(self) -> List[ProbabilityVariable]:
        variables = []
        for event in self.events:
            variables.extend(event.variables)
        return variables

    def evaluate_probability(self, probability_values: pd.Series) -> float:
        raise NotImplementedError

    def _pre_cnf_check(self, inverse: bool) -> None:
        assert not inverse
        assert all([not isinstance(e, MultiEvent) for e in self.events])


@dataclasses.dataclass
class EventsIntersection(MultiEvent):
    # Note: Events are independent.

    def __str__(self):
        return " n ".join([f"({e})" for e in self.events])

    def __hash__(self) -> int:
        return hash((super(), type(self).__name__))

    def evaluate_probability(self, probability_values: pd.Series) -> float:
        return np.prod(
            [
                e.evaluate_probability(
                    probability_values=probability_values[e.variables]
                )
                for e in self.events
            ]
        )

    def math_str(self):
        return " * ".join([f"({e.math_str()})" for e in self.events])

    def to_cnf(self, variable_indices: pd.Series, inverse: bool):
        super()._pre_cnf_check(inverse)
        return [[variable_indices.loc[e.variables[0]]] for e in self.events]


@dataclasses.dataclass
class EventsSymmetricDifference(MultiEvent):
    # Note: Events are mutually exclusive.

    def __str__(self):
        return " ^ ".join([f"({e})" for e in self.events])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def evaluate_probability(self, probability_values: pd.Series) -> float:
        return np.sum(
            [
                e.evaluate_probability(
                    probability_values=probability_values[e.variables]
                )
                for e in self.events
            ]
        )

    def math_str(self):
        return " + ".join([f"({e.math_str()})" for e in self.events])

    def to_cnf(self, variable_indices: pd.Series, inverse: bool):
        super()._pre_cnf_check(inverse)
        combinations = list(
            itertools.combinations(
                [-variable_indices.loc[e.variables[0]] for e in self.events], 2
            )
        )
        combinations = [list(c) for c in combinations]
        return [
            [variable_indices.loc[e.variables[0]] for e in self.events]
        ] + combinations


@dataclasses.dataclass
class EventsUnion(MultiEvent):
    # Note: Events are not mutually exclusive.

    def __str__(self):
        return " u ".join([f"({e})" for e in self.events])

    def __hash__(self) -> int:
        return hash((hash(super()), type(self).__name__))

    def evaluate_probability(self, probability_values: pd.Series) -> float:
        return 1 - np.prod(
            [
                1
                - e.evaluate_probability(
                    probability_values=probability_values[e.variables]
                )
                for e in self.events
            ]
        )

    def math_str(self):
        return f"1 - {' * '.join([f'(1 - ({e.math_str()}))' for e in self.events])}"

    def to_cnf(self, variable_indices: pd.Series, inverse: bool):
        super()._pre_cnf_check(inverse)
        return [[variable_indices.loc[e.variables[0]] for e in self.events]]


class Expression(abc.ABC):
    @property
    def variables(self) -> List[Variable]:
        pass

    def evaluate(self, values) -> float:
        raise NotImplementedError


@dataclasses.dataclass
class ProbabilityExpression(Expression):
    event: ProbabilityEvent

    __str__ = ProbabilityVariable.__str__

    def __hash__(self) -> int:
        return hash(self.event)

    @property
    def variables(self) -> List[ProbabilityVariable]:
        return self.event.variables

    def evaluate(self, probability_values: pd.Series) -> float:
        return self.event.evaluate_probability(probability_values=probability_values)

    def math_str(self):
        return self.event.math_str()

    def to_cnf(self, variable_indices: pd.Series, inverse: bool):
        return self.event.to_cnf(variable_indices=variable_indices, inverse=inverse)


@dataclasses.dataclass
class Equation:
    lhs: Union[Expression, Variable, float, int]
    rhs: Union[Expression, Variable, float, int]

    def __str__(self):
        return f"{self.lhs} = {self.rhs}"

    @property
    def variables(self) -> List[Variable]:
        variables = []
        if hasattr(self.lhs, "variables"):
            variables.extend(self.lhs.variables)
        if hasattr(self.rhs, "variables"):
            variables.extend(self.rhs.variables)
        return variables


@dataclasses.dataclass
class ProbabilityEquation(Equation):
    lhs: ProbabilityExpression
    rhs: float

    def __hash__(self) -> int:
        return hash((self.lhs, self.rhs))

    def math_str(self):
        return f"{self.lhs.math_str()} = {self.rhs}"

    def to_cnf(self, variable_indices: pd.Series):
        if self.rhs == 0:
            return self.lhs.to_cnf(
                variable_indices=variable_indices.loc[self.lhs.variables], inverse=True
            )
        elif self.rhs == 1:
            return self.lhs.to_cnf(
                variable_indices=variable_indices.loc[self.lhs.variables], inverse=False
            )
        else:
            raise Exception
