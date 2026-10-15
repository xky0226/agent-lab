import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from filenames import group_by_stem, strip_ext

def test_strip_plain():
    assert strip_ext("notes.txt") == "notes"
    assert strip_ext("data.txt") == "data"


def test_group():
    assert group_by_stem(["report.txt", "next.txt"]) == {"report": 1, "next": 1}
