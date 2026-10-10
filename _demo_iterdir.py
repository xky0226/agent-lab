"""iterdir() 吐出来的到底是什么？—— 它不是列表，是【生成器】。

起因：list_docs 里 `path = 资源目录.iterdir()`。
      能 for 它 —— 但除了 for，它还有一堆"不能"。

跑：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_iterdir.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

资源目录 = Path(__file__).resolve().parent / "docs"


def 试试(说明, 动作):
    try:
        print(f"  {说明:<28} →  {动作()!r}")
    except Exception as e:
        print(f"  {说明:<28} →  💥 {type(e).__name__}: {e}")


print("=" * 70)
print("① 它是什么东西")
print("=" * 70)
path = 资源目录.iterdir()
试试("type(path)", lambda: type(path).__name__)
试试("len(path)", lambda: len(path))          # 有几个？
试试("path[0]", lambda: path[0])              # 第几个？
试试("path[0:2]", lambda: path[0:2])          # 切一段？
试试("dir(path) 里有没有 __len__", lambda: "__len__" in dir(path))
试试("dir(path) 里有没有 __iter__", lambda: "__iter__" in dir(path))
试试("dir(path) 里有没有 __next__", lambda: "__next__" in dir(path))

print()
print("=" * 70)
print("② ⚠️ 它只能被【消费一次】—— 这个坑最阴")
print("=" * 70)
print(f"  第 1 次 for：{list(资源目录.iterdir())}")
print(f"  上面那行是重新生成的，不算数。下面才是同一个 path 连着用两次：")
path = 资源目录.iterdir()
第一次 = [p for p in path]
第二次 = [p for p in path]
print(f"    第 1 次 for 拿到的：{[p.name for p in 第一次]}")
print(f"    第 2 次 for 拿到的：{[p.name for p in 第二次]}   ← 空！它已经被掏干了")

print()
print("  转成列表就不怕了：")
path = list(资源目录.iterdir())
print(f"    list() 之后，能 len：{len(path)}")
print(f"    连着 for 两次：{[p.name for p in path]} / {[p.name for p in path]}")

print()
print("=" * 70)
print("③ 每个元素是什么")
print("=" * 70)
for p in 资源目录.iterdir():
    print(f"  type={type(p).__name__:<12} p={p}")
    print(f"      str(p)  = 它【在哪】：{p}")
    print(f"      p.name  = 它【叫什么】：{p.name}")
    print(f"      p.is_file() = {p.is_file()}")

print()
print("=" * 70)
print("一句话：iterdir() 是个【水龙头】，不是【水桶】。")
print("       拧一次出一滴；想反复看，先接进桶里（list()）。")
print("=" * 70)
