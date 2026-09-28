"""第 0 步：亲眼看见 tool_calls

唯一目的：让 DeepSeek 输出一次 tool_calls，原样打印出来。
⚠️ 这一步【不执行】任何工具 —— 我们只看它「说了什么」。

跑法：.venv/Scripts/python.exe step0_see_tool_calls.py
（中文乱码的话，前面先敲一句  chcp 65001）
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 控制台防乱码

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# === 客户端（跟 RAG 项目同一个套路，key 走 .env）===
client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
)

# ══════════════════════ 菜单：只有一道菜 ══════════════════════
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气。涉及天气的问题必须调用此工具，不得凭记忆回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市中文名，例如：成都、北京",
                    }
                },
                "required": ["city"],
            },
        },
    }
]

# ══════════════════════ 问它一句 ══════════════════════
messages = [{"role": "user", "content": "成都明天天气怎么样？"}]

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=TOOLS,
)

msg = resp.choices[0].message
#        ↑ 路径跟你 RAG 里写的 resp.choices[0].message.content 一模一样，
#          只是这次我们不只取 .content，还要取它的兄弟 .tool_calls

# ─────────────────────────────────────────────────────────
# ⓪ 它到底有没有「点菜」？（先看这个，防止下面崩）
# ─────────────────────────────────────────────────────────
print("─── ⓪ 有 tool_calls 吗？ ───")
print("是 None 吗？   ", msg.tool_calls is None)
print("有几个 tool_call？", len(msg.tool_calls) if msg.tool_calls else 0)
print()

# ─────────────────────────────────────────────────────────
# ① 它「说话」了吗？（它在点菜的时候，这里通常是 None）
# ─────────────────────────────────────────────────────────
print("─── ① content（它说的人话）───")
print(repr(msg.content))
print()

# ─────────────────────────────────────────────────────────
# ②③ 它点了什么菜？
#    msg.tool_calls 是个【列表】，先取 [0]
#    每个元素里有 4 个字段：id / type / function.name / function.arguments
# ─────────────────────────────────────────────────────────
tc = msg.tool_calls[0]

print("─── ② 原始对象（先看个全貌）───")
print(tc)
print()

print("id        =", tc.id)
print("name      =", tc.function.name)          # 工具名在 function.name 下
print("arguments =", tc.function.arguments)     # 参数在 function.arguments 下
print()
# ⚠️ 是 str 不是 dict —— 所以循环里那句 参数 = json.loads(...) 是必须的
print("arguments 的类型 =", type(tc.function.arguments))
