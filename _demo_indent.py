"""缩进到底是个啥？—— 同一段代码，只动缩进，输出完全不同。

    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_indent.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

资源目录 = Path(__file__).resolve().parent / "docs"

print("=" * 66)
print("① 缩进 = 站在【门里】")
print("=" * 66)
for 文件 in 资源目录.iterdir():
    if 文件.is_file():
        print(f"  [门里] 是文件：{文件.name}")
    print(f"  [门外] 不管是不是文件，我都打一行：{文件.name}")

print()
print("  读法：")
print("    `result += ...` 缩进 —— 它站在 if 的门【里】面，if 不成立就轮不到它")
print("    最后那行 print 不缩进 —— 它站在门【外】，每转一圈都跑，if 说不上话")

print()
print("=" * 66)
print("② 缩进 = 【谁包着谁】。Python 没有大括号，用空格代替 {}")
print("=" * 66)
print("""
    for 文件 in 资源目录.iterdir():      ← 这层：每转一圈跑一次
        if 文件.is_file():               ← 站进 for 的门里；每圈都被问一次
            result += 文件.name          ← 站进 if 的门里；只有"是文件"才轮到

    一层包一层。想让它归谁管，就往右挪 4 格；
    想让它从谁手里跑掉，就往左挪回来。
""")

print("=" * 66)
print("③ 你其实【早就在用了】")
print("=" * 66)
print("""
    result = ""
    for 文件 in 资源目录.iterdir():
        result += f"{文件.name}\\n"

    这一行你缩进了 —— 所以它【每转一圈加一次】。
    要是把它顶格写（不缩进），整段就只加【最后一次】。
""")
print("=" * 66)
