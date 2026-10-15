import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from convert import parse_int

def test_number():
    assert parse_int("42") == 42


def test_negative():
    assert parse_int("-7") == -7


def test_bad():
    assert parse_int("abc") == 0


def test_custom_default():
    assert parse_int("x", -1) == -1
