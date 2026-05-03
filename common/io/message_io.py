import dataclasses
import queue
from collections.abc import Sequence
from typing import Any, Literal, cast

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


class _ChoiceEntryRequest(BaseModel):
    type: Literal["choice_entry_request"] = "choice_entry_request"
    text: str = ""
    options: list[str]
    optional: str | None


class _RequiredChoiceEntryResponse(BaseModel):
    value: str


class _OptionalChoiceEntryResponse(BaseModel):
    value: str | None


class _MultiChoiceEntryRequest(BaseModel):
    type: Literal["multi_choice_entry_request"] = "multi_choice_entry_request"
    text: str = ""
    options: list[str]
    num_selections: int


class _MultiChoiceEntryResponse(BaseModel):
    type: Literal["multi_choice_entry_response"] = "multi_choice_entry_response"
    values: list[str]


@dataclasses.dataclass
class MessageIo(AbstractIo):
    send_queue: queue.Queue[dict[str, Any]]
    receive_queue: queue.Queue[dict[str, Any]]

    def get_human_player_names(self) -> list[str]:
        request = _PlayerNamesEntryRequest(text=self._PLAYER_NAMES_PROMPT)
        self.send_queue.put(request.model_dump())
        response = _PlayerNamesEntryResponse.model_validate(self.receive_queue.get())
        return response.player_names

    def get_yes_or_no(
        self, prompt: str, prefix: str | None = None, default: bool | None = None
    ) -> bool:
        options = ["yes", "no"]
        self.send_queue.put(
            _ChoiceEntryRequest(
                text=prompt, options=options, optional=None
            ).model_dump()
        )
        response = _RequiredChoiceEntryResponse.model_validate(self.receive_queue.get())
        if response.value not in options:
            raise ValueError("Invalid option")
        return response.value == "yes"

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
        self.send_queue.put(
            _MultiChoiceEntryRequest(
                text=prompt,
                options=[o.name for o in RUMORS],
                num_selections=n_rumor_cards,
            ).model_dump()
        )
        response = _MultiChoiceEntryResponse.model_validate(self.receive_queue.get())
        extra_cards: list[RumorCard] = []
        for rumor_name in response.values:
            if (rumor_card := parse_rumor(rumor_name)) is None:
                raise ValueError
            extra_cards.append(rumor_card)
        return extra_cards

    def get_game_variant(self) -> GameVariant:
        self.send_queue.put(
            _ChoiceEntryRequest(
                text=self._GAME_VARIANT_PROMPT,
                options=[gv.value for gv in GameVariant],
                optional=None,
            ).model_dump()
        )
        response = _RequiredChoiceEntryResponse.model_validate(self.receive_queue.get())
        return GameVariant(response.value)

    def announce_turn(
        self, turn_index: int, player_name: str, current_player_is_user: bool
    ) -> None:
        self.send_queue.put(
            _Banner(
                text=f"Turn {turn_index}: {'Your Turn' if current_player_is_user else f"{player_name.capitalize()}'s Turn"}"
            ).model_dump()
        )

    def get_rumor_card[T: Character | Weapon | Room](
        self, prompt: str, prefix: str | None = None, options: Sequence[T] = RUMORS
    ) -> T:
        if len(options) == 0:
            raise ValueError
        if prefix is not None:
            prompt = f"{prefix}: {prompt}"
        self.send_queue.put(
            _ChoiceEntryRequest(
                text=prompt, options=[o.name for o in options], optional=None
            ).model_dump()
        )
        response = _RequiredChoiceEntryResponse.model_validate(self.receive_queue.get())
        rumor_card = parse_rumor(rumor_name=response.value)
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
    ) -> int | None:
        options = [all_player_names[i] for i in player_indexes]
        self.send_queue.put(
            _ChoiceEntryRequest(
                text=prompt, options=options, optional=optional
            ).model_dump()
        )
        response = _OptionalChoiceEntryResponse.model_validate(self.receive_queue.get())
        player_name = response.value
        if player_name is None:
            return None
        elif player_name not in all_player_names:
            raise ValueError("Invalid player name")
        return all_player_names.index(player_name)

    def print_(self, msg: str, prefix: str | None = None, end: str = "\n") -> None:
        if prefix is not None:
            msg = f"{prefix}: {msg}"
        self.send_queue.put(_PlainMessage(text=msg).model_dump())
