"""第 1 步：手写一次「死」的调用

不写循环。手动走完一轮：
   ① 调模型 → 它点菜
   ② 你的代码真去查
   ③ 把前情提要拼回去
   ④ 再调一次模型 → 它说答案

跑法：D:/toutiao/agent-lab/.venv/Scripts/python.exe D:/toutiao/agent-lab/step1_manual_call.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
)

# ══════════════════════ 菜单（跟第 0 步一模一样） ══════════════════════
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


# ══════════════════════ 工具本体 ══════════════════════
# ⚠️ 第 1 步先【写死】。
#    理由：这一轮要验证的是「消息管道」通不通，而管道通不通跟网络毫无关系。
#    一次只动一个变量 → 第 3 步再把这个函数体换成真的去调 wttr.in。
def get_weather(city: str) -> str:
    return "小雨，18℃，东南风 2 级"


# ══════════════════════ 开场 ══════════════════════
messages = [{"role": "user", "content": "成都明天天气怎么样？"}]

# ─────────────────────────────────────────────────────────
# ① 第一次调模型 —— 它在点菜
# ─────────────────────────────────────────────────────────
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=TOOLS,
)
msg = resp.choices[0].message
tc = msg.tool_calls[0]

print("【① 第一次调模型】它说：我要调", tc.function.name)
print()

# ─────────────────────────────────────────────────────────
# ② 你的代码真去查！
# ─────────────────────────────────────────────────────────
#   tc.function.arguments 是【字符串】，不能直接 ["city"]，得先转成字典
参数 = json.loads(tc.function.arguments)

print("【② 我的代码动手】去查", 参数["city"], "……")
天气结果 = get_weather(参数["city"])      # ← 这就是「顾客没进厨房」的那一下
print("     查到了：", 天气结果)
print()

# ─────────────────────────────────────────────────────────
# ③ 把「前情提要」拼回去
# ─────────────────────────────────────────────────────────
messages.append(msg)          # ← 它点菜那一句，原样记下来（注意：混着放对象也行）
messages.append({
    "role": "tool",           # ← 身份是 tool，不是 user、不是 assistant
    "tool_call_id": tc.id,    # ← 外卖单号：靠它把「回话」和「点菜」对上
    "content": 天气结果,       # ← 查到的结果，转成字符串放进来
})

print("【③ 前情提要】现在 messages 有", len(messages), "条：")
for i, m in enumerate(messages):
    role = m["role"] if isinstance(m, dict) else m.role
    print(f"     {i}. role = {role}")
print()

# ─────────────────────────────────────────────────────────
# ④ 再调一次模型 —— 这回它该说话了
# ─────────────────────────────────────────────────────────
resp2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=TOOLS,
)
msg2 = resp2.choices[0].message

print("【④ 第二次调模型】它终于说话了：")
print()
print(msg2.content)
