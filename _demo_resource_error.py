"""
探边界：resource 的函数里抛异常，客户端到底收得到什么？

为什么要跑这个：
    tool 出错时你早就知道会发生什么 —— 变成一个 is_error=True 的【结果】返回，
    消息原封不动，模型看得见。那是 MCP 特意这么设计的（错误是给模型看的信息）。
    但 resource 出错呢？没人告诉过我们。
    而你任务 3 里"文件不存在"是必然要处理的一种情况 ——
    所以得先亲眼看清：抛哪种异常，你写的那句话才留得住。

这个脚本干的事：
    起一个临时 server，挂一个 resource，函数里按 name 抛不同的异常，
    然后一行行看客户端收到的到底是什么。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_resource_error.py

该看哪儿：
    最后两行 —— 普通异常（FileNotFoundError / ValueError）那一栏。
    看客户端收到的是【你写的那句话】，还是一句干巴巴的
    "UnexpectedResourceError: Error creating resource from template …"。
"""

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import (
    ResourceError,
    ResourceNotFoundError,
    UnexpectedResourceError,
)

server = MCPServer("探边界：resource 报错")


@server.resource("file:///docs/{name}")
def read_doc(name: str) -> str:
    if name == "正常":
        return "读到了，一切正常"
    if name == "普通异常-文件没找到":
        raise FileNotFoundError(f"【我的原话】没有这个文件：{name}")
    if name == "普通异常-自己造的":
        raise ValueError(f"【我的原话】这个参数我不认：{name}")
    if name == "MCP的-NotFound":
        raise ResourceNotFoundError(f"【我的原话】没有这个文件：{name}")
    if name == "MCP的-ResourceError":
        raise ResourceError(f"【我的原话】资源出问题了：{name}")


async def main():
    print("=" * 72)
    print("同一个 resource，函数里抛不同的异常，看看客户端那侧收到什么")
    print("=" * 72)
    for name in [
        "正常",
        "普通异常-文件没找到",
        "普通异常-自己造的",
        "MCP的-NotFound",
        "MCP的-ResourceError",
    ]:
        print(f"\n【函数里写的是：{name}】")
        try:
            结果 = await server.read_resource(f"file:///docs/{name}")
            print(f"   ✅ 没报错，返回：{str(list(结果))[:80]}")
        except Exception as e:
            print(f"   🛑 客户端收到 → {type(e).__name__}")
            print(f"        消息：{e}")
            if isinstance(e, UnexpectedResourceError) and e.__cause__:
                print(f"        （真话被塞进 __cause__ 里了：{e.__cause__}）")

    print()
    print("=" * 72)
    print("结论自己填：")
    print("=" * 72)
    print("  哪种异常，我写的那句话【原封不动】到了客户端？")
    print("  哪种异常，客户端只看到一句『出错了』，我的话被吞了？")


asyncio.run(main())
