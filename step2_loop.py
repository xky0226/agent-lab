"""第 2 步：把「手动四拍」包进 while 循环

第 1 步你手动做了：调模型 → 查 → 拼回去 → 再调模型
第 2 步让这件事自己转起来 —— 这就是 AgentLoop 了。

跑法：D:/toutiao/agent-lab/.venv/Scripts/python.exe D:/toutiao/agent-lab/step2_loop.py
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
# 这次让它把【城市名念回来】—— 好让你看出「到底被调了几次、查的是哪个城市」
def get_weather(city: str) -> str:
    return f"{city}：小雨，18℃，东南风 2 级"


# ══════════════════════════════════════════════════════════
# ⭐ 新零件一：字典查表
#    模型给的 tc.function.name 是【字符串】"get_weather"，
#    你要调的是【函数】get_weather —— 中间得有个电话簿。
# ══════════════════════════════════════════════════════════
TOOL_MAP = {
    "get_weather": get_weather,
}


# ══════════════════════ 开场 ══════════════════════
# 故意问两个城市 —— 逼它调两次工具，看循环转不转得起来
messages = [{"role": "user", "content": "成都和北京明天天气怎么样？"}]

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
        tools=TOOLS,
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

        参数 = json.loads(tc.function.arguments)   # arguments 是字符串，得拆成 dict

        # 查电话簿找到函数；**参数 把字典拆成关键字参数
        函数 = TOOL_MAP[tc.function.name]         # key = 模型念的名字（字符串）
        结果 = 函数(**参数)

        print(f"     ↳ 返回：{结果}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": 结果,
        })

        # ⚠️ 模型要是「瞎编」一个菜单上没有的工具名，TOOL_MAP[...] 会 KeyError。
        #    现在先不管它 —— 第 4 步专门治这个。
