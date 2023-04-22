import dataclasses
import itertools
from time import time
from typing import Callable, List, Literal, Tuple, Union

import numpy as np
import pandas as pd
import scipy.optimize
from pysat.card import CardEnc
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver

from src.common.agent_utils import (
    CASE_FILE,
    EXTRA_CARDS,
    BaseObserver,
    BasePlayer,
    GameLogEntry,
    UnknownRumor,
    agent_index_type,
)
from src.common.cards import (
    CHARACTERS,
    N_CASE_FILE_CARDS,
    ROOMS,
    RUMOR_TYPES,
    RUMORS,
    WEAPONS,
    Crime,
    RumorCard,
)
from src.common.maths import (
    EventsSymmetricDifference,
    EventsUnion,
    ProbabilityEquation,
    ProbabilityEvent,
    ProbabilityExpression,
    ProbabilityVariable,
)
from src.common.utils import shuffled, sign

GUESS_MAKING_STRATEGY_TYPE = Literal[
    "random",  # Moderate performance.
    "first-free-case-file-variables",  # Worst performance.
    "random-first-free-case-file-variables",  # Best performance.
    "new-guess-rumor",  # Not yet implemented.
]
GUESS_ANSWERING_STRATEGY_TYPE = Literal["first", "random"]


@dataclasses.dataclass
class PlayerHasCard(ProbabilityEvent):
    player_index: Union[agent_index_type, Literal["case-file"], Literal["extra-cards"]]
    rumor_card: RumorCard

    def __str__(self):
        return f"player {self.player_index} has {self.rumor_card.name} card"

    def __hash__(self) -> int:
        return hash((self.player_index, self.rumor_card))


class UnsolvableError(Exception):
    pass


class SmartBotObserver(BaseObserver):
    rumor_cards: List[RumorCard] = []
    _game_log: List[GameLogEntry]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._free_case_file_variables_ser = pd.Series(dtype=object).rename_axis(
            "turn_index"
        )

    @property
    def n_extra_cards(self):
        n_players = len(self.player_indices)
        return (len(RUMORS) - N_CASE_FILE_CARDS) % n_players

    def _game_log_to_truth_equations(self) -> List[ProbabilityEquation]:
        equations = []
        # GENERAL KNOWLEDGE OF THE GAME...
        # The case file contains exactly one character, weapon, and room:
        for rumor_cards in [CHARACTERS, WEAPONS, ROOMS]:
            equations.append(
                ProbabilityEquation(
                    lhs=ProbabilityExpression(
                        event=EventsSymmetricDifference(
                            events=[
                                PlayerHasCard(
                                    player_index=CASE_FILE,
                                    rumor_card=rc,
                                )
                                for rc in rumor_cards
                            ]
                        )
                    ),
                    rhs=1,
                )
            )
        # Each rumor card is owned by exactly one of the players including the case file and extra
        #     cards:
        for rumor_card in RUMORS:
            equations.append(
                ProbabilityEquation(
                    lhs=ProbabilityExpression(
                        event=EventsSymmetricDifference(
                            events=[
                                PlayerHasCard(
                                    player_index=pi,
                                    rumor_card=rumor_card,
                                )
                                for pi in self.player_indices
                                + [CASE_FILE]
                                + [EXTRA_CARDS]
                            ],
                        )
                    ),
                    rhs=1,
                )
            )
        # PLAYER KNOWLEDGE ACCUMULATED DURING GAMEPLAY...
        for game_log_entry in self._game_log:
            for card_reveal in game_log_entry.card_reveals:
                if card_reveal.rumor_card == UnknownRumor():
                    assert game_log_entry.turn_player_index != self.agent_index
                    # If a player A (can be this player) shows another player B (cannot be this
                    #     player) a rumor card, then this player knows that player A has at
                    #     least one of the rumor cards in player B's guess:
                    # This player does not know that specific rumor card.
                    equations.append(
                        ProbabilityEquation(
                            lhs=ProbabilityExpression(
                                event=EventsUnion(
                                    [
                                        PlayerHasCard(
                                            player_index=card_reveal.other_player_index,
                                            rumor_card=rc,
                                        )
                                        for rc in game_log_entry.guess
                                    ]
                                )
                            ),
                            rhs=1,
                        )
                    )
                elif card_reveal.rumor_card is not None:
                    # If another player has shown this player a rumor card, then this player
                    #     knows that that other player has that rumor card:
                    equations.append(
                        ProbabilityEquation(
                            lhs=ProbabilityExpression(
                                event=PlayerHasCard(
                                    player_index=card_reveal.other_player_index,
                                    rumor_card=card_reveal.rumor_card,
                                )
                            ),
                            rhs=1,
                        )
                    )
                else:
                    for rumor_card in game_log_entry.guess:
                        # If a player A (can be this player) does not show another player B (cannot
                        #     be this player) a rumor card, then this player knows that player A
                        #     does have any of the rumor cards in player B's guess:
                        equations.append(
                            ProbabilityEquation(
                                lhs=ProbabilityExpression(
                                    event=PlayerHasCard(
                                        player_index=card_reveal.other_player_index,
                                        rumor_card=rumor_card,
                                    )
                                ),
                                rhs=0,
                            )
                        )
        equations = list(set(equations))  # Remove duplicates.  # TODO: Preserve order?
        return equations

    def _get_all_variables(
        self,
    ) -> Tuple[List[ProbabilityVariable], pd.Series, pd.MultiIndex]:
        all_variables = [
            ProbabilityVariable(event=PlayerHasCard(player_index=pi, rumor_card=rc))
            for pi in self.player_indices + [CASE_FILE] + [EXTRA_CARDS]
            for rc in RUMORS
        ]
        all_variable_indices = (
            pd.Series(all_variables, name="variable")
            .reset_index()
            .set_index("variable")
        )["index"].astype(object) + 1
        all_variables_multiindex = pd.MultiIndex.from_tuples(
            [(v.event.player_index, str(v.event.rumor_card)) for v in all_variables],
            names=["player_index", "rumor_card"],
        )
        return all_variables, all_variable_indices, all_variables_multiindex

    def _equations_to_truths_func(
        self,
        equations: List[ProbabilityEquation],
        all_variables: List[ProbabilityVariable],
    ) -> Callable:
        def truths_func(x: np.ndarray) -> float:
            # TODO: Speed-up objective function evaluation.
            start_time = time()
            probability_values = pd.Series(
                x, index=all_variables, name="probability_value"
            )
            return_val = [
                eq.lhs.evaluate(probability_values=probability_values[eq.lhs.variables])
                - eq.rhs
                for eq in equations
            ]
            print(x)
            print(return_val)
            print(f"truths_func eval time: {(time() - start_time):.1} s")
            return return_val

        return truths_func

    def _solve_truths_func(self, x0_scalar: float = 0.5):
        # TODO: Specify Jacobian?
        equations = self._game_log_to_truth_equations()
        all_variables, _, _ = self._get_all_variables()
        truths_func = self._equations_to_truths_func(
            equations=equations, all_variables=all_variables
        )
        x0 = pd.Series(x0_scalar, index=all_variables).to_numpy()
        x = scipy.optimize.least_squares(
            fun=truths_func, x0=x0, bounds=(0, 1), verbose=2
        )
        return pd.Series(x, index=all_variables)

    def _equations_to_cnf_clauses(
        self,
        equations: List[ProbabilityEquation],
        all_variable_indices: pd.Series,
        all_variables_multiindex: pd.MultiIndex,
    ) -> List[List[int]]:
        clauses = []
        for eq in equations:
            clauses.extend(eq.to_cnf(variable_indices=all_variable_indices))
        id_pool = IDPool(start_from=1, occupied=[[1, len(all_variable_indices)]])
        for player_index in self.player_indices:
            clauses.extend(
                CardEnc.equals(
                    lits=all_variable_indices.set_axis(all_variables_multiindex)[
                        player_index
                    ].tolist(),
                    bound=self.n_cards_per_player,
                    vpool=id_pool,
                ).clauses
            )
        clauses = [
            list(c) for c in list(set(tuple(c) for c in clauses))
        ]  # TODO: Remove?
        n_lits = id_pool.top
        return clauses, n_lits

    def _solve_truths_cnf_probabilities(self, n_samples: int = 10):
        (
            all_variables,
            all_variable_indices,
            all_variables_multiindex,
        ) = self._get_all_variables()
        equations = self._game_log_to_truth_equations()
        clauses, n_lits = self._equations_to_cnf_clauses(
            equations, all_variable_indices, all_variables_multiindex
        )
        solution_sers = []
        for i in range(n_samples):
            orig_lit_indices = list(range(1, 1 + n_lits))
            random_lit_indices = shuffled(orig_lit_indices)
            orig2random_lit_index_mapping = dict(
                zip(orig_lit_indices, random_lit_indices)
            )
            random_clauses = [
                [sign(lit) * orig2random_lit_index_mapping[abs(lit)] for lit in clause]
                for clause in clauses
            ]
            cnf = CNF(
                from_clauses=shuffled([shuffled(lits) for lits in random_clauses])
            )
            with Solver(bootstrap_with=cnf) as solver:
                solver.solve()
                solution: List[int] = solver.get_model()
            random2orig_lit_index_mapping = {
                v: k for k, v in orig2random_lit_index_mapping.items()
            }
            solution = sorted(
                [
                    sign(lit) * random2orig_lit_index_mapping[abs(lit)]
                    for lit in solution
                ],
                key=abs,
            )
            solution_ser = pd.Series(
                solution[: len(all_variables)], index=all_variables_multiindex
            ).apply(lambda x: 1 if x > 0 else 0)
            solution_sers.append(solution_ser)
        probabilities_ser = (
            pd.concat(solution_sers, axis="columns")
            .mean(axis="columns")
            .rename("approx_probability")
        )
        return probabilities_ser

    def _must_see_extra_cards(self, turn_index: int = None) -> bool:
        free_case_file_variables = self._free_case_file_variables_getter(turn_index)
        must_see_extra_cards = (
            0 < len(free_case_file_variables) - 1 <= self.n_extra_cards
        )
        return must_see_extra_cards

    def _free_case_file_variables_getter(self, turn_index: Union[int, None] = None):
        if turn_index in self._free_case_file_variables_ser.index:
            free_case_file_variables = self._free_case_file_variables_ser[turn_index]
        else:
            _, free_case_file_variables = self._solve_truths_cnf()
            if turn_index is not None:
                self._free_case_file_variables_ser.loc[
                    turn_index
                ] = free_case_file_variables
        return free_case_file_variables

    def _solve_truths_cnf(self) -> Tuple[Union[Crime, None], List[ProbabilityVariable]]:
        (
            all_variables,
            all_variable_indices,
            all_variables_multiindex,
        ) = self._get_all_variables()
        equations = self._game_log_to_truth_equations()
        clauses, _ = self._equations_to_cnf_clauses(
            equations, all_variable_indices, all_variables_multiindex
        )
        cnf = CNF(from_clauses=clauses)
        with Solver(bootstrap_with=cnf) as solver:
            solvable = solver.solve()
            if not solvable:
                raise UnsolvableError
            solution: List[int] = solver.get_model()
            free_case_file_variables = []
            for rumor_card in RUMORS:
                case_file_variable = ProbabilityVariable(
                    event=PlayerHasCard(player_index=CASE_FILE, rumor_card=rumor_card)
                )
                case_file_variable_index = all_variable_indices[case_file_variable]
                if +case_file_variable_index in solution:
                    assumptions = [-case_file_variable_index]
                elif -case_file_variable_index in solution:
                    assumptions = [+case_file_variable_index]
                if solver.solve(assumptions=assumptions):
                    free_case_file_variables.append(case_file_variable)
        if len(free_case_file_variables) == 0:
            solution_ser = pd.Series(
                solution[: len(all_variables)], index=all_variables
            ).apply(lambda x: 1 if x > 0 else 0)
            return solution_ser, free_case_file_variables
        else:
            return None, free_case_file_variables

    def _try_solving_crime(self) -> Union[None, Crime]:
        result, _ = self._solve_truths_cnf()
        if result is not None:
            solution_ser = result
            case_file_solution_ser = solution_ser[
                [v for v in solution_ser.index if v.event.player_index == CASE_FILE]
            ]
            crime_cards = [
                v.event.rumor_card
                for v in case_file_solution_ser[case_file_solution_ser == 1].index
            ]
            return Crime(*crime_cards)
        else:
            return None


class SmartBotPlayer(BasePlayer, SmartBotObserver):
    guess_making_strategy: GUESS_MAKING_STRATEGY_TYPE
    guess_answering_strategy: GUESS_ANSWERING_STRATEGY_TYPE
    remaining_unique_guesses: List[Crime]

    def __init__(
        self,
        guess_making_strategy: GUESS_MAKING_STRATEGY_TYPE = "random-free-case-file-variables",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.guess_making_strategy = guess_making_strategy
        self.remaining_unique_guesses = [
            Crime(*x) for x in itertools.product(CHARACTERS, WEAPONS, ROOMS)
        ]

    def make_guess(self, turn_index: int = None) -> Crime:
        if self.guess_making_strategy == "random":
            guess = Crime(
                character=shuffled(CHARACTERS)[0],
                weapon=shuffled(WEAPONS)[0],
                room=shuffled(ROOMS)[0],
            )
        elif self.guess_making_strategy in [
            "first-free-case-file-variables",
            "random-free-case-file-variables",
        ]:
            free_case_file_variables = self._free_case_file_variables_getter(turn_index)
            case_file_variables = [
                ProbabilityVariable(
                    event=PlayerHasCard(player_index=CASE_FILE, rumor_card=rc)
                )
                for rc in RUMORS
            ]
            _rumor_cards_getter = lambda case_file_vars: [
                var.event.rumor_card
                for var in case_file_vars
                if type(var.event.rumor_card) == rumor_type
            ]
            crime_cards = {}
            for rumor_type in RUMOR_TYPES:
                rumor_cards = _rumor_cards_getter(free_case_file_variables)
                if len(rumor_cards) == 0:
                    rumor_cards = _rumor_cards_getter(case_file_variables)
                if self.guess_making_strategy == "random-free-case-file-variables":
                    rumor_cards = shuffled(rumor_cards)
                crime_cards[rumor_type] = rumor_cards[0]
            guess = Crime(*crime_cards.values())
        return guess

    def answer_guess(self, guess: Crime) -> Union[RumorCard, None]:
        for rumor_card in shuffled(self._rumor_cards):
            for rumor in guess:
                if rumor_card == rumor:
                    return rumor_card
        return None

    def _game_log_to_truth_equations(self) -> List[ProbabilityEquation]:
        equations = super()._game_log_to_truth_equations()
        # PLAYER KNOWLEDGE OF THE GAME INSTANCE...
        # This player owns their own rumor cards and only those rumor cards:
        for rumor_card in RUMORS:
            equations.append(
                ProbabilityEquation(
                    lhs=ProbabilityExpression(
                        event=PlayerHasCard(
                            player_index=self.agent_index,
                            rumor_card=rumor_card,
                        )
                    ),
                    rhs=(1 if rumor_card in self._rumor_cards else 0),
                )
            )
        equations = list(set(equations))  # Remove duplicates.  # TODO: Preserve order?
        return equations
