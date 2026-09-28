"""第 3 步 B：把工具柜接上循环 —— Agent 会自己挑工具了

第 2 步的循环里只有 1 个工具，还跟循环挤在同一个文件。
第 3 步把工具全搬进 tools.py 的工具柜（5 个），这里只留循环。

关键点：循环本身【一行没改】—— 只把 TOOLS / TOOL_MAP 的来源
从"本文件里写死的定义"换成"import tools 取过来"。
骨架解耦就是这样验的：换入口不换骨架，1 个工具扩到 5 个照样转。

跑法：D:/toutiao/agent-lab/.venv/Scripts/python.exe D:/toutiao/agent-lab/step3_agent.py
"""
import json
import os
import sys
import tools

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
)



# ══════════════════════ 开场 ══════════════════════
# 四句话把 5 个工具各问一遍 —— 看循环转不转得起来、工具是不是都能被点到
messages = [{"role": "user", "content": "成都和北京明天天气怎么样？"},
            {"role": "user", "content": "顺便帮我查下美元换人民币的汇率"},
            {"role": "user", "content": "帮我把'买菜'记到 2026-09-23，然后看看那天有什么安排"},
            {"role": "user", "content": "年假有几天？"}
            ]

轮次 = 0

# ══════════════════════════════════════════════════════════
# 第 1 步你手动写的四拍，现在转起来
# ══════════════════════════════════════════════════════════
while True:
    轮次 += 1
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
    for tc in msg.tool_calls:       # 它可能一次点几道菜，for 挨个做
        print(f"  🔧 调用工具 {tc.function.name}  参数={tc.function.arguments}")

        参数 = json.loads(tc.function.arguments)      # arguments 是字符串，得拆成 dict

        # 查电话簿找到函数；**参数 把字典拆成关键字参数
        函数 = tools.TOOL_MAP[tc.function.name]       # key = 模型念的名字（字符串）

        结果 = 函数(**参数)

        print(f"     ↳ 返回：{结果}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": 结果,
        })

        # ⚠️ 模型要是「瞎编」一个菜单上没有的工具名，TOOL_MAP[...] 会 KeyError。
        #    现在先不管它 —— 第 4 步专门治这个。
