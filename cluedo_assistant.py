import dataclasses
import os
import sys
from time import sleep
from typing import Self, assert_never

from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from common.agent_utils import BasePlayer, UnknownRumor
from common.cards import (
    Character,
    Crime,
    Room,
    Weapon,
    get_n_cards_per_player,
)
from common.circular_sequence import CircularSequence
from common.consts import GameVariant
from common.io.io import AbstractIo
from common.io.message_io import MessageIo
from common.io.text_io import TextIo
from common.smart_bot_agent import SmartBotObserver, SmartBotPlayer, UnsolvableError
from common.utils import print_logo

N_SAMPLES_FOR_PROBABILITY = 10


@dataclasses.dataclass
class CluedoAssistantSetup:
    io: AbstractIo
    player_names: list[str]
    agent: SmartBotObserver | SmartBotPlayer
    reveal_extra_cards_first: bool
    game_variant: GameVariant

    @property
    def player_indices(self) -> list[int]:
        return list(range(len(self.player_names)))

    @property
    def n_players(self) -> int:
        return len(self.player_names)

    @property
    def n_extra_cards(self) -> int:
        return self.agent.n_extra_cards


def run_cluedo_assistant(setup: CluedoAssistantSetup, p_heatmap: bool) -> None:
    turn_index = 0
    try:
        while True:
            for player_name in setup.player_names:
                if p_heatmap:
                    probabilities = setup.agent.solve_truths_cnf_probabilities(
                        n_samples=N_SAMPLES_FOR_PROBABILITY
                    )
                    if isinstance(setup.io, TextIo):
                        from common import store

                        store.append_probabilities(
                            str(setup.agent),
                            turn_index,
                            probabilities,
                            player_names=setup.player_names,
                        )
                    elif isinstance(setup.io, MessageIo):
                        setup.io.latest_probabilities = probabilities
                turn_index += 1
                if _run_turn(setup, turn_index, current_player_name=player_name):
                    return
                if (
                    not isinstance(setup.agent, BasePlayer)
                    and setup.n_extra_cards > 0
                    and not setup.reveal_extra_cards_first
                ):
                    # TODO: Move into `_run_turn`.
                    observer_must_see_extra_cards = setup.agent.must_see_extra_cards(
                        turn_index=turn_index
                    )
                    if observer_must_see_extra_cards:
                        setup.io.print_(
                            "Knowing the extra cards is the only thing left I need to "
                            "solve the crime."
                        )
                        setup.agent.sees_extra_cards(
                            turn_index=turn_index,
                            rumor_cards=setup.io.get_extra_cards(
                                n_extra_cards=setup.n_extra_cards
                            ),
                        )
                        solved = _try_solving_crime(
                            setup,
                        )
                        if not solved:
                            setup.io.print_("An unexpected error occurred.")
                        return
    except UnsolvableError:
        setup.io.print_(
            "Based on the information you've entered during the gameplay, "
            "the crime is unsolvable. "
            "You likely entered a rumor or player response incorrectly."
        )


def _run_turn(
    setup: CluedoAssistantSetup, turn_index: int, current_player_name: str
) -> bool:
    current_player_index = setup.player_names.index(current_player_name)
    current_player_is_user = current_player_index == setup.agent.agent_index

    setup.io.announce_turn(
        turn_index,
        current_player_name,
        current_player_is_user=current_player_is_user,
    )

    rumor_started = setup.io.get_yes_or_no(
        f"Did {'you' if current_player_is_user else current_player_name.capitalize()} start a rumor in this turn?"
    )
    if not rumor_started:
        setup.agent.add_game_log_entry(turn_index=turn_index)
        return False

    guess = _get_guess(setup, current_player_name)
    setup.agent.add_game_log_entry(turn_index=turn_index, guess=guess)

    setup.io.print_("Who gave evidence that the suspect, weapon, or room was wrong?")
    return collect_responses(setup, turn_index, current_player_name, guess)


def _get_guess(setup: CluedoAssistantSetup, current_player_name: str) -> Crime:
    current_player_index = setup.player_names.index(current_player_name)
    current_player_is_user = current_player_index == setup.agent.agent_index

    character = setup.io.get_rumor_card(
        prompt=f"Which character {'do you' if current_player_is_user else f'does {current_player_name.capitalize()}'} say killed the host?",
        options=Character.instances(),
    )
    weapon = setup.io.get_rumor_card(
        prompt=f"Which weapon {'do you' if current_player_is_user else f'does {current_player_name.capitalize()}'} say was used?",
        options=Weapon.instances(),
    )
    room = setup.io.get_rumor_card(
        prompt=f"Which room {'do you' if current_player_is_user else f'does {current_player_name.capitalize()}'} say the murder took place in?",
        options=Room.instances(),
    )
    return Crime(character=character, weapon=weapon, room=room)


def collect_responses(
    setup: CluedoAssistantSetup, turn_index: int, current_player_name: str, guess: Crime
) -> bool:
    current_player_index = setup.player_names.index(current_player_name)
    seq = CircularSequence(setup.player_indices)
    match setup.game_variant:
        case GameVariant.LEFT_PLAYERS_REVEAL:
            directions = [-1]
        case GameVariant.RIGHT_PLAYERS_REVEAL:
            directions = [+1]
        case GameVariant.BOTH_SIDES_REVEAL:
            directions = [-1, +1]
        case _ as unreachable:
            assert_never(unreachable)
    distance = (
        setup.n_players // 2
        if setup.game_variant is GameVariant.BOTH_SIDES_REVEAL
        else setup.n_players - 1
    )
    choiceset = [
        seq.get_adjacent_items(current_player_index, direction * distance)
        for direction in directions
    ]
    farthest_player_index = (
        seq.get_offset_item(current_player_index, distance)
        if setup.n_players % 2 == 0
        else None
    )
    farthest_player_reached = False
    while sum(len(choices) for choices in choiceset) > 0:
        respondent_index = setup.io.get_player_index(
            prompt=(
                "Select a player (<Enter> if no player)"
                if isinstance(setup.io, TextIo)
                else "Select a player."
            ),
            optional="no player",
            player_indexes=sorted({c for choices in choiceset for c in choices}),
            all_player_names=setup.player_names,
            player_index_of_user=setup.agent.agent_index,
        )
        if respondent_index is None:
            break
        if current_player_index == setup.agent.agent_index:
            rumor_card = setup.io.get_rumor_card(
                prompt=(
                    "Which rumor card did "
                    f"{setup.player_names[respondent_index].capitalize()} "
                    "reveal to you?"
                ),
                options=guess,
            )
        else:
            rumor_card = UnknownRumor()
        setup.agent.sees_card(
            turn_index=turn_index,
            other_player_index=respondent_index,
            rumor_card=rumor_card,
        )
        if (
            setup.game_variant is GameVariant.BOTH_SIDES_REVEAL
            and respondent_index == farthest_player_index
        ):
            farthest_player_reached = True
            choiceset = [
                [c for c in choices if c != farthest_player_index]
                for choices in choiceset
            ]
            if len(choiceset) == 1:
                break
        else:
            for choices in choiceset:
                if respondent_index not in choices:
                    continue
                choice_list = list(choices)
                nonrespondent_indexes = choice_list[
                    : choice_list.index(respondent_index)
                ]
                for nonrespondent_index in nonrespondent_indexes:
                    setup.agent.sees_card(
                        turn_index=turn_index,
                        other_player_index=nonrespondent_index,
                        rumor_card=None,
                    )
            choiceset = [
                choices for choices in choiceset if respondent_index not in choices
            ]
            if farthest_player_reached:
                break
        if _try_solving_crime(
            setup,
        ):
            return True
    all_choices = sorted({c for choices in choiceset for c in choices})
    for choice in all_choices:
        nonrespondent_index = choice
        setup.agent.sees_card(
            turn_index=turn_index,
            other_player_index=nonrespondent_index,
            rumor_card=None,
        )
    if len(all_choices) > 0:
        if _try_solving_crime(
            setup,
        ):
            return True
    return False


def _try_solving_crime(setup: CluedoAssistantSetup) -> bool:
    if isinstance(setup.io, MessageIo) and len(setup.io.game_history) > 0:
        # We weren't able to solve the crime at this point in the game history, and
        # we shouldn't be able to solve it now again either:
        return False
    crime = setup.agent.try_solving_crime()
    if crime is None:
        return False
    setup.io.print_("The Cluedo assistant has solved the case!")
    setup.io.print_(
        f"The host was killed by {crime.character.name.capitalize()} with the "
        f"{crime.weapon.name.capitalize()} in the {crime.room.name.capitalize()}."
    )
    return True


def set_up_cluedo_assistant(io: AbstractIo) -> CluedoAssistantSetup:
    io.print_("Welcome to the Cluedo Solver!")
    io.print_("Give me information about your gameplay by answering my prompts.")
    io.print_("I'll tell you what the crime was as soon as I've isolated the solution.")
    player_names = io.get_human_player_names()
    player_indices = list(range(len(player_names)))
    n_cards_per_player = get_n_cards_per_player(n_players=len(player_names))
    player_index = io.get_player_index(
        prompt=(
            "Which player are you? (<Enter> if no player if you're just observing)"
            if isinstance(io, TextIo)
            else "Which player are you?"
        ),
        optional="I'm just observing",
        player_indexes=player_indices,
        all_player_names=player_names,
        player_index_of_user=-1,
    )
    if player_index is None:
        agent = SmartBotObserver(
            agent_index=-1,
            player_indices=player_indices,
        )
    else:
        player_hand = io.get_rumor_cards(
            prompt=f"Which {n_cards_per_player} rumor cards are in your hand?",
            n_rumor_cards=n_cards_per_player,
        )
        agent = SmartBotPlayer(
            agent_index=player_index,
            player_indices=player_indices,
            rumor_cards=player_hand,
        )
    if agent.n_extra_cards > 0:
        reveal_extra_cards_first = io.get_yes_or_no(
            prompt=(
                "Based on the number of players, there must be extra cards that "
                "are neither in the case file nor in any player's hand. "
                "In observer mode, I must see these extra cards in order to solve "
                "the crime. "
                "Would you like to enter these extra cards now? "
                "If not, you can enter them later; "
                "I'll let you know when the knowing the extra cards is the only "
                "thing left I need to solve the crime."
            ),
        )
        if reveal_extra_cards_first:
            agent.sees_extra_cards(
                turn_index=0,
                rumor_cards=io.get_extra_cards(n_extra_cards=agent.n_extra_cards),
            )
    else:
        reveal_extra_cards_first = False
    game_variant = io.get_game_variant()
    return CluedoAssistantSetup(
        io=io,
        player_names=player_names,
        agent=agent,
        reveal_extra_cards_first=reveal_extra_cards_first,
        game_variant=game_variant,
    )


def cluedo_assistant(io: AbstractIo, p_heatmap: bool = False) -> None:
    if isinstance(io, TextIo):
        os.system("cls" if os.name == "nt" else "clear")
        print()
        print_logo()
        sleep(io.pause_seconds)
    setup = set_up_cluedo_assistant(io)
    run_cluedo_assistant(setup, p_heatmap)


def main() -> None:
    cli_settings = _CliSettings.from_cli_args()
    if cli_settings.p_heatmap:
        from common.dashboard import run_dashboard

        dashboard_thread = run_dashboard()
    else:
        dashboard_thread = None
    cluedo_assistant(io=TextIo(), p_heatmap=cli_settings.p_heatmap)
    if dashboard_thread is not None:
        dashboard_thread.join()


class _CliSettings(BaseSettings):
    model_config = SettingsConfigDict(cli_kebab_case=True, cli_implicit_flags=True)

    p_heatmap: bool = False

    @classmethod
    def from_cli_args(cls) -> Self:
        return CliApp.run(cls, cli_args=sys.argv[1:])


if __name__ == "__main__":
    main()
