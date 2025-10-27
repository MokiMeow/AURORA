from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pycalc import add


def test_add_returns_sum():
    assert add(2, 3) == 5

