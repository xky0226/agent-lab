r""".is_relative_to() 是什么意思 —— 名字拆开 + 实跑

        跑法：.venv\Scripts\python.exe _demo_is_relative_to.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

资源目录 = (Path(__file__).parent / "docs").resolve()

print("=" * 74)
print("先把名字拆开念")
print("=" * 74)
print("     is        relative            to")
print("     └ 是不是   └ 相对的            └ 对于")
print()
print("     连起来：「我是不是（相对于你来说）在你里面」")
print("     中文最顺的说法：「我在不在它里面」")

print()
print("=" * 74)
print("实跑：拿真实目录当靶子")
print("=" * 74)
靶子 = [
    ("docs\\服务器清单.txt", (资源目录 / "服务器清单.txt").resolve()),
    ("docs 目录自己",        资源目录),
    ("往上跳一级的 secret.txt", (资源目录 / "../secret.txt").resolve()),
    ("走 junction 近路的",     (资源目录 / "近路/秘密.txt").resolve()),
]
for 说明, 路径 in 靶子:
    在 = 路径.is_relative_to(资源目录)
    print(f"     {说明:<28} {str(路径):<52} → {在}")

print()
print("=" * 74)
print("它【不会】骗你的地方：前缀像不算数")
print("=" * 74)
print(f"     'secret.txt'     在不在 docs 里？{Path('secret.txt').is_relative_to('docs')}")
print(f"     'docs_bak/x.txt' 在不在 docs 里？{Path('docs_bak/x.txt').is_relative_to('docs')}")
print(f"     'docs/x.txt'     在不在 docs 里？{Path('docs/x.txt').is_relative_to('docs')}")
print("     ⚠️ 第三行那两个字符串【长得像】，但 is_relative_to 认的是【路径的层级】，")
print("        不是【字符串的前几个字】—— 所以 docs_bak 骗不到它。")

print()
print("=" * 74)
print("顺带分清它和兄弟 relative_to（名字只差一个 is）")
print("=" * 74)
print(f"     is_relative_to  → 是个【问句】，只回 True / False，问不出也不生气")
print(f"        Path('docs/x.txt').is_relative_to('docs')  →  {Path('docs/x.txt').is_relative_to('docs')}")
print()
print(f"     relative_to     → 是个【计算】，回的是【相对的那一小截】，算不出就报错")
print(f"        Path('docs/x.txt').relative_to('docs')     →  {Path('docs/x.txt').relative_to('docs')!r}")
try:
    真出不去 = Path("secret.txt").relative_to("docs")
except ValueError as e:
    print(f"        Path('secret.txt').relative_to('docs')    →  💥 ValueError: {e}")
print()
print("     ⇒ 白名单要的是「问句」，所以 ★2 用带 is 的那个。")
