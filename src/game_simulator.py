import dataclasses
import sys
from collections.abc import Sequence
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from src.common.agent_utils import BaseAgent, BaseObserver, BasePlayer, UnknownRumor
from src.common.cards import CHARACTERS, ROOMS, WEAPONS, Crime, RumorCard
from src.common.consts import MIN_N_PLAYERS
from src.common.probabilities_artifact_manager import ProbabilitiesArtifactManager
from src.common.smart_bot_agent import SmartBotObserver, SmartBotPlayer
from src.common.user_player import UserPlayer
from src.common.utils import shuffled

N_SAMPLES_FOR_PROBABILITY = 10


@dataclasses.dataclass
class GameSetup:
    crime: Crime
    extra_cards: list[RumorCard]
    agents: list[BaseAgent]


def run_turn(
    turn_index: int,
    agents: list[BaseAgent],
    current_player_index: int,
):
    print(f"Turn: {turn_index}.")
    agent_indices = list(agents.keys())
    player_indices = [
        index for index, player in agents.items() if isinstance(player, BasePlayer)
    ]
    current_player = agents[current_player_index]
    guess = current_player.make_guess(turn_index=turn_index)
    for agent_index in agent_indices:
        agents[agent_index].add_game_log_entry(
            turn_index=turn_index,
            turn_player_index=current_player.agent_index,
            guess=guess,
            card_reveals=[],
        )
    furthest_player_reached = False
    n_other_players = len(player_indices) - 1
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
            second_player = agents[
                (len(player_indices) + second_player_pos) % len(player_indices)
            ]
            rumor_card = second_player.answer_guess(guess)
            current_player.shown_card(
                turn_index=turn_index,
                other_player_index=second_player.agent_index,
                rumor_card=rumor_card,
            )
            for third_agent_index in [
                agent_index
                for agent_index in agent_indices
                if agent_index
                not in [current_player.agent_index, second_player.agent_index]
            ]:
                third_agent = agents[third_agent_index]
                third_agent.shown_card(
                    turn_index=turn_index,
                    other_player_index=second_player.agent_index,
                    rumor_card=(UnknownRumor() if rumor_card is not None else None),
                )
            if rumor_card is not None:
                break
            else:
                players_pos_delta += 1


def run_game(
    game_setup: GameSetup, artifacting_id: int | None, reveal_extra_cards_first: bool
):
    agents = game_setup.agents
    agent_indices = list(agents.keys())
    player_indices = [
        index for index, player in agents.items() if isinstance(player, BasePlayer)
    ]
    observer_indices = [index for index in agents.keys() if index not in player_indices]
    if artifacting_id is not None:
        probabilities_artifact_mgr = ProbabilitiesArtifactManager(start_over=False)
    n_extra_cards = len(game_setup.extra_cards)
    turn_index = 0
    for agent_index in agent_indices:
        agents[agent_index].add_game_log_entry(turn_index=turn_index, card_reveals=[])
        if n_extra_cards != 0 and reveal_extra_cards_first:
            agents[agent_index].shown_extra_cards(
                turn_index=turn_index, rumor_cards=game_setup.extra_cards
            )
    won_agent_indices = []
    while True:
        for current_player_index in player_indices:
            if artifacting_id is not None:
                for agent_index in agent_indices:
                    probabilities_ser = agents[
                        agent_index
                    ]._solve_truths_cnf_probabilities(
                        n_samples=N_SAMPLES_FOR_PROBABILITY
                    )
                    probabilities_artifact_mgr.append_probabilities_ser(
                        artifacting_id=artifacting_id,
                        agent_type=(
                            "Player"
                            if isinstance(agents[agent_index], BasePlayer)
                            else "Observer"
                        ),
                        agent_index=agent_index,
                        turn_index=turn_index,
                        probabilities_ser=probabilities_ser,
                    )
            turn_index += 1
            run_turn(turn_index, agents, current_player_index)
            newly_won_agent_indices = []
            for agent_index in agent_indices:
                if agent_index in won_agent_indices:
                    continue
                agent = agents[agent_index]
                if n_extra_cards != 0 and not reveal_extra_cards_first:
                    agent_must_see_extra_cards = agents[
                        agent_index
                    ]._must_see_extra_cards(turn_index=turn_index)
                    if agent_must_see_extra_cards:
                        agents[agent_index].shown_extra_cards(
                            turn_index=turn_index, rumor_cards=game_setup.extra_cards
                        )
                result = agent._try_solving_crime()
                if result is not None:
                    won_agent_indices.append(agent_index)
                    newly_won_agent_indices.append(agent_index)
            newly_won_player_indices = [
                index for index in newly_won_agent_indices if index in player_indices
            ]
            if len(newly_won_player_indices) > 0:
                print(
                    f"The following players have solved the crime in the last turn: {newly_won_player_indices}"
                )
            newly_won_observer_indices = [
                index for index in newly_won_agent_indices if index in observer_indices
            ]
            if len(newly_won_observer_indices) > 0:
                print(
                    f"The following observers have solved the crime in the last turn: {newly_won_observer_indices}"
                )
            if len(won_agent_indices) == len(agent_indices):
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
    agents = {}
    for agent_index, agent_type in enumerate(agent_types):
        agent = agent_type(
            agent_index=agent_index,
            player_indices=list(range(n_players)),
            n_cards_per_player=n_cards_per_player,
            **(
                {"rumor_cards": [rumor_deck.pop() for _ in range(n_cards_per_player)]}
                if issubclass(agent_type, BasePlayer)
                else {}
            ),
        )
        agents[agent_index] = agent
    game_setup = GameSetup(
        crime=crime,
        extra_cards=extra_cards,
        agents=agents,
    )
    return game_setup


def game_simulator(
    player_types: Sequence[type[BasePlayer]],
    observer_types: Sequence[type[BaseObserver]] = (),
    artifacting_id: int | None = None,
    reveal_extra_cards_first: bool = False,
) -> None:
    game_setup = set_up_game(player_types=player_types, observer_types=observer_types)
    run_game(
        game_setup=game_setup,
        artifacting_id=artifacting_id,
        reveal_extra_cards_first=reveal_extra_cards_first,
    )


def main() -> None:
    cli_settings = _CliSettings.from_cli_args()
    game_simulator(
        player_types=(
            [SmartBotPlayer] * cli_settings.n_bot_players
            + [UserPlayer] * cli_settings.n_human_players
        ),
        observer_types=([SmartBotObserver] if cli_settings.include_observer else []),
        artifacting_id=cli_settings.artifacting_id,
        reveal_extra_cards_first=cli_settings.reveal_extra_cards_first,
    )


class _CliSettings(BaseSettings):
    model_config = SettingsConfigDict(cli_kebab_case=True, cli_implicit_flags=True)

    n_bot_players: int = 0
    n_human_players: int = 0
    include_observer: bool = False
    artifacting_id: int | None = None
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
