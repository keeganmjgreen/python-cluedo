import os
import sys
from time import sleep
from typing import Self, assert_never

from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from common import store
from common.agent_utils import UnknownRumor
from common.cards import (
    N_CASE_FILE_CARDS,
    RUMORS,
    Character,
    Crime,
    Room,
    Weapon,
)
from common.circular_sequence import CircularSequence
from common.consts import GameVariant
from common.dashboard import run_dashboard
from common.io.io import AbstractIo
from common.io.text_io import TextIo
from common.smart_bot_agent import SmartBotObserver
from common.utils import print_logo

N_SAMPLES_FOR_PROBABILITY = 10


class CluedoAssistant:
    def __init__(self, io: AbstractIo, player_names: list[str]) -> None:
        self.io = io
        self.player_names = player_names
        self.player_indices = list(range(len(self.player_names)))
        self.n_players = len(self.player_names)
        n_cards_per_player = (len(RUMORS) - N_CASE_FILE_CARDS) // self.n_players
        self.observer = SmartBotObserver(
            agent_index=-1,
            player_indices=self.player_indices,
            n_cards_per_player=n_cards_per_player,
        )
        self.turn_index = 0
        self.n_extra_cards = self.observer.n_extra_cards
        if self.n_extra_cards > 0:
            self.reveal_extra_cards_first = self.io.get_yes_or_no(
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
            if self.reveal_extra_cards_first:
                self.observer.sees_extra_cards(
                    turn_index=self.turn_index,
                    rumor_cards=self.io.get_extra_cards(
                        n_extra_cards=self.n_extra_cards
                    ),
                )
        self.game_variant = self.io.get_game_variant()

    def run(self, dashboard: bool) -> None:
        while True:
            for player_name in self.player_names:
                if dashboard:
                    probabilities = self.observer.solve_truths_cnf_probabilities(
                        n_samples=N_SAMPLES_FOR_PROBABILITY
                    )
                    store.append_probabilities(
                        str(self.observer), self.turn_index, probabilities
                    )
                self.turn_index += 1
                if self._run_turn(current_player_name=player_name):
                    return
                if self.n_extra_cards > 0 and not self.reveal_extra_cards_first:
                    # TODO: Move into `_run_turn`.
                    observer_must_see_extra_cards = self.observer.must_see_extra_cards(
                        turn_index=self.turn_index
                    )
                    if observer_must_see_extra_cards:
                        self.io.print_(
                            "Knowing the extra cards is the only thing left I need to "
                            "solve the crime."
                        )
                        self.observer.sees_extra_cards(
                            turn_index=self.turn_index,
                            rumor_cards=self.io.get_extra_cards(
                                n_extra_cards=self.n_extra_cards
                            ),
                        )
                        solved = self._try_solving_crime()
                        if not solved:
                            self.io.print_("An unexpected error occurred.")
                        return

    def _run_turn(self, current_player_name: str) -> bool:
        self.io.announce_turn(self.turn_index, current_player_name)

        guess = self._get_guess(current_player_name)
        self.observer.add_game_log_entry(turn_index=self.turn_index, guess=guess)

        self.io.print_("Who gave evidence that the suspect, weapon, or room was wrong?")
        return self.collect_responses(current_player_name)

    def _get_guess(self, current_player_name: str) -> Crime:
        character = self.io.get_rumor_card(
            prompt=f"Which character does {current_player_name.capitalize()} say killed the host?",
            options=Character.instances(),
        )
        weapon = self.io.get_rumor_card(
            prompt=f"What weapon does {current_player_name.capitalize()} say was used?",
            options=Weapon.instances(),
        )
        room = self.io.get_rumor_card(
            prompt=f"Which room does {current_player_name.capitalize()} say the murder took place in?",
            options=Room.instances(),
        )
        return Crime(character=character, weapon=weapon, room=room)

    def collect_responses(self, current_player_name: str) -> bool:
        current_player_index = self.player_names.index(current_player_name)
        seq = CircularSequence(self.player_indices)
        match self.game_variant:
            case GameVariant.LEFT_PLAYERS_REVEAL:
                directions = [-1]
            case GameVariant.RIGHT_PLAYERS_REVEAL:
                directions = [+1]
            case GameVariant.BOTH_SIDES_REVEAL:
                directions = [-1, +1]
            case _ as unreachable:
                assert_never(unreachable)
        distance = (
            self.n_players // 2
            if self.game_variant is GameVariant.BOTH_SIDES_REVEAL
            else self.n_players - 1
        )
        choiceset = [
            seq.get_adjacent_items(current_player_index, direction * distance)
            for direction in directions
        ]
        farthest_player_index = (
            seq.get_offset_item(current_player_index, distance)
            if self.n_players % 2 == 0
            else None
        )
        farthest_player_reached = False
        while sum(len(choices) for choices in choiceset) > 0:
            respondent_index = self.io.get_player_index(
                player_indexes=sorted({c for choices in choiceset for c in choices}),
                all_player_names=self.player_names,
            )
            if respondent_index is None:
                break
            self.observer.sees_card(
                turn_index=self.turn_index,
                other_player_index=respondent_index,
                rumor_card=UnknownRumor(),
            )
            if (
                self.game_variant is GameVariant.BOTH_SIDES_REVEAL
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
                        self.observer.sees_card(
                            turn_index=self.turn_index,
                            other_player_index=nonrespondent_index,
                            rumor_card=None,
                        )
                choiceset = [
                    choices for choices in choiceset if respondent_index not in choices
                ]
                if farthest_player_reached:
                    break
            if self._try_solving_crime():
                return True
        all_choices = sorted({c for choices in choiceset for c in choices})
        for choice in all_choices:
            nonrespondent_index = choice
            self.observer.sees_card(
                turn_index=self.turn_index,
                other_player_index=nonrespondent_index,
                rumor_card=None,
            )
        if len(all_choices) > 0:
            if self._try_solving_crime():
                return True
        return False

    def _try_solving_crime(self) -> bool:
        crime = self.observer.try_solving_crime()
        if crime is None:
            return False
        self.io.print_("The Cluedo assistant has solved the case!")
        self.io.print_(
            f"The host was killed by {crime.character.name.capitalize()} with the "
            f"{crime.weapon.name.capitalize()} in the {crime.room.name.capitalize()}."
        )
        return True


def cluedo_assistant(io: AbstractIo, dashboard: bool = False) -> None:
    if isinstance(io, TextIo):
        os.system("cls" if os.name == "nt" else "clear")
        print()
        print_logo()
        sleep(io.pause_seconds)
    io.print_("Welcome to the Cluedo assistant!")
    io.print_("Give me information about your gameplay by answering my prompts.")
    io.print_("I'll tell you what the crime was as soon as I've isolated the solution.")
    player_names = io.get_human_player_names()
    cluedo_assistant = CluedoAssistant(io=io, player_names=player_names)
    cluedo_assistant.run(dashboard)


def main() -> None:
    cli_settings = _CliSettings.from_cli_args()
    if cli_settings.dashboard:
        dashboard_thread = run_dashboard()
    else:
        dashboard_thread = None
    cluedo_assistant(io=TextIo(), dashboard=cli_settings.dashboard)
    if dashboard_thread is not None:
        dashboard_thread.join()


class _CliSettings(BaseSettings):
    model_config = SettingsConfigDict(cli_kebab_case=True, cli_implicit_flags=True)

    dashboard: bool = False

    @classmethod
    def from_cli_args(cls) -> Self:
        return CliApp.run(cls, cli_args=sys.argv[1:])


if __name__ == "__main__":
    main()
