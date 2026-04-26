from common.circular_sequence import CircularSequence


def test_circular_sequence() -> None:
    sequence = CircularSequence(items=list("abc"))
    assert sequence.get_item(0) == "a"
    assert sequence.get_item(3) == "a"
    assert sequence.get_item(-1) == "c"
    assert sequence.get_item(-3) == "a"

    assert sequence.get_adjacent_items("a", 3) == ["b", "c", "a"]
    assert sequence.get_adjacent_items("a", -4) == ["c", "b", "a", "c"]
    assert sequence.get_adjacent_items("a", 0) == []
