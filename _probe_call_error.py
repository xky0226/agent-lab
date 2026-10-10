"""
探针：工具调用【出错】的时候，call_tool 到底抛不抛异常？

同一个 call_tool，三种入参，三种下场：

    ① 参数合法、工具也跑通        → 正常返回
    ② 参数合法、工具【内部】炸了   → ？    ← 本次要问的
    ③ 参数【本身】不合法           → ？    ← 顺手一起问，两种错不是一回事

跑法：
    .venv\\Scripts\\python.exe _probe_call_error.py
"""

import asyncio
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

启动参数 = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

案子们 = [
    ("① 合法 + 工具跑得通", "get_weather", {"city": "成都", "date": "2026-10-08"}),
    ("② 合法 + 工具内部炸", "get_weather", {"city": "成都", "date": "abc"}),
    ("③ 参数本身少一个", "get_weather", {"city": "成都"}),
]


async def main():
    async with stdio_client(启动参数) as (读, 写):
        async with ClientSession(读, 写) as 会话:
            await 会话.initialize()

            for 标题, 工具名, 入参 in 案子们:
                print("=" * 66)
                print(f"{标题}")
                print(f"    call_tool({工具名!r}, {入参})")
                print("=" * 66)
                try:
                    结果 = await 会话.call_tool(工具名, 入参)
                except Exception as e:
                    print(f"  ⟹ 【抛出异常】 {type(e).__name__}")
                    print(f"      {e}")
                    print()
                    continue

                print(f"  ⟹ 【正常返回】 {type(结果).__name__}")
                print(f"      is_error = {结果.is_error}")
                print(f"      content  = {结果.content}")
                if 结果.content:
                    print(f"      content[0].text = {结果.content[0].text!r}")
                print()


asyncio.run(main())
