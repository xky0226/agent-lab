import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from grade import grade

def test_top():
    assert grade(95) == "A"


def test_mid():
    assert grade(75) == "C"


def test_pass_line():
    assert grade(60) == "D"


def test_fail():
    assert grade(59) == "F"
