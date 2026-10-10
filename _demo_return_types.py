"""工具的【返回值】能是什么东西？—— 三件工具，三种返回，看客户端收到什么。

起因：你在 list_docs 里写了 `return NotImplementedError("资料库为空")`。
     —— "raise 去掉，还是报错吧？" 不是。去掉 raise 之后，
        那行字只是【造了一个对象】，跟 Path("x") 一样的造法，
        然后当成【结果】交出去了。

到底会怎样，别猜，跑：

    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_return_types.py

（不走真进程、不 spawn 子进程 —— 直接问 server 对象，够用了。
  因为这里要看的只是"返回值怎么被装箱"，跟跨不跨进程无关。）
"""

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp.server.mcpserver import MCPServer

server = MCPServer("probe")


@server.tool()
def return_exception_object() -> str:
    """★ 探针 1：返回一个【异常对象】—— 注意，没有 raise，就只是 return 它。"""
    return NotImplementedError("资料库为空,没有检索到资料")


@server.tool()
def return_list() -> str:
    """★ 探针 2：返回一个【列表】（跟 10-03 那次 materials 的形状一样）。"""
    return ["员工手册摘录.md", "服务器清单.txt"]


@server.tool()
def return_plain_string() -> str:
    """★ 探针 3：对照组 —— 老老实实返回【一句话】。"""
    return "资料库为空,没有检索到资料"


async def main():
    print("=" * 66)
    print("三件工具，三种返回值，客户端分别收到什么？")
    print("=" * 66)

    for 名字 in ["return_exception_object", "return_list", "return_plain_string"]:
        print(f"\n【{名字}】")
        try:
            结果 = await server.call_tool(名字, {})
        except Exception as e:
            print(f"  💥 直接炸了：{type(e).__name__}: {e}")
            continue

        print(f"  is_error      = {结果.is_error}")
        块们 = 结果.content or []
        for i, 块 in enumerate(块们):
            print(f"  content[{i}]     = type={type(块).__name__}  "
                  f"text={getattr(块, 'text', None)!r}")
        if not 块们:
            print("  content       = （空）")
        print(f"  structured    = {结果.structured_content!r}")

    print()
    print("=" * 66)
    print("读法：客户端（也就是模型）【只看得到 content 里的 text】。")
    print("     structured_content 是给程序看的，模型那边不一定拿得到。")
    print("=" * 66)


asyncio.run(main())
