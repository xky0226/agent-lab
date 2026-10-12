"""⑥ 验收：MCP 版那四条防线，还顶不顶用？

step4_guard.py 那四条线，换了接法之后必须重新验一遍 —— 因为
「跑通了」不代表「防线还在」。新接法里最该怀疑的是两条：

    ③ 参数错   —— 手写版靠 try/except 抓；MCP 版换成了 if 结果.is_error
                  ⭐ 这是我们【新写的判断】，最可能是假的
    ② 假工具名 —— 手写版比 tools.TOOL_MAP；MCP 版比的是自己攒的名字集合

（① 坏 JSON 一个字没改；④ 轮次上限也没改。但"按理说"不算数 ——
  顺手一起跑，反正便宜。）

它怎么工作：
    四个场景挨个演一遍，每个场景【只打开一个开关】，
    然后去输出里找【那句应该出现的话】。

    ✅ = 那句话真的出现了   → 这条防线还在，而且【真被执行过】
    ❌ = 没出现             → 防线没触发 / 被吞了 / 代码根本没走到

⚠️ 这不是"看一眼颜色"，是"读它到底说了什么" —— 所以每个 ✅ 旁边都把
   那句话【原文】贴出来，你自己核对一遍。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _check_mcp_guard.py
"""

import asyncio
import contextlib
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import step5_mcp                                   # 开关和 main() 都住这儿

# (场景名, 要打开的开关, 应该在输出里出现的那句话)
场景们 = [
    ("① 坏 JSON",  "注入坏JSON",   "arguments 不是合法 JSON"),
    ("② 假工具名", "注入假工具名", "瞎编工具名"),
    ("③ 参数错",   "注入坏参数",   "工具报错"),
    ("④ 轮次上限", None,           "轮次用尽"),
]


def 复位():
    """每个场景开跑前，把所有开关关掉 —— 一次只动一个变量。"""
    step5_mcp.注入坏JSON = False
    step5_mcp.注入坏参数 = False
    step5_mcp.注入假工具名 = False
    step5_mcp.上限 = 8


def 跑一个场景(开关):
    复位()
    if 开关:
        setattr(step5_mcp, 开关, True)
    if 开关 is None:                 # ④：靠"轮次上限=1"逼出半成品
        step5_mcp.上限 = 1

    缓冲 = io.StringIO()
    with contextlib.redirect_stdout(缓冲):
        asyncio.run(step5_mcp.main())
    return 缓冲.getvalue()


全绿 = True
for 名字, 开关, 应出现 in 场景们:
    输出 = 跑一个场景(开关)
    行们 = 输出.splitlines()
    命中 = [行.strip() for 行 in 行们 if 应出现 in 行]

    # 顺便把"模型怎么收尾的"也带出来 —— 防线接住之后，它有没有自己救回来
    收口 = [行.strip() for 行 in 行们 if 行.strip().startswith("🏁")]

    print(f"\n{'=' * 60}")
    if 命中:
        print(f"✅ {名字}  —— 防线在，而且真跑到了")
        for 行 in 命中[:2]:
            print(f"     原话：{行}")
        if 收口:
            print(f"     收尾：{收口[0][:90]}")
    else:
        全绿 = False
        print(f"❌ {名字}  —— 没找到「{应出现}」")
        print("     整段输出（前 25 行）：")
        for 行 in 行们[:25]:
            print(f"       {行}")

print(f"\n{'=' * 60}")
print("🏁 四条防线全部在位 —— MCP 版跟手写版一样扛得住" if 全绿
      else "🏁 有 ❌ —— 注意：报 ❌ 不等于防线坏了，也可能是【压根没被触发】。\n"
           "   两种要分清：是「没走到那一步」，还是「走到了但没拦住」。")
print("=" * 60)
