import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from padding import pad_right

def test_pads():
    assert pad_right([1, 2], 4) == [1, 2, 0, 0]


def test_input_untouched():
    src = [1, 2]
    pad_right(src, 4)
    assert src == [1, 2]
