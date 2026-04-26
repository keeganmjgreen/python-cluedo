import dataclasses
import itertools
from enum import Enum
from typing import cast

from pysat.card import CardEnc  # type: ignore
from pysat.formula import CNF, IDPool  # type: ignore
from pysat.solvers import Solver  # type: ignore

from common.agent_utils import (
    CASE_FILE,
    EXTRA_CARDS,
    BaseObserver,
    BasePlayer,
    UnknownRumor,
)
from common.cards import (
    CHARACTERS,
    N_CASE_FILE_CARDS,
    ROOMS,
    RUMOR_TYPES,
    RUMORS,
    WEAPONS,
    Crime,
    RumorCard,
)
from common.maths import (
    BooleanStatement,
    CardIsInLocation,
    CardLocation,
    Cnf,
    Not,
    Or,
    Xor,
)
from common.utils import shuffled, sign


class GuessMakingStrategy(Enum):
    RANDOM = "RANDOM"
    """Moderate performance."""
    FIRST_FREE_CASE_FILE_VARIABLES = "FIRST_FREE_CASE_FILE_VARIABLES"
    """Worst performance."""
    RANDOM_FIRST_FREE_CASE_FILE_VARIABLES = "RANDOM_FIRST_FREE_CASE_FILE_VARIABLES"
    """Best performance."""
    NEW_GUESS_RUMOR = "NEW_GUESS_RUMOR"
    """Not yet implemented."""


class GuessAnsweringStrategy(Enum):
    FIRST = "FIRST"
    """Moderate performance."""
    RANDOM = "RANDOM"
    """Not yet implemented."""


class UnsolvableError(Exception):
    pass


@dataclasses.dataclass
class SmartBotObserver(BaseObserver):
    _free_case_file_variables: dict[int, list[CardIsInLocation]] = dataclasses.field(
        init=False
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        self._free_case_file_variables = {}

    @property
    def n_extra_cards(self) -> int:
        n_players = len(self.player_indices)
        return (len(RUMORS) - N_CASE_FILE_CARDS) % n_players

    def _game_log_to_boolean_statements(self) -> list[BooleanStatement]:
        statements: list[BooleanStatement] = []

        # General knowledge of the game:

        # The case file contains exactly one character, weapon, and room.
        for rumor_cards in (CHARACTERS, WEAPONS, ROOMS):
            statements.append(
                Xor(
                    [
                        CardIsInLocation(rumor_card, CASE_FILE)
                        for rumor_card in rumor_cards
                    ]
                )
            )

        # Each rumor card is owned by exactly one of the players including the case file
        # and extra cards.
        locs: list[CardLocation] = [*self.player_indices, CASE_FILE, EXTRA_CARDS]
        for rumor_card in RUMORS:
            statements.append(
                Xor(
                    [CardIsInLocation(rumor_card, loc) for loc in locs],
                )
            )

        # Player knowledge accumulated during gameplay:

        for game_log_entry in self.game_log:
            for card_reveal in game_log_entry.card_reveals:
                if isinstance(card_reveal.rumor_card, RumorCard):
                    # If another player has shown this player a rumor card, then this
                    # player knows that that other player has that rumor card.
                    statements.append(
                        CardIsInLocation(
                            card_reveal.rumor_card, card_reveal.other_player_index
                        )
                    )
                elif game_log_entry.guess is None:
                    continue
                elif isinstance(card_reveal.rumor_card, UnknownRumor):
                    # If a player A (can be this player) shows another player B (cannot
                    # be this player) a rumor card, then this player knows that player A
                    # has at least one of the rumor cards in player B's guess:
                    # This player does not know that specific rumor card.
                    statements.append(
                        Or(
                            [
                                CardIsInLocation(
                                    rumor_card, card_reveal.other_player_index
                                )
                                for rumor_card in game_log_entry.guess
                            ]
                        )
                    )
                else:  # card_reveal.rumor_card is None
                    for rumor_card in game_log_entry.guess:
                        # If a player A (can be this player) does not show another
                        # player B (cannot be this player) a rumor card, then this
                        # player knows that player A does have any of the rumor cards in
                        # player B's guess.
                        statements.append(
                            Not(
                                CardIsInLocation(
                                    rumor_card, card_reveal.other_player_index
                                )
                            )
                        )

        # Remove duplicates.  # TODO: Preserve order?
        statements = list(set(statements))

        return statements

    def _get_all_variables(
        self,
    ) -> dict[CardIsInLocation, int]:
        locs: list[CardLocation] = [*self.player_indices, CASE_FILE, EXTRA_CARDS]
        all_variables = [
            CardIsInLocation(rumor_card, loc) for loc in locs for rumor_card in RUMORS
        ]
        return {var: i + 1 for i, var in enumerate(all_variables)}

    def _boolean_statements_to_cnf_clauses(
        self,
        statements: list[BooleanStatement],
        variables_to_lits: dict[CardIsInLocation, int],
    ) -> tuple[Cnf, int]:
        clauses: Cnf = []
        for statement in statements:
            clauses.extend(statement.to_cnf(variables_to_lits))
        id_pool = IDPool(start_from=1, occupied=[[1, len(variables_to_lits)]])
        for player_index in self.player_indices:
            clauses.extend(
                CardEnc.equals(  # type: ignore
                    lits=[
                        i
                        for v, i in variables_to_lits.items()
                        if v.location == player_index
                    ],
                    bound=self.n_cards_per_player,
                    vpool=id_pool,
                ).clauses  # type: ignore
            )
        clauses = [
            list(c) for c in list(set(tuple(c) for c in clauses))
        ]  # TODO: Remove?
        n_lits = cast(int, id_pool.top)  # type: ignore
        return clauses, n_lits

    def solve_truths_cnf_probabilities(self, n_samples: int = 10):
        all_variables = self._get_all_variables()
        statements = self._game_log_to_boolean_statements()
        clauses, n_lits = self._boolean_statements_to_cnf_clauses(
            statements, variables_to_lits=all_variables
        )
        solutions: list[dict[CardIsInLocation, bool]] = []
        for _ in range(n_samples):
            orig_lit_indices = list(range(1, 1 + n_lits))
            random_lit_indices = shuffled(orig_lit_indices)
            orig2random_lit_index_mapping = dict(
                zip(orig_lit_indices, random_lit_indices, strict=True)
            )
            random_clauses = [
                [sign(lit) * orig2random_lit_index_mapping[abs(lit)] for lit in clause]
                for clause in clauses
            ]
            cnf = CNF(
                from_clauses=shuffled([shuffled(lits) for lits in random_clauses])
            )
            with Solver(bootstrap_with=cnf) as solver:
                solver.solve()  # type: ignore
                solution = cast(list[int], solver.get_model())
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
            solutions.append(
                {v: s > 0 for v, s in zip(all_variables, solution, strict=False)}
            )
        probabilities = {
            var: sum(sol[var] for sol in solutions) / n_samples for var in all_variables
        }
        return probabilities

    def must_see_extra_cards(self, turn_index: int) -> bool:
        free_case_file_variables = self._get_free_case_file_variables(turn_index)
        return 0 < len(free_case_file_variables) - 1 <= self.n_extra_cards

    def _get_free_case_file_variables(self, turn_index: int | None = None):
        if (
            turn_index is not None
            and turn_index in self._free_case_file_variables.keys()
        ):
            free_case_file_variables = self._free_case_file_variables[turn_index]
        else:
            _, free_case_file_variables = self._solve_truths_cnf()
            if turn_index is not None:
                self._free_case_file_variables[turn_index] = free_case_file_variables
        return free_case_file_variables

    def _solve_truths_cnf(
        self,
    ) -> tuple[dict[CardIsInLocation, bool] | None, list[CardIsInLocation]]:
        all_variables = self._get_all_variables()
        statements = self._game_log_to_boolean_statements()
        clauses, _ = self._boolean_statements_to_cnf_clauses(
            statements, variables_to_lits=all_variables
        )
        cnf = CNF(from_clauses=clauses)
        with Solver(bootstrap_with=cnf) as solver:
            solvable = cast(bool, solver.solve())  # type: ignore
            if not solvable:
                raise UnsolvableError
            solution = cast(list[int], solver.get_model())
            free_case_file_variables: list[CardIsInLocation] = []
            for rumor_card in RUMORS:
                case_file_variable = CardIsInLocation(rumor_card, CASE_FILE)
                case_file_variable_index = all_variables[case_file_variable]
                if +case_file_variable_index in solution:
                    assumptions = [-case_file_variable_index]
                elif -case_file_variable_index in solution:
                    assumptions = [+case_file_variable_index]
                else:
                    raise ValueError
                if cast(bool, solver.solve(assumptions=assumptions)):  # type: ignore
                    free_case_file_variables.append(case_file_variable)
        if len(free_case_file_variables) == 0:
            solution = {v: s > 0 for v, s in zip(all_variables, solution, strict=False)}
            return solution, free_case_file_variables
        else:
            return None, free_case_file_variables

    def try_solving_crime(self) -> Crime | None:
        solution, _ = self._solve_truths_cnf()
        if solution is None:
            return None
        return Crime(
            *[
                var.rumor_card
                for var, v in solution.items()
                if var.location == CASE_FILE and v == 1
            ]  # type: ignore
        )


@dataclasses.dataclass
class SmartBotPlayer(BasePlayer, SmartBotObserver):
    guess_making_strategy: GuessMakingStrategy = (
        GuessMakingStrategy.RANDOM_FIRST_FREE_CASE_FILE_VARIABLES
    )
    # guess_answering_strategy: GuessAnsweringStrategy

    remaining_unique_guesses: list[Crime] = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.remaining_unique_guesses = [
            Crime(*x) for x in itertools.product(CHARACTERS, WEAPONS, ROOMS)
        ]

    def make_guess(self, turn_index: int | None = None) -> Crime:
        if self.guess_making_strategy is GuessMakingStrategy.RANDOM:
            guess = Crime(
                character=shuffled(CHARACTERS)[0],
                weapon=shuffled(WEAPONS)[0],
                room=shuffled(ROOMS)[0],
            )
        elif (
            self.guess_making_strategy
            is GuessMakingStrategy.FIRST_FREE_CASE_FILE_VARIABLES
            or self.guess_making_strategy
            is GuessMakingStrategy.RANDOM_FIRST_FREE_CASE_FILE_VARIABLES
        ):
            free_case_file_variables = self._get_free_case_file_variables(turn_index)
            case_file_variables = [
                CardIsInLocation(location=CASE_FILE, rumor_card=rc) for rc in RUMORS
            ]
            crime_cards = {}
            for rumor_type in RUMOR_TYPES:
                rumor_cards = [
                    var.rumor_card
                    for var in free_case_file_variables
                    if isinstance(var.rumor_card, rumor_type)
                ]
                if len(rumor_cards) == 0:
                    rumor_cards = [
                        var.rumor_card
                        for var in case_file_variables
                        if isinstance(var.rumor_card, rumor_type)
                    ]
                if (
                    self.guess_making_strategy
                    is GuessMakingStrategy.RANDOM_FIRST_FREE_CASE_FILE_VARIABLES
                ):
                    rumor_cards = shuffled(rumor_cards)
                crime_cards[rumor_type] = rumor_cards[0]
            guess = Crime(*crime_cards.values())
        elif self.guess_making_strategy is GuessMakingStrategy.NEW_GUESS_RUMOR:
            raise NotImplementedError
        else:
            raise TypeError
        return guess

    def answer_guess(self, guess: Crime) -> RumorCard | None:
        for rumor_card in shuffled(self.rumor_cards):
            for rumor in guess:
                if rumor_card == rumor:
                    return rumor_card
        return None

    def _game_log_to_boolean_statements(self) -> list[BooleanStatement]:
        statements = super()._game_log_to_boolean_statements()

        # Player knowledge of the game instance:

        # This player has their own rumor cards and only those rumor cards:
        for rumor_card in RUMORS:
            expression = CardIsInLocation(rumor_card, self.agent_index)
            if rumor_card in self.rumor_cards:
                statements.append(expression)
            else:
                statements.append(Not(expression))

        # Remove duplicates.  # TODO: Preserve order?
        statements = list(set(statements))

        return statements
