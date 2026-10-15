import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from boxes import add_item

def test_one_call():
    assert add_item("a", 1) == {"a": 1}


def test_two_calls_independent():
    add_item("x", 1)
    box = add_item("y", 2)
    assert box == {"y": 2}
