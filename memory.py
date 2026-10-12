"""三层记忆的【零件库】—— 只装函数，不装 while 循环。

跟 tools.py 是同一个分工道理：

    memory.py        零件：会话存/读、压缩、档案卡
    step6_memory.py  拿着零件，接进 while 循环

为什么零件库【不碰网络】：
    这里的函数全是"存取本地东西"，一个 API 调用都没有。
    摘要（要调模型）故意留在 step6 —— 零件库依赖网络，就没法单独测了。
    ⚠️ 这条判断在面试里能讲：**哪些模块该是纯的，哪些才配连外面**。

三层对照（详见《Agent 三层记忆 — 从零入门课.md》）：

    第一层 工作记忆 = messages           —— 只增不减，会爆。治法：压一压
    第二层 会话记忆 = sessions/<id>.json —— 关掉进程还能接着聊
    第三层 长期记忆 = profile.json       —— 跨会话记住"你是谁"

跑法（自检，等你填完）：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe memory.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 两个落点。跟脚本同一个目录，理由：这个项目就是这么朴素的（看 tools.py）
档案柜 = Path(__file__).resolve().parent / "sessions"
档案卡 = Path(__file__).resolve().parent / "profile.json"

# 工作记忆的闸门：最近多少【轮】原样留着，更早的交给"压"
保留最近几轮 = 6


# ══════════════════════════════════════════════════════════════
# 第一层：工作记忆 —— 量 + 压
# ══════════════════════════════════════════════════════════════
def 量一量(messages: list) -> dict:
    """粗估这本账有多大。

    ⚠️ 这是【估】，不是【真值】。真值只有一个来源：模型回给你的
       resp.usage.prompt_tokens。估的用处是"发之前先看一眼要不要压"，
       真的用处是"发完之后记账、画曲线"。两把尺子别混。

    0.7 这个数是实测出来的：200 个中文字 → 123 token（≈0.62）；
    20 个中文字 → 15 token（≈0.75）。取 0.7 当中间值够用。
    """
    字符数 = sum(
        len(m.get("content"))
        for m in messages
        if isinstance(m.get("content"), str)
    )
    return {"条数": len(messages), "字符数": 字符数, "粗估token": int(字符数 * 0.7)}


def 压一压(messages: list, 保留: int = 保留最近几轮) -> list:
    """第一层的核心动作：把老对话压缩掉，只留最近几轮原样。

    ★1 你来写。要求：

      ① 【system 必须原样留下】—— 它是"钉住不能丢"的东西（人设、日期、规则），
         被裁掉的话整个 Agent 的性格当场变。它是 messages[0]。
      ② 【按"轮"裁，不按"条"裁】—— 一轮 = 一问一答（可能还带工具结果）。
         按条裁会把 user 和它对应的 assistant 拆开，模型看到半个回合会懵。
         ⚠️ 这里有个真坑：tool_calls 的那些条（role="tool"）也算在一轮里，
            OpenAI 要求 tool_call_id 必须配平，**裁掉一半服务端会 400**。
            最稳的裁法：从后往前数"user 出现几次"，数够 保留 就切。
      ③ 被裁掉的部分【不直接扔】—— 返回的时候顺手拼成一句"（更早的对话已省略）"
         放在 system 后面，或者（★2 进阶）交给摘要函数压成一段话。
      ④ 返回【新列表】，别原地改传进来的那个（原地改会让调用方莫名其妙丢消息）。

    形状提示（不给答案，给形状）：
        头 = messages[:1]                  # system
        尾 = ...                           # 从后往前数够 保留 轮
        中间 = ...                          # 被省略的那截
        return 头 + [省略提示] + 尾
    """
    raise NotImplementedError("★1 你来填：压一压")


# ══════════════════════════════════════════════════════════════
# 第二层：会话记忆 —— 存 + 读
# ══════════════════════════════════════════════════════════════
def 存会话(session_id: str, messages: list) -> Path:
    """把整本账写进 sessions/<session_id>.json。

    ★3 你来写。要求：

      ① 目录可能不存在 → 先 mkdir（parents=True, exist_ok=True）
      ② 三个必须写全的参数，一个都别省：
           json.dumps(..., ensure_ascii=False, indent=2)
           write_text(..., encoding="utf-8")
         （不写 ensure_ascii 中文变 \\u674e；不写 encoding Windows 上乱码 —— 你都踩过）
      ③ 返回落点 Path，方便调用方打印

    ⭐ 真正要想的不是这三行，是【什么时候调它】—— 见 md 第 6 课的问题①。
    """
    raise NotImplementedError("★3 你来填：存会话")


def 读会话(session_id: str) -> list:
    """把账本读回来。没这个会话就返回 []。

    ★4 你来写。要求：

      ① 【读不到不是错】—— return []，不要 raise。
         这样"新用户"和"老用户"共用同一个入口，调用方不用写 if 判断。
      ② 文件存在但内容是坏的 JSON 怎么办？想想 10-09 那条：
         "坏 JSON 这条线"——那时候你在 json.loads 外面包了 try。
         这里要不要包？包了之后返回什么？（提示：返回 [] 和返回"账本坏了"
         是两件事 —— 你更想让用户看到哪个？）

    ⚠️ 进阶（写注释里就行，不用实现）：文件很大时，一次性 json.loads 会卡。
       真上生产要考虑流式/分片 —— 但你现在的量级，不用。
    """
    raise NotImplementedError("★4 你来填：读会话")


def 列会话() -> list:
    """列出档案柜里所有会话（按改动时间倒序）—— 已经给你了，直接调。"""
    if not 档案柜.exists():
        return []
    return sorted(档案柜.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


# ══════════════════════════════════════════════════════════════
# 第三层：长期记忆 —— 档案卡
#
# 跟第二层【最关键的区别】：
#     会话记忆 = 流水账。按时间存，全量加载。回答"我们聊过什么"。
#     长期记忆 = 档案卡。不记流水，只记"这个人是怎样的"。回答"你是谁"。
#
# 所以它不是"另一份 messages"，是【另一张表】：
#     profile.json = {"事实": ["他在学 Agent", "他做 RAG 项目", ...]}
# ══════════════════════════════════════════════════════════════
def 读档案() -> dict:
    """读档案卡。没有就返回空壳 {"事实": []}。

    ★5 你来写。跟 读会话 几乎一样 —— 只换了文件名和默认值。
    （所以先写 ★4，★5 是顺手。）
    """
    raise NotImplementedError("★5 你来填：读档案")


def 记一笔(事实: str) -> dict:
    """往档案卡里追加一条事实（去重）。

    ★6 你来写。要求：

      ① 【读-改-写】三步：读现有 → 加一条 → 写回去。
         ⚠️ 别写成覆盖（write_text 会把原来的一起抹掉）。
         ⭐ 但想一想：这跟 write_note 那把"只增不改"的锁是不是冲突？
            write_note 拒的是【覆盖别人的文件】；这里是【更新自己的账本】，
            必须覆盖。同一个 write_text，两种语义 —— 区别在"谁的文件"。
      ② 去重：已经有的别再加一遍（模型很可能反复说同一件事）
      ③ 返回更新后的档案（方便调用方直接打印/拼提示）

    ⚠️ 一个诚实的设计缺陷（写进注释）：JSON 文件"读-改-写"在并发下会丢更新。
       你这里只有一个进程、一轮一轮来，没事。真多进程要上锁或换 SQLite —— 知道就行。
    """
    raise NotImplementedError("★6 你来填：记一笔")


def 拼系统提示(档案: dict, 基础提示: str) -> str:
    """把档案卡拼进 system prompt —— 已经给你了。

    这是长期记忆【唯一发挥作用的地方】：
    它不塞进 messages 中间，而是【贴在 system 里】，每轮都跟着走。
    ⚠️ 所以档案不能无限长 —— 它每轮都要重发。
       长到几百条的时候，你就得从"全量贴"改成"按相关性检索"了 —
       那才是需要向量库的时刻（见 md 第 5 课）。
    """
    事实们 = 档案.get("事实") or []
    if not 事实们:
        return 基础提示
    清单 = "\n".join(f"- {f}" for f in 事实们)
    return f"{基础提示}\n\n【关于这位用户的已知信息】\n{清单}"


# ══════════════════════════════════════════════════════════════
# 自检：你填完之后，直接跑这个文件
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    假账本 = [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "第一句话"},
        {"role": "assistant", "content": "第一句答"},
        {"role": "user", "content": "第二句话"},
        {"role": "assistant", "content": "第二句答"},
        {"role": "user", "content": "第三句话"},
        {"role": "assistant", "content": "第三句答"},
        {"role": "user", "content": "第四句话"},
        {"role": "assistant", "content": "第四句答"},
    ]

    print("=" * 66)
    print("memory.py 自检")
    print("=" * 66)

    print(f"\n量一量（9 条假账本）：{量一量(假账本)}")

    print("\n压一压（保留最近 2 轮）：")
    try:
        压过的 = 压一压(假账本, 保留=2)
        print(f"   {len(假账本)} 条 → {len(压过的)} 条")
        for m in 压过的:
            print(f"     {m['role']:10s} {m['content'][:30]}")
        print(f"   system 还在吗：{压过的[0]['role'] == 'system'}")
        最后两条 = [m['content'] for m in 压过的 if m['role'] == 'user'][-2:]
        print(f"   最近两轮的用户话还在吗：{最后两条 == ['第三句话', '第四句话']}")
    except NotImplementedError as e:
        print(f"   ⏭  {e}")

    print("\n存/读会话：")
    try:
        落点 = 存会话("_自检", 假账本)
        print(f"   [存] {落点.name}  {落点.stat().st_size} 字节")
        读回 = 读会话("_自检")
        print(f"   [读] 读回 {len(读回)} 条，跟原来一样吗：{读回 == 假账本}")
        print(f"   [读] 读一个不存在的会话：{读会话('_根本没这个')!r}")
        落点.unlink(missing_ok=True)
        print("   🧹 自检文件已删")
    except NotImplementedError as e:
        print(f"   ⏭  {e}")

    print("\n档案卡：")
    try:
        档案 = 读档案()
        print(f"   读档案（一开始）：{档案}")
        档案 = 记一笔("他在学 Agent 记忆怎么设计")
        档案 = 记一笔("他在学 Agent 记忆怎么设计")      # 故意重复，考去重
        档案 = 记一笔("他在做一个跑腿平台")
        print(f"   记了三笔（其中一笔重复）：{档案}")
        print(f"   拼进 system：\n{拼系统提示(档案, '你是一个助手。')}")
        档案卡.unlink(missing_ok=True)
        print("   🧹 档案卡已删")
    except NotImplementedError as e:
        print(f"   ⏭  {e}")

    print("\n" + "=" * 66)
