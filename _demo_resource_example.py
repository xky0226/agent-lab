"""
例题：写一个 resource ——「笔记 Server」

为什么给例题：
    任务 3 是你第一次写 resource，手上没形状。先看一个【完整能跑】的，
    比对着空白填空强。（这门课当初就是为这个写的 —— 光有填空没有例题，看懵。）

⚠️ 例题里【故意没有白名单】。
    它就是个老实巴交的 read_note：用户给个名字，它就去读。
    「怎么防止用户跑出目录」那一格是【你的正菜】，例题不代劳。

resource 的三样东西（跟你 mcp_server.py 里要写的一模一样）：

    ① 一个【基础目录】—— 只读这个目录底下的东西
    ② @server.resource("file:///notes/{name}")   ← 花括号 = 模板资源
    ③ 函数参数名必须叫 name（跟花括号里那个一模一样，差一个字都不认）

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_resource_example.py
"""

import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError

笔记目录 = (Path(__file__).parent / "notes").resolve()

server = MCPServer("笔记例题")


@server.resource("file:///notes/{name}")
def read_note(name: str) -> str:
    """读取笔记库里的一个文件。"""
    路径 = 笔记目录 / name                     # 第一跳：目录 / 名字
    try:
        return 路径.read_text(encoding="utf-8")  # 第四跳：读出来
    except OSError as e:
        # ⚠️ 这里抛的【不是】FileNotFoundError，是 MCP 自己的异常类。
        #    差别见 _demo_resource_error.py 的实跑：普通异常的原话会被 SDK 吞掉，
        #    客户端只看到一句干巴巴的 "UnexpectedResourceError: ..." —— 你白写了。
        raise ResourceNotFoundError(f"读不到 {name}：{e}") from e


async def main():
    print("=" * 72)
    print("例题跑三枪")
    print("=" * 72)

    print()
    print("【枪 1】正常读一个文件")
    结果 = await server.read_resource("file:///notes/使用说明.txt")
    print(f"   ✅ 返回的是一串【内容块】，不是字符串：")
    print(f"      {list(结果)}")
    print(f"   取第一块的 .content 就是正文：{list(结果)[0].content[:40]}…")

    print()
    print("【枪 2】文件不存在 —— 看报错里你写的那句话还在不在")
    try:
        await server.read_resource("file:///notes/根本没有这个.txt")
    except Exception as e:
        print(f"   🛑 {type(e).__name__}: {e}")

    print()
    print("【枪 3】拿 ../ 往外跳 —— 看【是谁】挡的")
    try:
        await server.read_resource("file:///notes/../../agent-lab/secret.txt")
    except Exception as e:
        print(f"   🛑 {type(e).__name__}: {e}")
        print()
        print("   注意这句话是谁说的：read_note 里【完全没有】防越界的代码，")
        print("   可它还是被挡住了 —— 因为 SDK 在【模板匹配那一层】就把它拦下了，")
        print("   你的 read_note 压根没被调用。")
        print()
        print("   ⇒ 那问题来了：SDK 都挡了，你要写的白名单到底在防谁？")

    print()
    print("=" * 72)
    print("再问 server：你登记了什么？")
    print("=" * 72)
    print(f"   普通资源（写死 URI 的）：{await server.list_resources()}")
    for t in await server.list_resource_templates():
        print(f"   模板资源（带 {{}} 的）：  uri_template = {t.uri_template!r} / 函数名 = {t.name}")


asyncio.run(main())
