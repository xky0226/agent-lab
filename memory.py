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

# 被裁掉的那截，用这一句顶上。提到模块级只为两件事：
#   ① 测试和 step6 能引用同一个字符串 —— 谁也不许手抄一份（抄了就迟早分叉）
#   ② 它是【常量】：每轮都一样，才可能在服务端缓存里占到便宜（见下面压一压的注释）
省略提示 = "（更早的对话已省略）"


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
    # 空账本 / 只剩一条（就是 system）：没什么可压的，但【必须返回新列表】
    # —— 调用方拿到的永远是"可以随便改"的一份，不必回头怀疑原件。
    if len(messages) <= 1:
        return list(messages)

    保留 = max(1, 保留)   # 保留 <= 0 会让下面的数数永远数不满，等于静默不压。夹住它。

    # ── 找切点：从后往前数，数到第 保留 个 user，它就是"尾"的第一条 ──
    #
    # ⚠️ 为什么数的是 "user" 而不是别的：
    #   一轮的【开头】永远是 user。assistant / tool 都是这一轮的后续。
    #   按 user 切 → 尾巴必然从"一句话的开头"起，不可能切出半截回合。
    #
    # ⚠️ 为什么不数 assistant（看起来更自然："一问一答"数答的那半）：
    #   因为 assistant 条数【不等于】轮数 —— 调用工具的轮次里，
    #   一次对话会产生 assistant(带tool_calls) + 若干条 tool，
    #   甚至连续两条 assistant。以它当尺子，数出来的"轮"是错的。
    #
    # ⚠️ 为什么不干脆按"条"数（留最后 N 条）：
    #   一刀切在 assistant 和它的 tool 消息之间 → 那批 tool_call_id 落单 →
    #   服务端直接 400。这是本节唯一一个"错了就跑不起来"的坑。
    #   按 user 切，天然把 assistant + 它的 tool 结果【整窝】圈在同一侧。
    #
    # ⚠️ 循环 range(len-1, 0, -1) 从 1 停：messages[0] 是 system，
    #   它不是 user 也不该被数进去 —— 头是另外焊死的。
    数到 = 0
    切点 = None
    for i in range(len(messages) - 1, 0, -1):
        if messages[i].get("role") == "user":
            数到 += 1
            if 数到 == 保留:
                切点 = i
                break

    # 数不满 保留 轮 = 这本账还很年轻，用不着压。
    # ⚠️ 这时【不插省略提示】：一句谎话（"更早的对话已省略"）比不省更坏，
    #    模型会以为自己漏看了什么，然后开始瞎猜/道歉。
    #
    # ⚠️ 切点 <= 1 也要走这条路 —— 这是【双跑验尺子当场抓出来的 bug】：
    #    账本是 [system, u1, a1, u2]，保留 2 轮时，第二个 user 恰好就是 u1，
    #    切点 = 1 → 尾巴 messages[1:] 就是全部 → 【一条都没删】。
    #    可省略提示照样插了进去 → 账本反而变大。
    #    实测：那一轮打印 "压掉约 -7 token"（负的）。
    #    ⭐ 教训：**"压"这个动作必须先确认"确实删掉了东西"，再宣布自己省了。**
    #       不然你循环里的返回值是对的（消息没丢），但你以为省了 —— 而打印的
    #       那个负数就是全部线索，不打印就永远不知道。
    if 切点 is None or 切点 <= 1:
        return list(messages)

    # ── 拼：头（system） + 省略提示 + 尾 ──
    #
    # 提示条的 role 用 "system" 而不是 "user"：
    #   它不是"用户说的话"，是"关于这次对话的状态说明"，跟人设/规则同级。
    #   项目里已有先例 —— step5_mcp.py 轮次用尽时也是往中间 append 一条 system。
    #   ⚠️ 但要知道这条【可移植性有边界】：少数严格的服务端只认首条 system。
    #      真撞上就把它改成 "user"，语义稍有出入，功能一样。
    #
    # ⚠️ 这里【看不见】的一笔账：省略提示每轮都在变（"省了 3 轮"/"省了 4 轮"
    #    若写进正文就会变），而它贴在 system 正后方 ——
    #    服务端的 prompt 缓存是【按前缀逐字节比对】的，正文一变，
    #    从这条往后全部重算。写成【固定常量】是刻意的：只赔一次，不每轮赔。
    return [messages[0], {"role": "system", "content": 省略提示}] + list(messages[切点:])


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
    # ① 目录可能还不存在。parents=True：sessions/ 的上一层也帮我建；
    #    exist_ok=True：已经在了别报错（这个函数会被反复调用，不是只跑一次）
    档案柜.mkdir(parents=True, exist_ok=True)

    落点 = 档案柜 / f"{session_id}.json"

    # ② ensure_ascii=False —— 不加的话中文全变成 李 这种转义，
    #    文件能用（json.loads 解得回来），但你【打不开、读不了】。
    #    indent=2 —— 一屏一屏能看。会话存档是拿来"翻"的，不是拿来省字节的。
    #    encoding="utf-8" —— 不写就用平台默认（Windows 上是 GBK），
    #    中文进去就乱码或直接抛 UnicodeEncodeError。
    #
    # ⚠️ 这个函数【故意不做兜底】：如果调用方传来的是 openai SDK 的对象
    #    （resp.choices[0].message）而不是 dict，这里会当场 TypeError:
    #    "Object of type ChatCompletionMessage is not JSON serializable"。
    #    这是好事 —— 报得又响又准。真正的正解不在这里，在【记账那一端】：
    #    step6_memory.py 里 append 进去的就该是 msg.model_dump(exclude_none=True)，
    #    让 messages 从头到尾都是"纯字典"。
    #    教训：**存不进去，根因往往不在"存"这一端，在账本里混进了非字典对象。**
    落点.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")

    # ③ 返回落点而不是 None：调用方多半想打印一行"存到哪了"。
    #    库里少写一行 return，每个调用点就多写一遍路径拼接 —— 迟早拼得不一样。
    return 落点


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
    落点 = 档案柜 / f"{session_id}.json"

    # ① 没有这个会话 —— 这【不是错】，是"新用户"最正常的第一次。
    #    所以不 raise、不打日志、不吭声，就返回空账本。
    #    ⭐ 这一句是整个模块最值钱的设计：**新用户和老用户共用同一个入口**。
    #       要是这里 raise，每个调用点都得写 try 或者先 if 文件在不在 ——
    #       一处忘了写就是崩溃。把"没有"当成"空"，边界就只在库里这一处。
    if not 落点.is_file():
        return []

    # ② 文件在 = 之前真有用户聊过，这里坏了就是真坏了 —— 必须留痕。
    #
    #    ⚠️ 但留痕的方式是【分叉的】：函数对机器安静，对人大声。
    #        - 返回值：还是 []。调用方的契约永远只有一种，不用分叉。
    #        - 告警：打到 stderr。人（你、运维、日志系统）看得见。
    #       两件事本来就不是一件事：
    #           返回 []      是给【代码】看的 —— "往后没有历史可用"
    #           报"账本坏了"  是给【人】看的   —— "有东西被吃了，来查"
    #       只返回 [] 不吭声 = 用户的聊天记录【静默消失】，最难查的那种 bug；
    #       直接 raise     = 一个坏文件把整个服务打死，也不对。
    #
    #    ⚠️ 为什么 to stderr 而不是 print 到 stdout：
    #       正常流程的输出走 stdout（机器/管道读它），异常走 stderr。
    #       混在一起，重定向输出时报警就被当成正文了。
    try:
        数据 = json.loads(落点.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"⚠️ 会话账本读不动（{落点.name}）：{type(e).__name__}: {e}", file=sys.stderr)
        return []

    # ③ JSON 合法但形状不对（比如有人手写成了 {"messages": [...]}，或者存了个对象）。
    #    契约是"一定给你 list"，所以这里也得把它掰回 list —— 让下游少一层 if。
    if not isinstance(数据, list):
        print(f"⚠️ 会话账本形状不对（{落点.name}）：期望 list，实际 {type(数据).__name__}", file=sys.stderr)
        return []

    return 数据


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
    # ⭐ 这个函数之所以只有十几行，全靠 ★4 立下的那条规矩：
    #    【"没有" = 空，不是错】。同一个规矩换张表就能复用 —— 这就是先写 ★4 的意义。
    if not 档案卡.is_file():
        return {"事实": []}

    try:
        档案 = json.loads(档案卡.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"⚠️ 档案卡读不动（{档案卡.name}）：{type(e).__name__}: {e}", file=sys.stderr)
        return {"事实": []}

    # ⚠️ 默认值的形状必须【处处一致】，否则空壳会伪装成"有内容"：
    #    默认是 {"事实": []}，那校验也得盯着这两点 —— 是 dict、且有"事实"、且它是 list。
    #    漏了这层，"档案.get('事实')" 拿到个字符串，拼系统提示时就会被
    #    【逐字符】拆成一行一个字（字符串可迭代），拼出一坨谁也没预料到的人设。
    if not isinstance(档案, dict) or not isinstance(档案.get("事实"), list):
        print(f"⚠️ 档案卡形状不对（{档案卡.name}）：期望 {{'事实': [...]}}", file=sys.stderr)
        return {"事实": []}

    return 档案


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
    # ⚠️ 空白先剃掉再谈去重。模型很可能吐 " 他在学 Agent" / "他在学 Agent "，
    #    字面不同、意思一样，不剃就是两条 —— 档案卡会被这种"看不见的差异"灌满。
    事实 = 事实.strip()
    if not 事实:
        return 读档案()   # 空事实不入档。返回现档案，调用方拿到的形状始终一致。

    # ① 读：拿到现在这本账
    档案 = 读档案()
    # setdefault 比 档案.get("事实") or [] 好在哪：它【顺手把键补上】。
    # 万一文件里是 {}（手工改坏过），这里就地修好，下面写回去就是完整的形状。
    事实们 = 档案.setdefault("事实", [])

    # ② 改：去重后再加
    #    ⚠️ 去重是【必需】不是优化：三楼这层每轮都会跟着 system 重发一次，
    #       重复事实不是"多占一点磁盘"，是【每一轮都多花一次 token】。
    #       而且重复的"人设"会让模型把那句话的权重无端抬高。
    if 事实 not in 事实们:
        事实们.append(事实)
        # ③ 写：只在真的变了才写盘。
        #    ⚠️ 重复时【跳过 write_text】，不是"写一样的内容也没事"——
        #       每次都写会刷新 mtime；列会话() 是按 mtime 倒序排的，
        #       而任何"按改动时间排序"的展示，最怕的就是无意义的空写。
        档案卡.write_text(json.dumps(档案, ensure_ascii=False, indent=2), encoding="utf-8")

    # ⭐ 这里有个必须想清楚的对照：
    #    mcp_server.py 的 write_note 是【只增不改】—— 文件已存在就拒绝。
    #    这里却必须【覆盖】。同一个 write_text，两种相反的语义，区别在哪？
    #        答：**"这是谁的文件"。**
    #        write_note 面对的是【别人的文档】，它不知道人家原来写了什么，
    #        覆盖 = 毁掉用户的东西 → 只能拒绝。
    #        记一笔 面对的是【自己维护的账本】，全量内容就在手上（刚读回来的），
    #        写回去 = 完整地更新它 → 覆盖才是对的，拒绝反而成了写不进去的 bug。
    #    → 所以"该不该覆盖"从来不是 write_text 的性质，是【你对这份数据有没有完整的所有权】。
    #
    # ⚠️ 诚实的设计缺陷（已知、不改，留着面试讲）：
    #    "读 → 改 → 写"不是原子的。两个进程同时进来，A 读到旧档案、B 也读到旧档案，
    #    A 写回、B 写回 → A 那条事实【凭空消失】（丢更新，lost update）。
    #    现在只有一个进程、一轮一轮来，安全。真要多进程：加文件锁，或换成 SQLite。
    return 档案


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
