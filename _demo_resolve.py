r""".resolve() 到底干了什么 —— 三件事，一件一件跑给你看

        跑法：.venv\Scripts\python.exe _demo_resolve.py

    你以为它只干第二件。其实它干三件，第三件才是白名单真正的命门。
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

资源目录 = (Path(__file__).parent / "docs").resolve()

print("=" * 74)
print("第一件：相对路径 → 绝对路径")
print("=" * 74)
相对的 = Path("docs/服务器清单.txt")
print(f"     原样：       {相对的}")
print(f"     resolve 后： {相对的.resolve()}")
print("     ⚠️ 它补的那截是从【当前目录】来的 —— 所以这事儿跟你在哪启动有关。")

print()
print("=" * 74)
print("第二件：把 . 和 .. 算平   ← 你说的就是这件")
print("=" * 74)
绕路 = 资源目录 / "../secret.txt"
print(f"     原样：       {绕路}")
print(f"     resolve 后： {绕路.resolve()}")

print()
print("=" * 74)
print("第三件：把【快捷方式】展开成真身   ← 这件的杀伤力最大")
print("=" * 74)
近路 = 资源目录 / "近路/秘密.txt"
print(f"     原样：       {近路}")
print(f"     resolve 后： {近路.resolve()}")
print()
print("     docs\\近路 是个 junction（Windows 的快捷方式文件夹），指向 docs_bak。")
print("     字面上它【明明在 docs 里面】—— 没有 .. ，也没有绝对路径。")
print(f"        拿【字面】比 startswith(资源目录)：      {str(近路).startswith(str(资源目录))}   ← 放行了 ❌")
print(f"        拿【落点】比 is_relative_to(资源目录)：   {近路.resolve().is_relative_to(资源目录)}   ← 抓住了 ✅")
print()
print(f"     真去读一下，读到的是：{近路.resolve().read_text(encoding='utf-8').strip()[:30]!r}")
