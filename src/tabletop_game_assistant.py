from copy import deepcopy
from time import sleep
from typing import List, Literal

from src.common.agent_utils import UnknownRumor
from src.common.smart_bot_agent import SmartBotObserver, UnsolvableError
from src.common.cards import (
    CHARACTER_NAMES,
    N_CASE_FILE_CARDS,
    ROOM_NAMES,
    RUMOR_NAMES,
    RUMORS,
    WEAPON_NAMES,
    Character,
    Crime,
    Room,
    RumorCard,
    Weapon,
)
from src.common.probabilities_artifact_manager import ProbabilitiesArtifactManager
from src.common.utils import print_logo, sign

N_SAMPLES_FOR_PROBABILITY = 10
MIN_N_PLAYERS = 2


def format_list(l: list, sep="and") -> str:
    return ", ".join(l[:-1]) + f", {sep} " + l[-1]


def pause(duration_seconds: float = 0.5) -> None:
    sleep(duration_seconds)


def _print(msg: str = "", end: str = "\n") -> None:
    for char in msg:
        print(char, end="")
        sleep(0.01)
    pause()
    print(end, end="")
    if end == "\n":
        pause()


class TabletopGameAssistant:
    def __init__(
        self,
        game_id: int,
        artifacting: bool = True,
        reveal_extra_cards_first: bool = False,
    ):
        self.game_id = game_id
        self.artifacting = artifacting
        self.reveal_extra_cards_first = reveal_extra_cards_first
        if self.artifacting:
            self.probabilities_artifact_mgr = ProbabilitiesArtifactManager(
                start_over=False
            )
        self.player_names = self._get_human_player_names()
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

    @staticmethod
    def _get_human_player_names() -> List[str]:
        _print(
            "Please provide the player names in turn order, beginning with the starting player. "
        )
        current_player_num = 1
        player_names = []

        while True:
            _print(
                f"Player {current_player_num} name{f' (<Enter> if no player {current_player_num})' if len(player_names) >= MIN_N_PLAYERS else ''}: ",
                end="",
            )
            player_name = input()

            if player_name.lower() in [n.lower() for n in player_names]:
                _print("Player names must be unique. ", end="")
                continue

            if player_name != "":
                player_names.append(player_name)
                current_player_num += 1
            else:
                n_players = len(player_names)
                if n_players >= MIN_N_PLAYERS:
                    break
                else:
                    _print(f"There must be at least {MIN_N_PLAYERS} players. ", end="")
                    continue

        return player_names

    def run(self) -> None:
        self.observer.add_game_log_entry(turn_index=self.turn_index, card_reveals=[])
        if self.n_extra_cards != 0 and self.reveal_extra_cards_first:
            self.observer.shown_extra_cards(
                turn_index=self.turn_index, rumor_cards=self._get_extra_cards()
            )
        while True:
            for player_name in self.player_names:
                if self.artifacting:
                    probabilities_ser = self.observer._solve_truths_cnf_probabilities(
                        n_samples=N_SAMPLES_FOR_PROBABILITY
                    )
                    self.probabilities_artifact_mgr.append_probabilities_ser(
                        game_id=self.game_id,
                        agent_type="Observer",
                        agent_index=self.observer.agent_index,
                        turn_index=self.turn_index,
                        probabilities_ser=probabilities_ser,
                    )
                self.turn_index += 1
                self._run_turn(current_player_name=player_name)
                if self.n_extra_cards != 0 and not self.reveal_extra_cards_first:
                    observer_must_see_extra_cards = self.observer._must_see_extra_cards(
                        turn_index=self.turn_index
                    )
                    if observer_must_see_extra_cards:
                        self.observer.shown_extra_cards(
                            turn_index=self.turn_index,
                            rumor_cards=self._get_extra_cards(),
                        )

    def _get_extra_cards(self) -> List[RumorCard]:
        _print("Look at the extra cards. ")
        _print("What are they? ")
        extra_cards = []
        # TODO: Select from list narrowed down by observer.
        # TODO: No duplicate rumor cards entered.
        for i in range(self.n_extra_cards):
            extra_card_name = self._get_item_name(type_of_item="rumor card")
            if extra_card_name in CHARACTER_NAMES:
                card_type = Character
            elif extra_card_name in WEAPON_NAMES:
                card_type = Weapon
            elif extra_card_name in ROOM_NAMES:
                card_type = Room
            extra_cards.append(card_type(name=extra_card_name))
        return extra_cards

    def _run_turn(self, current_player_name: str) -> None:
        _print(f"It's {current_player_name}'s turn. ")

        _print(f"Who does {current_player_name} say killed the host? ", end="")
        character_name = self._get_item_name("character")
        _print(f"How does {current_player_name} say the crime was committed? ", end="")
        weapon_name = self._get_item_name("weapon")
        _print(f"Where does {current_player_name} say the murder took place? ", end="")
        room_name = self._get_item_name("room")
        guess = Crime(
            character=Character(name=character_name),
            weapon=Weapon(name=weapon_name),
            room=Room(name=room_name),
        )

        current_player_index = self.player_names.index(current_player_name)
        self.observer.add_game_log_entry(
            turn_index=self.turn_index,
            turn_player_index=current_player_index,
            guess=guess,
            card_reveals=[],
        )
        _print("Who gave evidence that the suspect, weapon, or room was wrong? ")
        other_player_names = []
        furthest_player_reached = False
        while True:  # TODO: Convert to for-loop?
            print(" - ", end="")
            other_player_name = self._get_item_name(
                "player"
            )  # TODO: Make more user-friendly?
            if other_player_name == current_player_name.lower():
                _print(
                    "The player answering the guess cannot be the same as the player making the guess. "
                )
                continue
            if other_player_name in [n.lower() for n in other_player_names]:
                _print("The same player cannot be entered twice. ", end="")
                if furthest_player_reached:
                    _print("If there is no other player, press <Enter>. ", end="")
                _print()
                continue
            if other_player_name != "":
                other_player_index = [n.lower() for n in self.player_names].index(
                    other_player_name
                )
                raw_players_pos_delta = other_player_index - current_player_index
                raw_abs_players_pos_delta = abs(raw_players_pos_delta)
                if (
                    raw_abs_players_pos_delta
                    == self.n_players - raw_abs_players_pos_delta
                ):
                    furthest_player_reached = True
                    abs_players_pos_delta = raw_abs_players_pos_delta
                    direction = None
                elif (
                    raw_abs_players_pos_delta
                    < self.n_players - raw_abs_players_pos_delta
                ):
                    abs_players_pos_delta = raw_abs_players_pos_delta
                    direction = +sign(raw_players_pos_delta)
                elif (
                    raw_abs_players_pos_delta
                    > self.n_players - raw_abs_players_pos_delta
                ):
                    abs_players_pos_delta = self.n_players - raw_abs_players_pos_delta
                    direction = -sign(raw_players_pos_delta)
            else:
                if len(other_player_names) == 0:
                    # TODO: "...(<Enter> if no player)..."
                    _print("You've indicated that no players answered the guess. ")
                    # TODO:
                    # TODO: Undo option(s)? User double checks?
                    for _other_player_index in self.player_indices:
                        if _other_player_index != current_player_index:
                            self.observer.shown_card(
                                turn_index=self.turn_index,
                                other_player_index=_other_player_index,
                                rumor_card=None,
                            )
                    self._try_solving_crime()
                    break
                else:
                    abs_players_pos_delta = self.n_players // 2
                    direction = None

            if len(other_player_names) == 1:
                if prev_direction is not None:
                    if direction is not None:
                        if prev_direction != -direction:
                            _print("That player cannot be entered. ", end="")
                            continue
                    direction = -prev_direction
                else:
                    if direction is None:
                        direction = 1
                    for _player_pos_delta in range(1, abs_players_pos_delta):
                        _other_player_index = (
                            current_player_index + (-direction) * _player_pos_delta
                        ) % self.n_players
                        self.observer.shown_card(
                            turn_index=self.turn_index,
                            other_player_index=_other_player_index,
                            rumor_card=None,
                        )
            if direction is not None:
                for _player_pos_delta in range(1, abs_players_pos_delta):
                    _other_player_index = (
                        current_player_index + direction * _player_pos_delta
                    ) % self.n_players
                    self.observer.shown_card(
                        turn_index=self.turn_index,
                        other_player_index=_other_player_index,
                        rumor_card=None,
                    )
            if other_player_name not in other_player_names + [""]:
                self.observer.shown_card(
                    turn_index=self.turn_index,
                    other_player_index=other_player_index,
                    rumor_card=UnknownRumor(),
                )
            elif (
                other_player_name == ""
                and len(other_player_names) == 1
                and prev_direction is not None
            ):
                other_player_index = (
                    current_player_index + direction * abs_players_pos_delta
                ) % self.n_players
                self.observer.shown_card(
                    turn_index=self.turn_index,
                    other_player_index=other_player_index,
                    rumor_card=None,
                )
            self._try_solving_crime()
            other_player_names.append(self.player_names[other_player_index])
            if len(other_player_names) == 2:
                break
            prev_direction = deepcopy(direction)

    def _try_solving_crime(self):
        result = self.observer._try_solving_crime()
        if result is not None:
            crime = result
            _print("Cluedo Assistant has solved the case! ")
            _print(
                f"The host was killed by {crime.character.capitalize()} with the "
                f"{crime.weapon.capitalize()} in the {crime.room.capitalize()}. "
            )

    def _get_item_name(
        self,
        type_of_item: Literal["character", "weapon", "room", "rumor card", "player"],
    ) -> str:
        item_names_lookup = {
            "character": CHARACTER_NAMES,
            "weapon": WEAPON_NAMES,
            "room": ROOM_NAMES,
            "rumor card": RUMOR_NAMES,
            "player": self.player_names,
        }
        item_names = item_names_lookup[type_of_item]
        while True:
            _print(f"Enter {type_of_item} name: ", end="")
            item_name = input()
            pause()
            if item_name.lower() in [n.lower() for n in item_names]:
                break
            else:
                if item_name != "":
                    _print(f"I don't recognize that {type_of_item}. ", end="")
                elif type_of_item == "player":
                    break
                _print(
                    f"Please enter {format_list([n.title() if type_of_item != 'player' else n for n in item_names], 'or')}. ",
                    end="",
                )

        return item_name.lower()

    def _get_other_player_names(self, current_player_name: str) -> List[str]:
        ...


def main(game_id: int = 0, artifacting: bool = True):
    print_logo()
    pause()
    _print("Initializing Cluedo Assistant... ")
    tabletop_game_assistant = TabletopGameAssistant(
        game_id=game_id, artifacting=artifacting
    )
    _print("Running Cluedo Assistant... ")
    _print("Give me information about your gameplay by answering my prompts. ", end="")
    _print("I will tell you what the crime was as soon as I've isolated the solution. ")
    tabletop_game_assistant.run()


if __name__ == "__main__":
    print("\n" * 100)
    main(game_id=0, artifacting=True)
