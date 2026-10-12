"""任务 2 的验收：翻译的【原料】对不对 + 你转出来的【成品】对不对。

任务 2 有两个可能出错的地方，长得完全不一样：

    ① 原料不对 —— MCP 给的 input_schema 跟手写 TOOLS 里的 parameters 本来就不同
    ② 装箱不对 —— 原料一样，但你搬错了键（比如壳里写成 "input_schema" 而不是 "parameters"）

这个脚本两个都查。它做三件事：

    A. 真拉起 mcp_server.py（新进程），list_tools() 拿回全部
    B. 调【你自己写的】step5_mcp.转成openai工具() 翻译一遍
    C. 跟 tools.TOOLS 逐字段对账，差异一条条列出来

⚠️ 2026-10-12 起：mcp_server 有 7 件，tools.TOOLS 只有 5 件 —— 差的那 2 件
   （list_docs / write_note）是 ⑦ 四件套里 MCP【独有】的，tools.py 里本来就没有
   对照物。所以只比【两边都有】的那 5 件，独有件跳过、不算差异。
   （原来是"件数不相等就整脚本退出"，加了新工具就当场假红。）

怎么读结果：

    每件【能对账的】工具一行 ✅ / ❌。❌ 后面跟的是【差在哪】。
    全 ✅ = 任务 2 通关。

    ⚠️ "多出个 title" 不算差异 —— MCP 那边 Pydantic 顺手塞的，OpenAI 会忽略。
       脚本自动把它摘掉再比。（手写版里那些注释性说明不参与对账。）

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _check_mcp_tools.py
"""

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import tools                                  # 手写版：对账的【参照物】
import step5_mcp                              # 你写的翻译函数住这儿

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def 归一化(x):
    """把两边拉齐到同一把尺子上再比。

    - 摘掉 title：MCP 那侧 Pydantic 会塞 "title": "City" 这类，OpenAI 不看它
    - required 排序：["city","date"] 和 ["date","city"] 语义一样，别当差异
    """
    if isinstance(x, dict):
        d = {k: 归一化(v) for k, v in x.items() if k != "title"}
        if isinstance(d.get("required"), list):
            d["required"] = sorted(d["required"])
        return d
    if isinstance(x, list):
        return [归一化(i) for i in x]
    return x


def 找差异(左边, 右边, 路="") -> list:
    """递归把两坨 dict 不一样的地方，按【路径】一条条报出来。"""
    差异 = []
    if isinstance(左边, dict) and isinstance(右边, dict):
        for 键 in sorted(set(左边) | set(右边)):
            这路 = f"{路}.{键}" if 路 else 键
            if 键 not in 左边:
                差异.append(f"{这路}：你这边【少了】，参照物里是 {右边[键]!r}")
            elif 键 not in 右边:
                差异.append(f"{这路}：你这边【多了】{左边[键]!r}")
            else:
                差异 += 找差异(左边[键], 右边[键], 这路)
    elif 左边 != 右边:
        差异.append(f"{路}：你这边是 {左边!r}，参照物是 {右边!r}")
    return 差异


async def main():
    启动参数 = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])

    async with stdio_client(启动参数) as (读, 写):
        async with ClientSession(读, 写) as 会话:
            await 会话.initialize()
            工具清单 = (await 会话.list_tools()).tools

    参照 = {t["function"]["name"]: t for t in tools.TOOLS}
    名字们 = [t.name for t in 工具清单]
    对账的 = [n for n in 名字们 if n in 参照]
    新加的 = [n for n in 名字们 if n not in 参照]

    print(f"MCP 交了 {len(工具清单)} 件，tools.TOOLS 有 {len(tools.TOOLS)} 件")
    print(f"  能对账的：{len(对账的)} 件 {对账的}")
    print(f"  没对照物的：{新加的}")
    print("     ← MCP 独有的工具，手写版本来就没有 → 跳过，不算差异")
    print()

    全绿 = True

    for t in 工具清单:
        名字 = t.name
        if 名字 not in 参照:
            continue

        try:
            转换 = step5_mcp.转成openai工具(t)
        except Exception as e:
            打印 = f"❌ {名字}：转成openai工具() 抛异常 {type(e).__name__}: {e}"
            print(打印)
            全绿 = False
            continue

        if 转换 is None:
            print(f"❌ {名字}：转成openai工具() 返回了 None —— 函数体还是 `...` 吧？")
            全绿 = False
            continue

        差异 = 找差异(归一化(转换), 归一化(参照[名字]))
        if 差异:
            全绿 = False
            print(f"❌ {名字}：")
            for d in 差异:
                print(f"     · {d}")
        else:
            print(f"✅ {名字}")

    print()
    print("════════════════════════════════════")
    print(f"🏁 任务 2 通关 —— 有对照物的 {len(对账的)} 件全过" if 全绿
          else "🏁 还有 ❌ —— 照上面那几行改")
    print("════════════════════════════════════")


asyncio.run(main())
