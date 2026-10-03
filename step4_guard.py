"""第 4 步：给循环装上四条防线 —— 模型乱来的时候不许崩

`step3_agent.py` 是【无防线基线】，这个文件是它的加固版。四条线：

    ① 坏 JSON    → `json.loads` 抛 JSONDecodeError   → try 接住
    ② 瞎编工具名  → `TOOL_MAP[...]` 抛 KeyError        → if 提前拦
    ③ 参数对不上  → `函数(**参数)` 抛 TypeError         → 内层 try 接住
    ④ 转不完      → 根本没有异常抛出                    → 轮次上限 + 收口

接住之后一律【用 tool 信封回话】，且必须**配平**：每个 tool_call_id 都要有回话。

跑法：D:/toutiao/agent-lab/.venv/Scripts/python.exe D:/toutiao/agent-lab/step4_guard.py
"""
import json
import os
import sys
import tools
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI

# ══════ 三个可调参数，全摆在这一处 —— 改值不用翻代码 ══════
注入坏JSON = False   # 测试开关：让 arguments 坏掉（模拟 ①）
注入坏参数 = False   # 测试开关：删掉一个必填参数（模拟 ③）
上限 = 8             # 轮次上限：测试用 1（逼出"半成品"）；上线值 8~10

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
)

today = date.today().isoformat()

# ══════════════════════ 开场 ══════════════════════
# 故意要一个【无条件的两步走】任务：先查天气 → 再记待办。
# 第 1 轮结束时它手上只有"天气"，"记带伞"这一步还没做 —— 这就是「半成品」状态，
# 也是 ④ 真正要考的：手上只有一半时，它认不认这笔账。
# （⚠️ 别写成"要是下雨就记" —— 那是条件式任务，不下雨就等于不用做，逼不出半成品）
messages = [
    {"role": "system", "content": f"今天是{today},记得说到日期的时候以今天/明天/后天,这样为准。无论用户用什么语言提问，始终用简体中文回答。"},  # ★ 把今天告诉它，并且说清"今天/明天"以这个为准
    {"role": "user", "content": "看看成都下周五天气，然后帮我记一条'带伞'"},
    ]
# ↑ 想测"全干完"就换回四句话；想测"一点没干"就把 上限 改成 0
#
# 📌 2026-10-03 测第 6 步（Agentic RAG）时，这里临时换过这几个问题，测完已还原：
#      "公司年假的申请流程是什么？"                             → 检索 1 次
#      "我想请 3 天年假，需要提前多久申请？另外这 3 天有工资吗？"  → 检索 2 次（但是并行，不是迭代）
#      "员工手册说年假申请要谁来批准？这个人还负责别的什么审批？"
#    还原的理由：上面那句"查天气→记待办"才是为 ④ 轮次上限【专门设计】的半成品场景。

轮次 = 0

# ══════════════════════════════════════════════════════════
# 第 1 步你手动写的四拍，现在转起来
# ══════════════════════════════════════════════════════════
while True:
    轮次 += 1

    if 轮次 > 上限:
        messages.append({"role": "system", "content": "轮次已用尽，请直接告诉用户目前查到了什么、还剩什么没查完"})
        resp = client.chat.completions.create(model="deepseek-chat", messages=messages)  # ← 注意：没带 tools
        end_result = resp.choices[0].message.content
        # 收口必须留痕 —— 不然日志里"被掐断"和"正常完成"长得一模一样
        print(f"\n⚠️ 轮次用尽（已转满 {上限} 轮）—— 下面是收口，不是正常完成")
        print(f"🏁 它说：{end_result}")
        break

    print(f"\n════════ 第 {轮次} 轮 ════════")

    # ── ① 调模型 ──────────────────────────────────────
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools.TOOLS,
    )
    msg = resp.choices[0].message
    messages.append(msg)          # 不管它说啥，先记下来（前情提要）

    # ── ② 出口：它不点菜了，就是在说话 ──────────────────
    if not msg.tool_calls:          # 宽条件：None 和 [] 都接得住（别写成 is None）
        print(f"\n🏁 它说：{msg.content}")
        break

    # ── ③ 它点菜了 —— 可能一次点好几个，一个个做 ──────────
    for tc in msg.tool_calls:
        if 注入坏JSON:
            tc.function.arguments = tc.function.arguments[:-1]
        # 它可能一次点几道菜，for 挨个做
        if tc.function.name not in tools.TOOL_MAP:
            行们 = []
            for c in tools.TOOL_MAP:
                行们.append(f"- {c}")
            正文 = "\n".join(行们)

            bad = {"role": "tool", "tool_call_id": tc.id, "content": f"{tc.function.name}不在tools.TOOL_MAP,请使用{正文}里的工具"}
            messages.append(bad)
        else:
            try:
                print(f"  🔧 调用工具 {tc.function.name}  参数={tc.function.arguments}")

                参数 = json.loads(tc.function.arguments)      # arguments 是字符串，得拆成 dict

                if 注入坏参数:
                    参数.pop("due_date", None)

                # 查电话簿找到函数；**参数 把字典拆成关键字参数
                函数 = tools.TOOL_MAP[tc.function.name]       # key = 模型念的名字（字符串）

                try:
                    结果 = 函数(**参数)


                    print(f"     ↳ 返回：{结果}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": 结果,
                    })
                except Exception as e:
                    print(f"     ↳ 调用 {tc.function.name} 失败：{type(e).__name__}: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"调用 {tc.function.name} 失败：{type(e).__name__}: {e}",
                    })


            except Exception as e:
                print(f"  🔧 调用工具 {tc.function.name}  参数={tc.function.arguments}无效")

                result = f"{tc.function.arguments}无效：{type(e).__name__}: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
