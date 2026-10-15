import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clean import normalize

def test_edges():
    assert normalize("\ta\n") == "a"


def test_inner_spaces():
    assert normalize("  a  b  ") == "a b"
