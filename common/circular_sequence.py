import dataclasses
from collections.abc import Sequence
from typing import Any

from common.utils import sign


@dataclasses.dataclass
class CircularSequence[T: Any]:
    items: Sequence[T]

    def get_item(self, index: int) -> T:
        return self.items[index % len(self.items)]

    def get_offset_item(self, item: T, offset: int) -> T:
        index = self.items.index(item)
        return self.get_item(index + offset)

    def get_adjacent_items(self, item: T, n: int) -> list[T]:
        if n == 0:
            return []
        index = self.items.index(item)
        return [self.get_item(index + (i + 1) * sign(n)) for i in range(abs(n))]
