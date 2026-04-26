import os
import sys
from time import sleep
from typing import Self

from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from common import store
from common.agent_utils import UnknownRumor
from common.cards import (
    N_CASE_FILE_CARDS,
    RUMORS,
    Character,
    Crime,
    Room,
    RumorCard,
    Weapon,
)
from common.circular_sequence import CircularSequence
from common.consts import MIN_N_PLAYERS
from common.dashboard import run_dashboard
from common.smart_bot_agent import SmartBotObserver
from common.textio import TextIo
from common.utils import print_logo

N_SAMPLES_FOR_PROBABILITY = 10


def _get_human_player_names(textio: TextIo) -> list[str]:
    textio.print_(
        "Please provide the player names in turn order, beginning with the starting player."
    )
    current_player_num = 1
    player_names: list[str] = []

    while True:
        player_name = textio.input_(
            f"Player {current_player_num} name{f' (<Enter> if no player {current_player_num})' if len(player_names) >= MIN_N_PLAYERS else ''}: ",
        )
        if player_name is None:
            n_players = len(player_names)
            if n_players >= MIN_N_PLAYERS:
                break
            else:
                textio.print_(
                    f"There must be at least {MIN_N_PLAYERS} players.", end=" "
                )
                continue
        elif player_name.lower() in [n.lower() for n in player_names]:
            textio.print_("Player names must be unique.", end=" ")
            continue
        else:
            player_names.append(player_name)
            current_player_num += 1
            continue

    return player_names


class CluedoAssistant:
    def __init__(
        self,
        textio: TextIo,
        player_names: list[str],
        reveal_extra_cards_first: bool = False,
    ) -> None:
        self.textio = textio
        self.player_names = player_names
        self.reveal_extra_cards_first = reveal_extra_cards_first
        self.player_indices = list(range(len(self.player_names)))
        self.n_players = len(self.player_names)
        n_cards_per_player = (len(RUMORS) - N_CASE_FILE_CARDS) // self.n_players
        self.observer = SmartBotObserver(
            agent_index=-1,
            player_indices=self.player_indices,
            n_cards_per_player=n_cards_per_player,
        )
        self.n_extra_cards = self.observer.n_extra_cards
        self.turn_index = 0

    def run(self, dashboard: bool) -> None:
        if self.n_extra_cards != 0 and self.reveal_extra_cards_first:
            self.observer.sees_extra_cards(
                turn_index=self.turn_index, rumor_cards=self._get_extra_cards()
            )
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
                if self.n_extra_cards != 0 and not self.reveal_extra_cards_first:
                    observer_must_see_extra_cards = self.observer.must_see_extra_cards(
                        turn_index=self.turn_index
                    )
                    if observer_must_see_extra_cards:
                        self.observer.sees_extra_cards(
                            turn_index=self.turn_index,
                            rumor_cards=self._get_extra_cards(),
                        )

    def _get_extra_cards(self) -> list[RumorCard]:
        self.textio.print_("Look at the extra cards.")
        self.textio.print_("What are they?")
        extra_cards = []
        # TODO: Select from list narrowed down by observer.
        options = RUMORS
        extra_cards: list[RumorCard] = []
        for i in range(self.n_extra_cards):
            extra_card = self.textio.get_rumor_card(
                prompt=f"Enter extra card #{i + 1}/{self.n_extra_cards}",
                options=options,
            )
            extra_cards.append(extra_card)
            options = [o for o in options if o != extra_card]
        return extra_cards

    def _run_turn(self, current_player_name: str) -> bool:
        self.textio.print_(f"It's {current_player_name}'s turn.")

        guess = self._get_guess(current_player_name)
        self.observer.add_game_log_entry(turn_index=self.turn_index, guess=guess)

        self.textio.print_(
            "Who gave evidence that the suspect, weapon, or room was wrong?"
        )
        return self.collect_responses(current_player_name)

    def _get_guess(self, current_player_name: str) -> Crime:
        character = self.textio.get_rumor_card(
            prompt=f"Which character does {current_player_name} say killed the host?",
            options=Character.instances(),
        )
        weapon = self.textio.get_rumor_card(
            prompt=f"What weapon does {current_player_name} say was used?",
            options=Weapon.instances(),
        )
        room = self.textio.get_rumor_card(
            prompt=f"Which room does {current_player_name} say the murder took place in?",
            options=Room.instances(),
        )
        return Crime(character=character, weapon=weapon, room=room)

    def collect_responses(self, current_player_name: str) -> bool:
        current_player_index = self.player_names.index(current_player_name)
        seq = CircularSequence(self.player_indices)
        choiceset = [
            seq.get_adjacent_items(
                current_player_index, direction * (self.n_players // 2)
            )
            for direction in [-1, +1]
        ]
        farthest_player_index = (
            seq.get_offset_item(current_player_index, self.n_players // 2)
            if self.n_players % 2 == 0
            else None
        )
        farthest_player_reached = False
        while sum(len(choices) for choices in choiceset) > 0:
            respondent_index = self.textio.get_player_index(
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
            if respondent_index == farthest_player_index:
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
        self.textio.print_("The Cluedo assistant has solved the case!")
        self.textio.print_(
            f"The host was killed by {crime.character.name.capitalize()} with the "
            f"{crime.weapon.name.capitalize()} in the {crime.room.name.capitalize()}."
        )
        return True


def cluedo_assistant(dashboard: bool, reveal_extra_cards_first: bool = False) -> None:
    print()
    print_logo()
    textio = TextIo()
    sleep(textio.pause_seconds)
    textio.print_("Initializing the Cluedo assistant...")
    cluedo_assistant = CluedoAssistant(
        textio=textio,
        player_names=_get_human_player_names(textio),
        reveal_extra_cards_first=reveal_extra_cards_first,
    )
    textio.print_("Running the Cluedo assistant...")
    textio.print_(
        "Give me information about your gameplay by answering my prompts. "
        "I will tell you what the crime was as soon as I've isolated the solution."
    )
    cluedo_assistant.run(dashboard)


def main() -> None:
    cli_settings = _CliSettings.from_cli_args()
    if cli_settings.dashboard:
        dashboard_thread = run_dashboard()
    else:
        dashboard_thread = None
    cluedo_assistant(
        dashboard=cli_settings.dashboard,
        reveal_extra_cards_first=cli_settings.reveal_extra_cards_first,
    )
    if dashboard_thread is not None:
        dashboard_thread.join()


class _CliSettings(BaseSettings):
    model_config = SettingsConfigDict(cli_kebab_case=True, cli_implicit_flags=True)

    dashboard: bool = False
    reveal_extra_cards_first: bool = False

    @classmethod
    def from_cli_args(cls) -> Self:
        return CliApp.run(cls, cli_args=sys.argv[1:])


if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    main()
