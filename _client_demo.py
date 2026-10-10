"""
最小 MCP 客户端：真的把 mcp_server.py 当【另一个进程】拉起来，用 stdio 说话。

跟 _probe_tools.py 的根本区别 ——
    探针：  import mcp_server      ┐ 同一个进程
            守卫 __name__ != "__main__" 被跳过，文件一路跑到底  ┘

    这个：  subprocess 拉起新进程   ┐ 两个进程
            新进程里 __name__ == "__main__"，跑到那就开跑       ┘

所以探针绿不代表这个绿。两个都要跑。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _client_demo.py
"""

import asyncio
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# 让子进程用【当前这个解释器】去跑 mcp_server.py，
# 免得 PATH 里的 python 是另一个、没装 mcp。
启动参数 = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server.py"],
)


async def main():
    # stdio_client 帮我建好两根管子：读子进程的 stdout、往它的 stdin 写。
    async with stdio_client(启动参数) as (读, 写):
        async with ClientSession(读, 写) as 会话:
            # 握手。说好版本、换掉能力清单。
            握手结果 = await 会话.initialize()
            服务器自报 = 握手结果.server_info
            print(f"连上了：{服务器自报.name}  version={服务器自报.version}")
            print(f"协议版本：{握手结果.protocol_version}")
            print()

            工具们 = await 会话.list_tools()
            结果 = await 会话.call_tool("get_weather", {"city": "成都", "date": "2026-10-08"})
            print(结果)
            print(f"它报上来的工具：{len(工具们.tools)} 件")
            for t in 工具们.tools:
                print(f"  ┌─ {t.name}")
                print(f"  │  说明书 = {t.description!r}")
                print(f"  └─ 参数   = {t.input_schema}")


asyncio.run(main())
