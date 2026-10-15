import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tags import join_tags

def test_two():
    assert join_tags(["a", "b"]) == "#a #b"


def test_one():
    assert join_tags(["py"]) == "#py"


def test_empty():
    assert join_tags([]) == ""
