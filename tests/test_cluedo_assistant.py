import dataclasses
from typing import TextIO
from unittest.mock import Mock

import pytest

from cluedo_assistant import CluedoAssistant
from common.agent_utils import CardReveal, UnknownRumor
from common.cards import Character, Crime, Room, Weapon


@dataclasses.dataclass
class Case:
    n_players: int
    respondent_indexes: list[int]
    expected_n_prompts: int
    expected_card_reveals: list[CardReveal]


@pytest.mark.parametrize(
    "case",
    [
        # 2-player cases:
        Case(
            n_players=2,
            respondent_indexes=[],  # No players respond.
            expected_n_prompts=1,
            expected_card_reveals=[
                CardReveal(1, None),
            ],
        ),
        Case(
            n_players=2,
            respondent_indexes=[1],  # Other player responds.
            expected_n_prompts=1,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
            ],
        ),
        # 3-player cases:
        Case(
            n_players=3,
            respondent_indexes=[],  # No players respond.
            expected_n_prompts=1,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, None),
            ],
        ),
        Case(
            n_players=3,
            respondent_indexes=[1],  # Right-hand player responds.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(2, None),
            ],
        ),
        Case(
            n_players=3,
            respondent_indexes=[2],  # Left-hand player responds.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, UnknownRumor()),
            ],
        ),
        Case(
            n_players=3,
            respondent_indexes=[1, 2],  # Right- and left-hand players respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(2, UnknownRumor()),
            ],
        ),
        Case(
            n_players=3,
            respondent_indexes=[2, 1],  # Left- and right-hand players respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(2, UnknownRumor()),
            ],
        ),
        # 4-player cases:
        Case(
            n_players=4,
            respondent_indexes=[],  # No players respond.
            expected_n_prompts=1,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, None),
                CardReveal(3, None),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[1],  # Right-hand player responds.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(2, None),
                CardReveal(3, None),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[3],  # Left-hand player responds.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, None),
                CardReveal(3, UnknownRumor()),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[1, 3],  # Right- and left-hand players respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(3, UnknownRumor()),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[3, 1],  # Left- and right-hand players respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(3, UnknownRumor()),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[2],  # Farthest player responds.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, UnknownRumor()),
                CardReveal(3, None),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[1, 2],  # Right-hand player and farthest player respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(2, UnknownRumor()),
                CardReveal(3, None),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[3, 2],  # Left-hand player and farthest player respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, UnknownRumor()),
                CardReveal(3, UnknownRumor()),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[2, 1],  # Farthest player and right-hand player respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(2, UnknownRumor()),
                CardReveal(3, None),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[2, 3],  # Farthest player and left-hand player respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, UnknownRumor()),
                CardReveal(3, UnknownRumor()),
            ],
        ),
        Case(
            n_players=4,
            respondent_indexes=[2],  # Farthest player responds.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, UnknownRumor()),
                CardReveal(3, None),
            ],
        ),
        # 5-player cases:
        Case(
            n_players=5,
            respondent_indexes=[2, 4],  # Players 2 and 4 respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, None),
                CardReveal(2, UnknownRumor()),
                CardReveal(4, UnknownRumor()),
            ],
        ),
        Case(
            n_players=5,
            respondent_indexes=[1, 3],  # Players 1 and 3 respond.
            expected_n_prompts=2,
            expected_card_reveals=[
                CardReveal(1, UnknownRumor()),
                CardReveal(3, UnknownRumor()),
                CardReveal(4, None),
            ],
        ),
    ],
)
def test_collect_responses(case: Case) -> None:
    # Arrange

    textio = Mock(spec=TextIO)
    get_player_index_call_count = 0

    def get_player_index(
        player_indexes: list[int], all_player_names: list[str]
    ) -> int | None:
        nonlocal get_player_index_call_count
        player_index = (
            case.respondent_indexes[get_player_index_call_count]
            if get_player_index_call_count < len(case.respondent_indexes)
            else None
        )
        get_player_index_call_count += 1
        return player_index

    textio.get_yes_or_no = lambda prompt: False  # type: ignore
    textio.get_player_index = get_player_index
    textio.print_ = lambda: None
    textio.input_ = lambda: ""

    assistant = CluedoAssistant(
        io=textio, player_names=[f"Player {i}" for i in range(case.n_players)]
    )
    assistant.turn_index = 1
    guess = Crime(Character("plum"), Weapon("ax"), Room("spa"))
    assistant.observer.add_game_log_entry(turn_index=assistant.turn_index, guess=guess)

    # Act

    assistant.collect_responses(current_player_name="Player 0")

    # Assert

    assert get_player_index_call_count == case.expected_n_prompts
    assert len(assistant.observer.game_log) == 2
    assert assistant.observer.game_log[1].turn_index == 1
    assert assistant.observer.game_log[1].guess == guess
    assert (
        sorted(
            assistant.observer.game_log[1].card_reveals,
            key=(lambda cr: cr.other_player_index),
        )
        == case.expected_card_reveals
    )
