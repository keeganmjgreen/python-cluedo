from collections.abc import MutableSequence
from copy import deepcopy
from random import shuffle
from typing import Any, TypeVar

T = TypeVar("T", bound=MutableSequence[Any])


def shuffled(iterable: T) -> T:
    iterable_copy = deepcopy(iterable)
    shuffle(iterable_copy)
    return iterable_copy


def sign(x: int | float):
    return +1 if x > 0 else -1 if x < 0 else 0


def print_logo() -> None:
    print(" ██████╗██╗     ██╗   ██╗███████╗██████╗  ██████╗ ")
    print("██╔════╝██║     ██║   ██║██╔════╝██╔══██╗██╔═══██╗")
    print("██║     ██║     ██║   ██║█████╗  ██║  ██║██║   ██║")
    print("██║     ██║     ██║   ██║██╔══╝  ██║  ██║██║   ██║")
    print("╚██████╗███████╗╚██████╔╝███████╗██████╔╝╚██████╔╝")
    print(" ╚═════╝╚══════╝ ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ")
    # Credit: textkool.com
