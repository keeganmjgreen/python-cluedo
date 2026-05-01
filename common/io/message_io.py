import dataclasses
import queue
from collections.abc import Sequence
from typing import Any, Literal, cast

import pydantic
from pydantic.alias_generators import to_camel

from common.cards import (
    CHARACTER_NAMES,
    ROOM_NAMES,
    RUMORS,
    WEAPON_NAMES,
    Character,
    Room,
    Weapon,
)


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=to_camel)


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
    optional: bool


class _RequiredChoiceEntryResponse(BaseModel):
    value: str


class _OptionalChoiceEntryResponse(BaseModel):
    value: str | None


@dataclasses.dataclass
class MessageIo:
    send_queue: queue.Queue[dict[str, Any]]
    receive_queue: queue.Queue[dict[str, Any]]

    def get_human_player_names(self) -> list[str]:
        request = _PlayerNamesEntryRequest(
            text=(
                "Please provide the player names in turn order, "
                "beginning with the starting player."
            )
        )
        self.send_queue.put(request.model_dump())
        response = _PlayerNamesEntryResponse.model_validate(self.receive_queue.get())
        return response.player_names

    def announce_turn(self, turn_index: int, player_name: str) -> None:
        self.send_queue.put(
            _Banner(text=f"Turn {turn_index}: {player_name.capitalize()}").model_dump()
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
                text=prompt, options=[o.name for o in options], optional=False
            ).model_dump()
        )
        response = _RequiredChoiceEntryResponse.model_validate(self.receive_queue.get())
        rumor_name = response.value
        if rumor_name in CHARACTER_NAMES:
            rumor = Character(name=rumor_name)
        elif rumor_name in WEAPON_NAMES:
            rumor = Weapon(name=rumor_name)
        elif rumor_name in ROOM_NAMES:
            rumor = Room(name=rumor_name)
        else:
            raise ValueError("Invalid rumor")
        if rumor in options:
            return cast(T, rumor)
        raise ValueError("Invalid option")

    def get_player_index(
        self, player_indexes: list[int], all_player_names: list[str]
    ) -> int | None:
        options = [all_player_names[i] for i in player_indexes]
        self.send_queue.put(
            _ChoiceEntryRequest(options=options, optional=True).model_dump()
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
