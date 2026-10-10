"""
探边界：ResourceSecurity 到底挡住了什么，什么能钻到函数里头？

为什么要跑这个：
    任务 3 的白名单，靶子是"别让模型读到 docs 外面的东西"。
    但 SDK 自己已经挡了一层（../ 和绝对路径）。
    那就必须先搞清楚：哪几种越界【在进门时就被挡了】，哪几种
    【能一路走到你的函数里】—— 不然你会以为白名单是多余的，
    或者反过来，以为 SDK 全包了。

这个脚本干的事：
    起一个临时的 server，只挂一个 resource，函数里【只打印它收到了什么】，
    然后拿各种奇形怪状的 name 去 read_resource，看哪些能到函数里。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_resource_guard.py
"""

import asyncio
import sys

# Windows 控制台默认是 GBK，打不出 ⬅️ 这种字符（会直接 UnicodeEncodeError 崩掉），
# 中文也会变乱码。这一行把 stdout 掰成 utf-8，一劳永逸。
sys.stdout.reconfigure(encoding="utf-8")

from mcp.server.mcpserver import MCPServer

server = MCPServer("探边界")


@server.resource("file:///docs/{name}")
def read_doc(name: str) -> str:
    # 这行能打印出来，就说明这一枪【穿过了 SDK 那道门】，进到函数里了。
    print(f"      ⬅️ 函数被调用了！它收到的 name = {name!r}")
    return f"（假装读到了 {name}）"


# 拿这些去敲门。左边是攻击者能控制的那个 name 拼进 URI 的样子。
枪 = [
    ("正常读一个文件", "file:///docs/员工手册摘录.md"),
    ("../ 往上跳一级", "file:///docs/../secret.txt"),
    ("../../ 跳两级", "file:///docs/../../secret.txt"),
    ("绝对路径（Windows 盘符）", "file:///docs/C:/Windows/win.ini"),
    ("绝对路径（斜杠开头）", "file:///docs//etc/passwd"),
    ("反斜杠跳级", "file:///docs/..\\secret.txt"),
    ("URL 编码的 ..", "file:///docs/%2e%2e/secret.txt"),
    ("空字节", "file:///docs/a\x00.txt"),
    ("junction 那格：字面上一个可疑字符都没有", "file:///docs/近路"),
    ("不存在的文件", "file:///docs/根本没有这个文件.md"),
]


async def main():
    print("=" * 70)
    print("手上有哪些枪，一发一发射，看谁穿得过 SDK 那道门")
    print("=" * 70)
    for 说明, uri in 枪:
        print(f"\n【{说明}】")
        print(f"      URI = {uri!r}")
        try:
            结果 = await server.read_resource(uri)
            片段 = list(结果) if not isinstance(结果, str) else 结果
            print(f"      ✅ 没被挡，返回了：{str(片段)[:80]}")
        except Exception as e:
            print(f"      🛑 {type(e).__name__}: {e}")

    print()
    print("=" * 70)
    print("再看看 server 自己登记了什么（模板资源跟普通资源分开列）")
    print("=" * 70)
    print("  普通资源:", await server.list_resources())
    print("  模板资源:", await server.list_resource_templates())


asyncio.run(main())
