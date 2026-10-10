r"""五跳拆解：(Path(__file__).parent / "docs").resolve()

        跑法：.venv\Scripts\python.exe _demo_dunder_file.py

看什么：
    每一跳单独打一行。跳 0 → 跳 4 一路看下来，
    你就知道最后那个 D:\toutiao\agent-lab\docs 是【怎么一步步长出来的】。
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

print("跳 0  __file__       =", __file__)
print("跳 1  Path(__file__) =", Path(__file__))
print("跳 2  .parent        =", Path(__file__).parent)
print("跳 3  / 'docs'       =", Path(__file__).parent / "docs")
print("跳 4  .resolve()     =", (Path(__file__).parent / "docs").resolve())
