from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Literal, TypeVar, cast

import pydantic
from pydantic.alias_generators import to_camel

from common.cards import (
    RUMORS,
    Character,
    Room,
    RumorCard,
    Weapon,
    parse_rumor,
)
from common.consts import GameVariant
from common.io.io import AbstractIo
from common.maths import BooleanStatement, CardIsInLocation

T = TypeVar("T", bound=(Character | Weapon | Room))


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True
    )


class _BaseMessage(BaseModel):
    pass


class _BaseGameHistoryItem(BaseModel):
    pass


class _PlainMessage(_BaseMessage):
    type: Literal["plain_message"] = "plain_message"
    text: str


class _PlayerNamesEntryRequest(_BaseMessage):
    type: Literal["player_names_entry_request"] = "player_names_entry_request"
    text: str
    response: _PlayerNamesEntryResponse | None = None


class _PlayerNamesEntryResponse(_BaseGameHistoryItem):
    player_names: list[str]


class _Banner(_BaseMessage):
    type: Literal["banner"] = "banner"
    text: str


class _Option(BaseModel):
    value: str
    display_name: str


class _ChoiceEntryRequest(_BaseMessage):
    type: Literal["choice_entry_request"] = "choice_entry_request"
    text: str = ""
    options: list[_Option]
    optional: str | None
    response: _ChoiceEntryResponse | None = None


class _ChoiceEntryResponse(_BaseGameHistoryItem):
    value: str | None


class _MultiChoiceEntryRequest(_BaseMessage):
    type: Literal["multi_choice_entry_request"] = "multi_choice_entry_request"
    text: str = ""
    options: list[_Option]
    num_selections: int
    response: _MultiChoiceEntryResponse | None = None


class _MultiChoiceEntryResponse(_BaseGameHistoryItem):
    type: Literal["multi_choice_entry_response"] = "multi_choice_entry_response"
    values: list[str]


class _BooleanStatements(_BaseMessage):
    type: Literal["boolean_statements"] = "boolean_statements"
    boolean_statements: list[str]


Message = (
    _PlainMessage
    | _PlayerNamesEntryRequest
    | _Banner
    | _ChoiceEntryRequest
    | _MultiChoiceEntryRequest
    | _BooleanStatements
)
GameHistoryItem = (
    _PlayerNamesEntryResponse | _ChoiceEntryResponse | _MultiChoiceEntryResponse
)


class GameHistoryExhaustedError(Exception):
    pass


@dataclasses.dataclass
class MessageIo(AbstractIo):
    game_history: list[GameHistoryItem]
    messages: list[Message] = dataclasses.field(init=False)
    latest_probabilities: dict[CardIsInLocation, float] | None = None

    def __post_init__(self) -> None:
        self.messages = []

    def get_human_player_names(self) -> list[str]:
        request = _PlayerNamesEntryRequest(text=self._PLAYER_NAMES_PROMPT)
        self._send(request)
        request.response = _PlayerNamesEntryResponse.model_validate(self._receive())
        return request.response.player_names

    def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool:
        options = ["yes", "no"]
        request = _ChoiceEntryRequest(
            text=prompt,
            options=[_Option(value=o, display_name=o.capitalize()) for o in options],
            optional=None,
        )
        self._send(request)
        request.response = _ChoiceEntryResponse.model_validate(self._receive())
        if request.response.value not in options:
            raise ValueError("Invalid option")
        return request.response.value == "yes"

    def get_extra_cards(self, n_extra_cards: int) -> list[RumorCard]:
        return self.get_rumor_cards(
            prompt=(
                f"Select the {n_extra_cards} extra cards."
                if n_extra_cards > 1
                else "Select the extra card."
            ),
            n_rumor_cards=n_extra_cards,
        )

    def get_rumor_cards(self, prompt: str, n_rumor_cards: int) -> list[RumorCard]:
        request = _MultiChoiceEntryRequest(
            text=prompt,
            options=[
                _Option(value=o.name, display_name=o.name.capitalize()) for o in RUMORS
            ],
            num_selections=n_rumor_cards,
        )
        self._send(request)
        request.response = _MultiChoiceEntryResponse.model_validate(self._receive())
        extra_cards: list[RumorCard] = []
        for rumor_name in request.response.values:
            if (rumor_card := parse_rumor(rumor_name)) is None:
                raise ValueError
            extra_cards.append(rumor_card)
        return extra_cards

    def get_game_variant(self) -> GameVariant:
        request = _ChoiceEntryRequest(
            text=self._GAME_VARIANT_PROMPT,
            options=[
                _Option(value=gv.value, display_name=gv.value.capitalize())
                for gv in GameVariant
            ],
            optional=None,
        )
        self._send(request)

        request.response = _ChoiceEntryResponse.model_validate(self._receive())
        return GameVariant(request.response.value)

    def announce_turn(
        self, turn_index: int, player_name: str, current_player_is_user: bool
    ) -> None:
        whose_turn = (
            "Your Turn"
            if current_player_is_user
            else f"{player_name.capitalize()}'s Turn"
        )
        self._send(_Banner(text=f"Turn {turn_index}: {whose_turn}"))

    def get_rumor_card(
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T:
        if len(options) == 0:
            raise ValueError
        if prefix is not None:
            prompt = f"{prefix}: {prompt}"
        request = _ChoiceEntryRequest(
            text=prompt,
            options=[
                _Option(value=o.name, display_name=o.name.capitalize()) for o in options
            ],
            optional=None,
        )
        self._send(request)
        request.response = _ChoiceEntryResponse.model_validate(self._receive())
        if request.response.value is None:
            raise ValueError
        rumor_card = parse_rumor(rumor_name=request.response.value)
        if rumor_card is None:
            raise ValueError("Invalid rumor")
        if rumor_card in options:
            return cast(T, rumor_card)
        raise ValueError("Invalid option")

    def get_player_index(
        self,
        prompt: str,
        optional: str,
        player_indexes: list[int],
        all_player_names: list[str],
        player_index_of_user: int,
    ) -> int | None:
        request = _ChoiceEntryRequest(
            text=prompt,
            options=[
                _Option(
                    value=all_player_names[i],
                    display_name=(
                        "Me"
                        if i == player_index_of_user
                        else all_player_names[i].capitalize()
                    ),
                )
                for i in player_indexes
            ],
            optional=optional.capitalize(),
        )
        self._send(request)
        request.response = _ChoiceEntryResponse.model_validate(self._receive())
        player_name = request.response.value
        if player_name is None:
            return None
        elif player_name not in all_player_names:
            raise ValueError("Invalid player name")
        return all_player_names.index(player_name)

    def print_(self, msg: str, prefix: str | None = None, end: str = "\n") -> None:
        if prefix is not None:
            msg = f"{prefix}: {msg}"
        self._send(_PlainMessage(text=msg))

    def send_boolean_statements(
        self, boolean_statements: list[BooleanStatement], player_names: list[str]
    ) -> None:
        message = _BooleanStatements(
            boolean_statements=sorted(
                s.to_string(player_names) for s in boolean_statements
            )
        )
        self._send(message)

    def _send(self, message: Message) -> None:
        self.messages.append(message)

    def _receive(self) -> GameHistoryItem | None:
        if len(self.game_history) == 0:
            raise GameHistoryExhaustedError
        return self.game_history.pop(0)
