"""
Path 招式速览 —— 读文件要用的那几招，一次跑给你看。

为什么要跑这个：
    任务 3 是「文件系统 Server」，可你上次摸文件是写 tools.py 那会儿，手生了。
    与其翻文档，不如让电脑跑一遍给你看。

⚠️ 这些招式你其实【早就写过】—— 打开 tools.py，搜一下 todos.json：

        待办账本 = Path(__file__).parent / "todos.json"     ← 第 ① 招
        文字 = 待办账本.read_text(encoding="utf-8")           ← 第 ④ 招

    今天没有新东西，只是把它用在【用户给的名字】上 ——
    多出来的那层「防他乱跑」，才是任务 3 的正菜。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_path.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

基础目录 = (Path(__file__).parent / "docs").resolve()

print("=" * 72)
print(f"基础目录 = {基础目录}")
print("=" * 72)

print()
print("① 拼路径 —— 目录 / 名字")
路径 = 基础目录 / "服务器清单.txt"
print(f"     基础目录 / '服务器清单.txt'   →  {路径}")
print("     ⚠️ 斜杠不是「字符串相加」。它是「进到这一格里面去」。")
print("        用 + 拼字符串迟早出事，用 / 才是路径该有的样子。")

print()
print("② 问它在不在、是不是文件")
print(f"     .exists()  →  {路径.exists()}")
print(f"     .is_file() →  {路径.is_file()}")
print(f"     不存在的名字： .exists() →  {(基础目录 / '不存在的').exists()}")
print(f"     目录本身：     .is_file() →  {基础目录.is_file()}   ← 目录不是文件")

print()
print("③ 算真实路径 —— .resolve()")
绕路 = 基础目录 / "../docs_bak/秘密.txt"
print(f"     原始：        {绕路}")
print(f"     resolve 之后：{绕路.resolve()}")
print("     ⚠️ 这才是「它到底要去哪」。字符串长什么样不算数，")
print("        电脑最后打开的那个文件才算数 —— 判断必须在 resolve 之后做。")
print("        （跟 get_weather 的 date 一样：要用「真的那个值」去判断）")

print()
print("④ 读出来 —— .read_text(encoding='utf-8')")
第一行 = 路径.read_text(encoding="utf-8").splitlines()[0]
print(f"     读到的第一行：{第一行}")
print("     （encoding 必须写。不写的话 Windows 会按 GBK 去读 UTF-8 文件，中文直接乱码）")

print()
print("⑤ 还有一招：问「我在不在这儿里面」")
print("     Path 身上名字里带 relative / parent 的方法有：")
for 名字 in dir(Path):                     # dir(Path) = 把 Path 身上所有的名字列出来
    if "relative" in 名字 or "parent" in 名字:
        print(f"        {名字}")
print("     提示：你要找的那个，返回的是 True / False ——")
print("           名字里的 relative 是「相对」，问的是「你是不是相对它而言在里面」。")
print("           ⚠️ 别用 str(...).startswith(str(...)) 去凑，项目根目录里")
print("              那个 docs_bak/ 就是专门拿来打这个脸的。")
