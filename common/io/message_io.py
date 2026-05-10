import asyncio
import dataclasses
from collections.abc import Sequence
from typing import Any, Literal, TypeVar, cast

import pydantic
from pydantic.alias_generators import to_camel
from socketio import AsyncServer

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

T = TypeVar("T", bound=(Character | Weapon | Room))


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True
    )


class _PlainMessage(BaseModel):
    type: Literal["plain_message"] = "plain_message"
    text: str


class _PlayerNamesEntryRequest(BaseModel):
    type: Literal["player_names_entry_request"] = "player_names_entry_request"
    text: str


class _PlayerNamesEntryResponse(BaseModel):
    player_names: list[str]


class _Banner(BaseModel):
    type: Literal["banner"] = "banner"
    text: str


class _Option(BaseModel):
    value: str
    display_name: str


class _ChoiceEntryRequest(BaseModel):
    type: Literal["choice_entry_request"] = "choice_entry_request"
    text: str = ""
    options: list[_Option]
    optional: str | None


class _RequiredChoiceEntryResponse(BaseModel):
    value: str


class _OptionalChoiceEntryResponse(BaseModel):
    value: str | None


class _MultiChoiceEntryRequest(BaseModel):
    type: Literal["multi_choice_entry_request"] = "multi_choice_entry_request"
    text: str = ""
    options: list[_Option]
    num_selections: int


class _MultiChoiceEntryResponse(BaseModel):
    type: Literal["multi_choice_entry_response"] = "multi_choice_entry_response"
    values: list[str]


@dataclasses.dataclass
class MessageIo(AbstractIo):
    sio: AsyncServer
    sid: str
    receive_queue: asyncio.Queue[dict[str, Any]]

    async def get_human_player_names(self) -> list[str]:
        request = _PlayerNamesEntryRequest(text=self._PLAYER_NAMES_PROMPT)
        await self._send(request)
        response = _PlayerNamesEntryResponse.model_validate(await self._receive())
        return response.player_names

    async def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool:
        options = ["yes", "no"]
        await self._send(
            _ChoiceEntryRequest(
                text=prompt,
                options=[
                    _Option(value=o, display_name=o.capitalize()) for o in options
                ],
                optional=None,
            )
        )

        response = _RequiredChoiceEntryResponse.model_validate(await self._receive())
        if response.value not in options:
            raise ValueError("Invalid option")
        return response.value == "yes"

    async def get_extra_cards(self, n_extra_cards: int) -> list[RumorCard]:
        return await self.get_rumor_cards(
            prompt=(
                f"Select the {n_extra_cards} extra cards."
                if n_extra_cards > 1
                else "Select the extra card."
            ),
            n_rumor_cards=n_extra_cards,
        )

    async def get_rumor_cards(self, prompt: str, n_rumor_cards: int) -> list[RumorCard]:
        await self._send(
            _MultiChoiceEntryRequest(
                text=prompt,
                options=[
                    _Option(value=o.name, display_name=o.name.capitalize())
                    for o in RUMORS
                ],
                num_selections=n_rumor_cards,
            )
        )

        response = _MultiChoiceEntryResponse.model_validate(await self._receive())
        extra_cards: list[RumorCard] = []
        for rumor_name in response.values:
            if (rumor_card := parse_rumor(rumor_name)) is None:
                raise ValueError
            extra_cards.append(rumor_card)
        return extra_cards

    async def get_game_variant(self) -> GameVariant:
        await self._send(
            _ChoiceEntryRequest(
                text=self._GAME_VARIANT_PROMPT,
                options=[
                    _Option(value=gv.value, display_name=gv.value.capitalize())
                    for gv in GameVariant
                ],
                optional=None,
            )
        )

        response = _RequiredChoiceEntryResponse.model_validate(await self._receive())
        return GameVariant(response.value)

    async def announce_turn(
        self, turn_index: int, player_name: str, current_player_is_user: bool
    ) -> None:
        whose_turn = (
            "Your Turn"
            if current_player_is_user
            else f"{player_name.capitalize()}'s Turn"
        )
        await self._send(_Banner(text=f"Turn {turn_index}: {whose_turn}"))

    async def get_rumor_card(
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T:
        if len(options) == 0:
            raise ValueError
        if prefix is not None:
            prompt = f"{prefix}: {prompt}"
        await self._send(
            _ChoiceEntryRequest(
                text=prompt,
                options=[
                    _Option(value=o.name, display_name=o.name.capitalize())
                    for o in options
                ],
                optional=None,
            )
        )
        response = _RequiredChoiceEntryResponse.model_validate(await self._receive())
        rumor_card = parse_rumor(rumor_name=response.value)
        if rumor_card is None:
            raise ValueError("Invalid rumor")
        if rumor_card in options:
            return cast(T, rumor_card)
        raise ValueError("Invalid option")

    async def get_player_index(
        self,
        prompt: str,
        optional: str,
        player_indexes: list[int],
        all_player_names: list[str],
        player_index_of_user: int,
    ) -> int | None:
        await self._send(
            _ChoiceEntryRequest(
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
        )

        response = _OptionalChoiceEntryResponse.model_validate(await self._receive())
        player_name = response.value
        if player_name is None:
            return None
        elif player_name not in all_player_names:
            raise ValueError("Invalid player name")
        return all_player_names.index(player_name)

    async def print_(
        self, msg: str, prefix: str | None = None, end: str = "\n"
    ) -> None:
        if prefix is not None:
            msg = f"{prefix}: {msg}"
        await self._send(_PlainMessage(text=msg))

    async def _send(self, message: BaseModel) -> None:
        await self.sio.emit("message", message.model_dump(), to=self.sid)

    async def _receive(self) -> dict[str, Any]:
        return await self.receive_queue.get()
