"""工具柜自检 —— 跑一下，看看两个工具是不是真的活着。

跑法（在 agent-lab 目录下，cmd / PowerShell / VS Code 终端都行）：
    .venv\\Scripts\\python.exe _check_tools.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import tools
from datetime import date

今天 = date.today().isoformat()

print("=" * 56)
print("① 工具登记情况")
print("=" * 56)
print("  TOOLS 里的名字：   ", [t["function"]["name"] for t in tools.TOOLS])
print("  TOOL_MAP 的 key：  ", list(tools.TOOL_MAP.keys()))
# 这两行必须【一模一样】——对不上就是「模型点了一道菜，电话簿里没这个号」

print()
print("=" * 56)
print("② 天气工具（真·联网）")
print("=" * 56)
# ⚠️ get_weather 现在要两个参数（第 2 个是日期）—— 少一个整段就 TypeError。
#    用 today 而不是写死日期：wttr.in 只服务今天起 3 天，写死的日期过两天就永远"查不到"了。
for city in ["成都", "北京", "不存在的城市xyz"]:
    print(f"  {city:12s} → {tools.get_weather(city, 今天)}")

print()
print("=" * 56)
print("③ 汇率工具（真·联网）")
print("=" * 56)
cases = [
    ("USD", "CNY"),   # 大汇率
    ("CNY", "JPY"),   # 跨币种，得自己算
    ("USD", "JPY"),
    ("JPY", "USD"),   # 反过来 —— 小于 1
    ("VND", "USD"),   # 极小汇率 —— 1 VND ≈ 0.00004 USD，固定 4 位小数会全变 0
    ("USD", "VND"),   # ⚠️ 极大汇率
    ("美元", "人民币"),  # 中文名（说明书已经改成"填代码"了，这里应该被拒）
    ("ABC", "USD"),   # 瞎编的代码
]
for a, b in cases:
    print(f"  {a:6s} → {b:6s} : {tools.get_exchange_rate(a, b)}")

print()
print("=" * 56)
print("④ 本地工具（会改硬盘上那个账本）")
print("=" * 56)
# ⚠️ 这里绝不能直接 unlink 真的账本 —— 那是用户的真数据，跑一次自检就冲没了。
#    正确做法：先【备份】，测完【原样还回去】。只保证这一轮测试环境干净。
备份 = None
if tools.待办账本.exists():
    备份 = tools.待办账本.read_text(encoding="utf-8")
    tools.待办账本.unlink()
    print("  （真账本已暂存，测完原样还回去）")
print("  加两条：")
print("   ", tools.add_todo("买菜", "2026-09-23"))
print("   ", tools.add_todo("取快递", "2026-09-23"))
print("  加一条别的日期（当干扰项，看下面会不会串台）：")
print("   ", tools.add_todo("开会", "2026-09-25"))
print()
print("  查 2026-09-23：")
print(tools.get_calendar("2026-09-23"))
print()
print("  查 2026-09-25：")
print(tools.get_calendar("2026-09-25"))
print()
print("  查一个没安排的日子 2026-10-01：")
print(tools.get_calendar("2026-10-01"))
# ── 还原真账本（测试数据别留在用户硬盘上）──────
if 备份 is None:
    tools.待办账本.unlink(missing_ok=True)      # 本来就没账本 → 把测试留下的那份删掉
else:
    tools.待办账本.write_text(备份, encoding="utf-8")
    print("\n  （原账本已原样还原）")

print()
print("=" * 56)
print("⑤ 知识库检索（跨进程 HTTP → rag-knowledge-base）")
print("=" * 56)
print("  ⚠️ 这一段要对面服务在跑：")
print("     cd /d D:\\toutiao\\rag-knowledge-base")
print("     .venv\\Scripts\\python.exe -m uvicorn rag_api:app --port 8000")
print("  没起的话，这里会打印「查询 … 失败：URLError…」—— 那是【设计好的失败路径】，不是脚本坏了。")
print(" ", tools.search_docs("年假有几天"))

print()
print("=" * 56)
print("⑥ 说明书体检 —— 拿真实 API 打一发，看它收不收这张表")
print("=" * 56)
# 上一步的教训：Python 语法过了 ≠ 说明书合格。
# 结构不对的话，模型那边直接 400 拒绝，你到跑循环时才发现就晚了。
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
_client = OpenAI(api_key=os.getenv("API_KEY"), base_url="https://api.deepseek.com")

for _t in tools.TOOLS:
    _名字 = _t["function"]["name"]
    try:
        _client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_t],
        )
        print(f"  {_名字:20s} API 接受 ✅")
    except Exception as _e:
        print(f"  {_名字:20s} API 拒绝 ❌  {str(_e)[:160]}")

