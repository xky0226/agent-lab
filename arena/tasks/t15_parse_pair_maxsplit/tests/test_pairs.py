import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pairs import parse_pair

def test_simple():
    assert parse_pair("a:b") == ("a", "b")


def test_no_colon():
    assert parse_pair("abc") == ("abc", "")


def test_two_colons():
    assert parse_pair("a:b:c") == ("a", "b:c")
