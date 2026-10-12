"""第 4 课例题：会话记忆 —— 把账本存进抽屉，下次翻开接着记。

要解决的问题：
    现在的 step5_mcp.py 一退出（Ctrl+C、崩了、关机），这次聊的全没了。
    第 2 课已经看见：账本在你手上。那它凭什么不能存下来？

这个例题给【最小完整形状】：
    一个 session_id → 一个文件 sessions/<session_id>.json
    存：把 messages 原样写进去
    读：原样读回来，直接接着用

⚠️ 本例题【不调模型】（纯本地，随便跑多少遍）。它演的是"存/读"这个动作本身。
   接进循环是【你的作业】——见 md 第 6 课。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _demo_session_file.py
    .venv\\Scripts\\python.exe _demo_session_file.py 001     ← 指定会话 id，接着上次的

看什么：
    ① sessions/ 里的文件长什么样（json，缩进过的，能直接肉眼看）
    ② 第二次跑带上同一个 id —— 它会说"账本里已经有 N 条了"，而不是从零开始
    ③ 每次 [存] 都发生在【一轮结束之后】—— 想想：换成"退出时才存"会丢什么
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 抽屉：跟脚本同一个目录下的 sessions/
档案柜 = Path(__file__).resolve().parent / "sessions"
档案柜.mkdir(exist_ok=True)


def 存档(session_id: str, messages: list) -> Path:
    """把整本账写进 sessions/<session_id>.json。

    三个细节都不是随便写的：
      ensure_ascii=False —— 不写的话中文存成 \\u674e\\u56db 这种，肉眼看不了
      indent=2           —— 换行+缩进。存下来是【给人看】的，不是给机器看的
      encoding="utf-8"   —— 不写，Windows 上中文直接乱码（你踩过这个）
    """
    落点 = 档案柜 / f"{session_id}.json"
    落点.write_text(
        json.dumps(messages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 落点


def 读档(session_id: str) -> list:
    """把账本读回来。没有这个会话就【从零开始】—— 不是报错。

    ⭐ 这是"新用户"和"老用户"的同一个入口：读得到就接着聊，读不到就当第一次。
       所以调用方不用写 if os.path.exists(...) —— 判断藏在函数里。
    """
    落点 = 档案柜 / f"{session_id}.json"
    if not 落点.exists():
        return []
    return json.loads(落点.read_text(encoding="utf-8"))


def 看看抽屉():
    print(f"   档案柜 = {档案柜}")
    文件们 = sorted(档案柜.glob("*.json"))
    if not 文件们:
        print("   （空的）")
        return
    for f in 文件们:
        print(f"   {f.name:20s} {f.stat().st_size:>6} 字节")


session_id = sys.argv[1] if len(sys.argv) > 1 else "demo"

print("=" * 72)
print(f"会话记忆例题 —— session_id = {session_id!r}")
print("=" * 72)
print("\n[开聊前] 抽屉里现有的：")
看看抽屉()

# ── 开场：读档。读不到就是空账本 —— 同一个入口，两个分支都通
messages = 读档(session_id)
if messages:
    print(f"\n[读档] 找回 {len(messages)} 条消息，接着上次聊")
else:
    print("\n[读档] 没有这个会话 → 空账本，当第一次聊")
    messages.append({"role": "system", "content": "你是一个说话很短的助手。"})

# ── 假装聊了两轮（不调模型，手搓消息，专看"存"的形状）
假装的两轮 = [
    ("我想学 Agent 的记忆怎么设计", "先搞清三层：工作 / 会话 / 长期。"),
    ("工作记忆是哪个？", "就是你手里这本 messages。"),
]

for 我, 它 in 假装的两轮:
    messages.append({"role": "user", "content": 我})
    messages.append({"role": "assistant", "content": 它})
    落点 = 存档(session_id, messages)
    print(f"\n[存] 一轮结束就存 → {落点.name}，现在 {len(messages)} 条，"
          f"{落点.stat().st_size} 字节")

print("\n[盘上实际长这样] —— 直接 open 那个文件看：")
print("─" * 72)
print((档案柜 / f"{session_id}.json").read_text(encoding="utf-8")[:600])
print("─" * 72)

print("""
⭐ 三个要想清楚的问题（作业里要答）：

   ① 【什么时候存】？
      例题写的是"每轮结束存一次"。换成"整个对话退出时才存" —— 崩了丢什么？
      换成"每 append 一条就存" —— 安全，但代价是什么？
      （想想 agent-lab/todos.json 被跑脏那次：写盘是有后果的动作）

   ② 【存原始的还是存压缩的】？
      现在存的是原样 messages。聊了 200 轮之后，这个文件多大？
      下次读回来直接塞进 messages —— 第 2 课那个账本膨胀问题会不会【原封不动】地回来？

   ③ 【读回来的东西，该不该整本塞进 messages】？
      如果会，那第 1 层的"裁剪/压缩"就必须在【读档之后】也生效一次。
      —— 这就是三层【不是三个独立功能，是一条流水线上的三个站】。
""")
