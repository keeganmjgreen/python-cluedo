import dataclasses
import sys
from collections.abc import Sequence
from time import sleep
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from common import store
from common.agent_utils import (
    AgentIndex,
    BaseAgent,
    BaseObserver,
    BasePlayer,
    UnknownRumor,
)
from common.cards import CHARACTERS, ROOMS, WEAPONS, Crime, RumorCard
from common.consts import MIN_N_PLAYERS
from common.dashboard import run_dashboard
from common.smart_bot_agent import SmartBotObserver, SmartBotPlayer
from common.user_player import UserPlayer
from common.utils import shuffled

N_SAMPLES_FOR_PROBABILITY = 10


@dataclasses.dataclass
class GameSetup:
    crime: Crime
    extra_cards: Sequence[RumorCard]
    agents: dict[AgentIndex, BaseAgent]

    @property
    def players(self) -> dict[AgentIndex, BasePlayer]:
        return {
            agent.agent_index: agent
            for agent in self.agents.values()
            if isinstance(agent, BasePlayer)
        }

    @property
    def observers(self) -> dict[AgentIndex, BaseObserver]:
        return {
            agent.agent_index: agent
            for agent in self.agents.values()
            if isinstance(agent, BaseObserver) and not isinstance(agent, BasePlayer)
        }


def run_turn(
    turn_index: int,
    players: dict[AgentIndex, BasePlayer],
    current_player_index: AgentIndex,
    observers: dict[AgentIndex, BaseObserver],
) -> None:
    print(f"Turn: {turn_index}.")
    agents: dict[AgentIndex, BaseAgent] = {**players, **observers}
    current_player = players[current_player_index]
    guess = current_player.make_guess(turn_index=turn_index)
    for agent in agents.values():
        agent.add_game_log_entry(
            turn_index=turn_index,
            turn_player_index=current_player.agent_index,
            guess=guess,
            card_reveals=[],
        )
    furthest_player_reached = False
    n_other_players = len(players) - 1
    for direction in [-1, +1]:
        players_pos_delta = 1
        while players_pos_delta <= n_other_players // 2 + 1:
            if (
                players_pos_delta == n_other_players // 2 + 1
                and furthest_player_reached
            ):
                break
            if players_pos_delta == n_other_players // 2 + 1:
                furthest_player_reached = True
            second_player_pos = (
                current_player.agent_index + players_pos_delta * direction
            )
            second_player = players[(len(players) + second_player_pos) % len(players)]
            rumor_card = second_player.answer_guess(guess)
            current_player.shown_card(
                turn_index=turn_index,
                other_player_index=second_player.agent_index,
                rumor_card=rumor_card,
            )
            for third_agent in [
                agent
                for agent in agents.values()
                if agent.agent_index
                not in [current_player.agent_index, second_player.agent_index]
            ]:
                third_agent.shown_card(
                    turn_index=turn_index,
                    other_player_index=second_player.agent_index,
                    rumor_card=(UnknownRumor() if rumor_card is not None else None),
                )
            if rumor_card is not None:
                break
            else:
                players_pos_delta += 1


def run_game(setup: GameSetup, dashboard: bool, reveal_extra_cards_first: bool) -> None:
    n_extra_cards = len(setup.extra_cards)
    turn_index = 0
    for agent in setup.agents.values():
        agent.add_game_log_entry(turn_index=turn_index, card_reveals=[])
        if n_extra_cards != 0 and reveal_extra_cards_first:
            agent.shown_extra_cards(
                turn_index=turn_index, rumor_cards=setup.extra_cards
            )
    won_agent_indices: list[AgentIndex] = []
    while True:
        for player in setup.players.values():
            if dashboard:
                for agent in setup.agents.values():
                    if not isinstance(agent, SmartBotObserver):
                        continue
                    probabilities = agent.solve_truths_cnf_probabilities(
                        n_samples=N_SAMPLES_FOR_PROBABILITY
                    )
                    store.append_probabilities(str(agent), turn_index, probabilities)
                    sleep(0.1)
            turn_index += 1
            run_turn(turn_index, setup.players, player.agent_index, setup.observers)
            newly_won_agent_indices: list[AgentIndex] = []
            for agent in setup.agents.values():
                if agent.agent_index in won_agent_indices:
                    continue
                if n_extra_cards != 0 and not reveal_extra_cards_first:
                    if isinstance(agent, SmartBotObserver):
                        agent_must_see_extra_cards = agent.must_see_extra_cards(
                            turn_index=turn_index
                        )
                        if agent_must_see_extra_cards:
                            agent.shown_extra_cards(
                                turn_index=turn_index, rumor_cards=setup.extra_cards
                            )
                result = agent.try_solving_crime()
                if result is not None:
                    won_agent_indices.append(agent.agent_index)
                    newly_won_agent_indices.append(agent.agent_index)
            newly_won_player_indices = [
                index
                for index in newly_won_agent_indices
                if index in setup.players.keys()
            ]
            if len(newly_won_player_indices) > 0:
                print(
                    f"The following players have solved the crime in the last turn: {newly_won_player_indices}"
                )
            newly_won_observer_indices = [
                index
                for index in newly_won_agent_indices
                if index in setup.observers.keys()
            ]
            if len(newly_won_observer_indices) > 0:
                print(
                    f"The following observers have solved the crime in the last turn: {newly_won_observer_indices}"
                )
            if len(won_agent_indices) == len(setup.agents):
                print("By now, all players and observers have solved the crime.")
                return


def set_up_game(
    player_types: Sequence[type[BasePlayer]],
    observer_types: Sequence[type[BaseObserver]],
) -> GameSetup:
    character_deck = shuffled(CHARACTERS)
    weapon_deck = shuffled(WEAPONS)
    room_deck = shuffled(ROOMS)
    crime = Crime(
        character=character_deck.pop(),
        weapon=weapon_deck.pop(),
        room=room_deck.pop(),
    )
    rumor_deck = shuffled(character_deck + weapon_deck + room_deck)
    n_players = len(player_types)
    n_cards_per_player = len(rumor_deck) // n_players
    n_extra_cards = len(rumor_deck) % n_players
    extra_cards = [rumor_deck.pop() for _ in range(n_extra_cards)]
    agent_types = list(player_types) + list(observer_types)
    agents: dict[AgentIndex, BaseAgent] = {}
    for agent_index, agent_type in enumerate(agent_types):
        player_indices = list(range(n_players))
        if issubclass(agent_type, BasePlayer):
            agent = agent_type(
                agent_index=agent_index,
                player_indices=player_indices,
                n_cards_per_player=n_cards_per_player,
                rumor_cards=[rumor_deck.pop() for _ in range(n_cards_per_player)],
            )
        else:
            agent = agent_type(
                agent_index=agent_index,
                player_indices=player_indices,
                n_cards_per_player=n_cards_per_player,
            )
        agents[agent_index] = agent
    game_setup = GameSetup(
        crime=crime,
        extra_cards=extra_cards,
        agents=agents,
    )
    return game_setup


def cluedo_simulator(
    player_types: Sequence[type[BasePlayer]],
    observer_types: Sequence[type[BaseObserver]] = (),
    dashboard: bool = False,
    reveal_extra_cards_first: bool = False,
) -> None:
    game_setup = set_up_game(player_types=player_types, observer_types=observer_types)
    run_game(
        setup=game_setup,
        dashboard=dashboard,
        reveal_extra_cards_first=reveal_extra_cards_first,
    )


def main() -> None:
    cli_settings = _CliSettings.from_cli_args()
    if cli_settings.dashboard:
        dashboard_thread = run_dashboard()
    else:
        dashboard_thread = None
    cluedo_simulator(
        player_types=(
            [SmartBotPlayer] * cli_settings.n_bot_players
            + [UserPlayer] * cli_settings.n_human_players
        ),
        observer_types=([SmartBotObserver] if cli_settings.include_observer else []),
        dashboard=cli_settings.dashboard,
        reveal_extra_cards_first=cli_settings.reveal_extra_cards_first,
    )
    if dashboard_thread is not None:
        dashboard_thread.join()


class _CliSettings(BaseSettings):
    model_config = SettingsConfigDict(cli_kebab_case=True, cli_implicit_flags=True)

    n_bot_players: int = 0
    n_human_players: int = 0
    include_observer: bool = False
    dashboard: bool = False
    reveal_extra_cards_first: bool = False

    @model_validator(mode="after")
    def check_n_total_players(self) -> Self:
        if self.n_bot_players + self.n_human_players < MIN_N_PLAYERS:
            raise ValueError(f"There must be at least {MIN_N_PLAYERS} players")
        return self

    @classmethod
    def from_cli_args(cls) -> Self:
        return CliApp.run(cls, cli_args=sys.argv[1:])


if __name__ == "__main__":
    main()
