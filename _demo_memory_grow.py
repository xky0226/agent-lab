"""第 2 课实测：messages 是个【只增不减的账本】，而且每轮都要【整本重喂】。

为什么要跑这个：
    你大概会以为"模型记得我们刚才聊过什么"。它不记得 —— 模型是【无状态】的。
    所谓"记忆"，是你每轮把【全部历史】重新贴一遍给它看。

    这个脚本让你亲眼看见：prompt_tokens 一轮比一轮大，
    涨的是【整本账】——system + 全部 user + 全部 assistant，一个字都不少。

    第 1 轮发出去的是 50 个字，第 4 轮发出去的是 50 + 前面所有轮。
    ⭐ 这就是"会话一长 Prompt 就爆"的全部病因。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_memory_grow.py

看什么：
    ① 每轮的 prompt_tokens   —— 单调递增
    ② 每轮的"本轮新增"       —— 只有几十个字，可 prompt 涨了几十
    ③ 最后一行的倍数         —— 这就是账本膨胀的比例
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openai import OpenAI

# .env 里只有 API_KEY；不用 load_dotenv()（从 stdin 跑的时候它会报 AssertionError）
配置 = {}
for 行 in Path(".env").read_text(encoding="utf-8").splitlines():
    if "=" in 行 and not 行.strip().startswith("#"):
        名, _, 值 = 行.partition("=")
        配置[名.strip()] = 值.strip()

client = OpenAI(api_key=配置["API_KEY"], base_url="https://api.deepseek.com")

本轮要说的话 = [
    "用一句话介绍你自己",
    "刚才你说的是什么？",
    "把我们这两句对话，各用一个词总结",
    "现在一共聊了几轮？",
]

messages = [
    {"role": "system", "content": "你是一个说话很短的助手，每次回答不超过 20 个字。"}
]

print("=" * 72)
print("messages 膨胀实测 —— 每轮都把【整本账】重新发出去")
print("=" * 72)

记录 = []
for i, 话 in enumerate(本轮要说的话, 1):
    messages.append({"role": "user", "content": 话})

    新增字数 = len(话)
    整本字数 = sum(len(m["content"]) for m in messages)

    resp = client.chat.completions.create(model="deepseek-chat", messages=messages)
    回答 = resp.choices[0].message.content
    messages.append({"role": "assistant", "content": 回答})

    用了 = resp.usage.prompt_tokens
    记录.append((i, 新增字数, 整本字数, 用了))

    print(f"\n第 {i} 轮")
    print(f"   这一轮新增          : {新增字数} 个字")
    print(f"   整本账（要发出去）   : {整本字数} 个字，{len(messages)} 条消息")
    print(f"   ⭐ prompt_tokens    : {用了}")
    print(f"   它答               : {回答}")

print()
print("=" * 72)
print(f"{'轮':>3} {'本轮新增':>10} {'整本字数':>10} {'prompt_tokens':>15}")
for i, 新增, 整本, 用了 in 记录:
    print(f"{i:>3} {新增:>10} {整本:>10} {用了:>15}")

最初, 最后 = 记录[0][3], 记录[-1][3]
print()
print(f"第 1 轮 {最初} token → 第 {len(记录)} 轮 {最后} token"
      f"（涨了 {最后 / 最初:.1f} 倍，而这 4 轮你其实一共只说了 "
      f"{sum(r[1] for r in 记录)} 个字）")
print()
print("⭐ 结论：模型这边【没有任何东西在记】。账本在你手上，你每轮整本寄一遍。")
print("   → 所以第一层记忆要治的不是'模型忘了'，是【你这本账越来越厚，寄不动了】。")
