import dataclasses

from common.agent_utils import BasePlayer
from common.cards import (
    RUMOR_TYPES,
    Crime,
    RumorCard,
)
from common.io.text_io import TextIo


@dataclasses.dataclass
class UserPlayer(BasePlayer):
    textio: TextIo = dataclasses.field(default_factory=TextIo)

    def try_solving_crime(self) -> Crime | None:
        if self.textio.get_yes_or_no(
            prompt="Do you want to try solving the crime?",
            prefix=self._prefix,
            default=False,
        ):
            return self._get_crime()

    def make_guess(self, turn_index: int | None = None) -> Crime:
        print(f"{self._prefix}: It's your turn to make a guess.")
        return self._get_crime()

    def answer_guess(self, guess: Crime) -> RumorCard | None:
        options = set(guess) & set(self.rumor_cards)
        if len(options) == 0:
            return None
        if len(options) == 1:
            return options.pop()
        else:
            return self.textio.get_rumor_card(
                "Select a rumor card in answer to the guess",
                self._prefix,
                list(options),
            )

    def _get_crime(self) -> Crime:
        guess = Crime(
            **{
                f: self.textio.get_rumor_card(
                    f"Select a {f}", self._prefix, rt.instances()
                )
                for f, rt in zip(Crime._fields, RUMOR_TYPES, strict=True)
            }  # type: ignore
        )
        return guess

    @property
    def _prefix(self) -> str:
        return f"Player {self.agent_index}"
