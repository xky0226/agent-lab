"""第 6 步：同一个循环、同一份工具 —— 多装了三层记忆。

对照物：step5_mcp.py —— 一个字没动，留着并排放。
同一个 while、同四条防线、同一套 MCP 接线，只有【循环外面】和【循环里两行】多了东西。

⚠️ 先看【哪些没动】，再看多了什么 —— 这是读这一步的正确顺序：
   四条防线（假工具名 / 坏 JSON / 坏参数 / is_error）、配平、收口、日志顺序
   —— 全部原样。记忆是【包在循环外面的壳】，不是塞进循环里的分支。
   真要是"加了功能就得改一堆循环体"，说明第 4~5 步的结构本来就没搭好。

新增的东西（对照《Agent 三层记忆 — 从零入门课.md》第 6 课）：

    位置              动作                      第一层/二层/三层
    ──────────────────────────────────────────────────────────────
    开聊前  ① 读档案   读档案()                 第三层
            ② 拼      拼系统提示(档案, 基础)     第三层【唯一生效处】
            ③ 读档    读会话(会话号)             第二层
            ④ 压      压一压(账本) → 要发的       第一层（读回来必须再压一次）
    每一轮  ⑤ 量      量一量 + usage.prompt_tokens  第一层（两把尺子）
            ⑥ 调      create(messages=要发的)
            ⑦ 存      存会话(会话号, 账本)        第二层

跑法：
    cd D:\\toutiao\\agent-lab

    # ① 先看【不压】，让账本自己长 —— 这是 ⑦，顺序不能跳
    .venv\\Scripts\\python.exe step6_memory.py 记忆演示 --问 "我叫李雷，在做 RAG 和 Agent 两个项目。" --问 "我主要用 Python。" --问 "给我三条建议。"

    # ② 再看【压】的那一遍 —— 这是 ⑧
    .venv\\Scripts\\python.exe step6_memory.py 记忆演示2 --compress --问 "..." --问 "..." --问 "..."

    # ③ 跨会话：这条事实落进 profile.json 之后，换个会话号新开一轮，system 里已经有了
    .venv\\Scripts\\python.exe step6_memory.py 记忆演示 --remember "用户叫李雷，主攻 Python"

    # ④ 老两条跑法跟 step5 完全一样（不传 --问 就用默认开场）
    .venv\\Scripts\\python.exe step6_memory.py 会话A
    .venv\\Scripts\\python.exe step6_memory.py 会话A t01_grade_boundary
"""

import asyncio
import contextlib
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ══════════════════════════════════════════════════════════════
# 【新增】把 step5 里那些零件借过来。一行 import，背后是人家写好的五个函数。
#
# ⚠️ 注意 memory.py 里【没有 openai 的 import】—— 它是纯零件库，一个 API 调用都没有。
#    所以上面这行 from openai import OpenAI 不会渗进它。这条边界是刻意的：
#    零件库一联网，就没法单独测了（见 md 6.3）。
# ══════════════════════════════════════════════════════════════
from memory import (
    保留最近几轮,
    压一压,
    存会话,
    拼系统提示,
    量一量,
    读会话,
    读档案,
    记一笔,
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
)

# ══════════════════════════════════════════════════════════════
# 命令行 —— 比 step5 多了三个开关，但【题号那条规矩一个字没改】：
#    题号仍然由【启动方】给，不让模型给。
#
# ⚠️ 为什么用手写的这几行、不引 argparse：
#    这个项目的卖点是"看得见每一块"，命令行解析也让它看得见。
#    真上生产当然用 argparse —— 但那是另一个权衡（功能 vs 可读）。
# ══════════════════════════════════════════════════════════════
参数 = sys.argv[1:]

开压 = "--compress" in 参数          # ⑧ 的开关。默认【关】：先看见膨胀，才谈得上"压有用"
while "--compress" in 参数:
    参数.remove("--compress")

# 保留最近几轮 = 6 是零件库里的默认值。--keep N 只是【为了做对照实验】能把它压小 ——
# ⚠️ 别为了"省 token"就把它调到 1：调小 = 忘得更多，这是效果和成本之间的取舍，
#    不是"数字越小越好"。默认值 6 是权衡过的。
保留轮数 = 保留最近几轮
while "--keep" in 参数:
    i = 参数.index("--keep")
    if i + 1 >= len(参数) or not 参数[i + 1].isdigit():
        print("--keep 后面要跟一个正整数，比如 --keep 2", file=sys.stderr)
        raise SystemExit(2)
    保留轮数 = int(参数[i + 1])
    del 参数[i:i + 2]

要记的事实们 = []                     # --remember 可重复
while "--remember" in 参数:
    i = 参数.index("--remember")
    if i + 1 >= len(参数):
        print("--remember 后面要跟一条事实，比如 --remember \"用户叫李雷\"", file=sys.stderr)
        raise SystemExit(2)
    要记的事实们.append(参数[i + 1])
    del 参数[i:i + 2]

问句们 = []                          # --问 可重复 —— 【多轮就是靠它重复出来的】，不用 stdin
while "--问" in 参数:
    i = 参数.index("--问")
    if i + 1 >= len(参数):
        print("--问 后面要跟一句话", file=sys.stderr)
        raise SystemExit(2)
    问句们.append(参数[i + 1])
    del 参数[i:i + 2]

位置参数 = [a for a in 参数 if not a.startswith("--")]
会话号 = 位置参数[0] if 位置参数 else "默认"
题号 = 位置参数[1] if len(位置参数) > 1 else None

# 本文件住在 agent-lab/ 根，arena/ 是它楼下的一层
arena根 = Path(__file__).resolve().parent / "arena"


def 要连的服务器们():
    """(显示名, 启动参数) 的清单 —— 跟 step5 一字不差。

    ⚠️ 记忆是【壳】，不是【第五个 server】。别顺手把档案也做成一个 MCP server ——
       那会把"进程内的一个 dict"吹成"多一个进程 + 一次握手"，
       而它每轮都要读、要拼进 system，本地才是对的落点。
    """
    清单 = [("资料柜", StdioServerParameters(command=sys.executable, args=["mcp_server.py"]))]
    if 题号 is not None:
        清单.append(("靶场", StdioServerParameters(command=sys.executable, args=["mcp_arena.py", 题号])))
    return 清单


def 读题面():
    """把 task.md 原文读进来 —— 跟 step5 一字不差。"""
    落点 = arena根 / "tasks" / 题号 / "task.md"
    if not 落点.is_file():
        print(f"没有这道题：{落点}", file=sys.stderr)
        raise SystemExit(2)
    return 落点.read_text(encoding="utf-8")

# ══════ 前三个测试开关跟 step5 一字不差 ══════
注入坏JSON = False
注入坏参数 = False
注入假工具名 = False
上限 = 8               # 【每一问】内部的工具轮次上限（不再是整场对话的上限）

today = date.today().isoformat()


def 转成openai工具(t) -> dict:
    """把 MCP 的 Tool 对象，装成 OpenAI 要的那两层壳 —— 跟 step5 一字不差。"""
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema,
        },
    }


# ══════════════════════════════════════════════════════════════
# 【新增】两把尺子
#
# ⚠️ 这两把尺子【量的不是同一件事】，别混：
#     量一量(messages)             事前估，随时能问，但只是估
#     resp.usage.prompt_tokens     事后真值，只有一个来源、也是最贵的一个
#
# 为什么两个都要：
#   「要不要压」必须在【发之前】回答 → 只有估的能用。
#   「压了有没有用」必须用【真值】回答 → 估的那把会骗你（下面 ⑦ 的实测会露出来）。
# ══════════════════════════════════════════════════════════════
def 量并报(账本: list, 要发的: list) -> None:
    """打印本轮的账本大小 —— 压没压、压掉多少，一屏看完。"""
    账 = 量一量(账本)
    if 要发的 is 账本:
        # 没压：只有一把数，多打一行一样的数是噪音
        print(f"   📏 账本 {账['条数']} 条 / {账['字符数']} 字 / 粗估 {账['粗估token']} token（未压）")
        return

    发 = 量一量(要发的)
    省 = 账["粗估token"] - 发["粗估token"]

    # ⚠️ 省 <= 0 这一支不是"以防万一"，是【双跑当场抓到过的事故】：
    #    轮数还没超过闸门时，压一压 会原样返回 —— 但它仍然可以插进一条省略提示。
    #    那样"压"就变成了纯亏（实测打印过 "压掉约 -7 token"）。
    #    ⭐ 之所以能发现，就因为有这一行对比；把 ⑤ 量 省掉，这个 bug 永远不现形。
    if 省 <= 0:
        print(f"   📏 账本 {账['条数']} 条 / 粗估 {账['粗估token']} token"
              f"（这一轮压不动：还没删满一轮，插提示反而是净增）")
        return

    print(f"   📏 账本 {账['条数']} 条 / 粗估 {账['粗估token']} token")
    print(f"   📏 发出 {发['条数']} 条 / 粗估 {发['粗估token']} token  ← 压掉约 {省} token")


def 记真值(resp, 轮次: int) -> None:
    """把模型报回来的真值记下来 —— 这一行就是 ⑦ 的核心。

    ⚠️ 真值在【模型那边】，本地算不出来。这就是为什么"先量后压"：
       你得先看见【不压】时的真值曲线，后面压出来的改善才有对照。
    """
    用量 = resp.usage
    命中 = getattr(用量, "prompt_cache_hit_tokens", None)
    后缀 = f"  缓存命中={命中}" if 命中 is not None else ""
    print(f"   📐 第 {轮次} 轮真值：prompt_tokens={用量.prompt_tokens}  "
          f"completion_tokens={用量.completion_tokens}{后缀}")


async def main():
    题面 = 读题面() if 题号 is not None else None

    # ══════════════════════════════════════════════════════════
    # 【新增】开聊前那四件事 —— 顺序就是 md 6.1 那张图
    #
    # ⚠️ 这四件事全在【拉起 server 之前】做，是刻意的：
    #    它们【不需要网络、不需要模型】。先把自己这边的账理清楚，
    #    再去接外面的世界。顺序反了也不报错，但读代码的人会以为"读档案得先联网"。
    # ══════════════════════════════════════════════════════════
    print("=" * 66)
    print(f"step6_memory.py  会话号={会话号}  压={'开' if 开压 else '关'}  保留最近 {保留轮数} 轮")
    print("=" * 66)

    # ① 第三层：把这一轮要记的事实先落进档案卡，再拼 system —— 顺序不能反，
    #    反了这次记的这条要等下次开聊才生效（不是 bug，但会让你以为"没记上"）。
    for 事实 in 要记的事实们:
        档案 = 记一笔(事实)
        print(f"🗂  记一笔：{事实}")
    if 要记的事实们:
        print(f"🗂  档案现有 {len(读档案().get('事实') or [])} 条事实")

    # ② 第三层：读档案 → 拼系统提示。
    #    ⚠️ 档案【贴在 system 里】，不塞进 messages 中间 —— 理由见 md 第 5 课：
    #       塞中间 → 它会被第一层的压一压裁掉，也会跟着会话一起膨胀；
    #       贴 system → 它每一轮都在最前面，模型永远看得见。
    #    ⚠️ 代价也在这：档案一变，system 就变 → 整个请求前缀的缓存全废。
    #       这就是为什么 记一笔 只让"事实只有几十条"的规模全量贴 ——
    #       真到几百条，就得从"全量贴"改成"按相关性检索"（那才是向量库该上场的时刻）。
    基础提示 = 建基础提示(题面)
    档案 = 读档案()
    系统提示 = 拼系统提示(档案, 基础提示)
    事实数 = len(档案.get("事实") or [])
    print(f"🗂  档案 {事实数} 条事实" + ("（已拼进 system）" if 事实数 else "）"))

    # ③ 第二层：读档。读不到就是新会话 —— 调用方不用写 if，因为"读不到 = 空"。
    旧账本 = 读会话(会话号)
    if 旧账本:
        print(f"📂 读档 {会话号}.json：{len(旧账本)} 条（上次聊到这儿）")
    else:
        print(f"📂 读档 {会话号}.json：没有 → 新会话")

    # ④ 【账本】—— 全量，只增不减，每次存盘存的是它。
    #
    #    ⚠️ 账本里【一定带着 system】。这一条不是格式讲究，是给 压一压 立的地基：
    #       压一压 的整个算法都建立在"messages[0] 是 system、永远留着"之上。
    #       账本要是把 system 剥掉，压一压 就会把【第一条 user】当成头焊住 ——
    #       那一轮对话没了开头（user 后面直接跟省略提示），而且白留一句远古的话。
    #       （我第一版就是这么写的，实测才发现。教训记在这儿。）
    #
    #    ⚠️ 续聊时那条 system 是【上次拼的】，档案可能已经长了新事实 ——
    #       所以整条【换掉】，不是往后追加。不换的话模型看到的是过期人设，
    #       这种错特别安静：你不会看到报错，只会觉得"它怎么没记住"。
    账本 = list(旧账本) if 旧账本 else []

    # ⭐ 这里有个必须想清楚的设计，也是本步最值钱的一处：
    #       【账本】和【要发的】必须是两个列表。
    #           账本    —— 全量，只增不减，压缩的结果【绝不写回】它
    #           要发的  —— 每轮从账本现压现算，带"（更早的对话已省略）"，绝不落盘
    #    混成一个会怎样？第一次压缩就等于把老历史【永久删掉】——
    #    而且你事后翻磁盘查不出来：文件里就是那份被压过的，连个对照物都没有。
    #    这正是 ★1 要求"返回新列表、别原地改"的真正原因 —— 不是为了好看。
    if not 账本 or 账本[0].get("role") != "system":
        账本.insert(0, {"role": "system", "content": 系统提示})
    else:
        账本[0] = {"role": "system", "content": 系统提示}

    # ⑤ 第一层：读回来的老账【必须再压一次】。
    #    ⚠️ 这是三层最容易被忽略的一处咬合：第二层解决"跨进程"，它【不解决】膨胀。
    #       磁盘上的账本只会越存越长；读回来整本塞进 messages 的话，
    #       第 2 课那个膨胀问题会【原封不动】回来。
    #       → 压不是"读档时做一次"就完了，是【每一轮发之前都做】。见下面循环里那行。

    async with contextlib.AsyncExitStack() as 栈:
        会话们 = {}
        for 名字, 参数_ in 要连的服务器们():
            读, 写 = await 栈.enter_async_context(stdio_client(参数_))
            会话 = await 栈.enter_async_context(ClientSession(读, 写))
            握手 = await 会话.initialize()
            会话们[名字] = 会话
            print(f"连上了：{握手.server_info.name}  version={握手.server_info.version}")

        哪些工具 = []
        电话簿 = {}
        for 名字, 会话 in 会话们.items():
            这柜子的工具 = (await 会话.list_tools()).tools
            print(f"  {名字}：{len(这柜子的工具)} 件")
            for t in 这柜子的工具:
                if t.name in 电话簿:
                    raise SystemExit(f"两个 server 有重名工具：{t.name}（名字必须全局唯一）")
                电话簿[t.name] = 会话
                哪些工具.append(转成openai工具(t))
        print(f"合计 {len(哪些工具)} 件工具")

        # ══════════════════════════════════════════════════════════
        # 【新增】尺子的固定偏差 —— 这一行是为"两把尺子对不上"准备的
        #
        # ⚠️ 第一轮实测就撞上的怪事：
        #       量一量报"粗估 17 token"，模型回的真值是 1121 —— 差 1000 多。
        #    不是谁算错了，是【尺子量不到这块】：
        #       量一量 只数 messages 里每条 content 的字符，
        #       而真正发出去的请求里还有【工具说明书】（tools 那份 JSON Schema）
        #       和【tool_calls 的 arguments】—— 这两块都不是 content，尺子看不见。
        #
        #    → 所以粗估永远是个【下界】，偏差 ≈ 一份工具说明书的体积，而且是常数。
        #      知道它是常数，就能减掉：真值 - 工具开销 ≈ 消息本身的量。
        #      （不知道的话，你会以为"我的压缩没用"或"token 算错了"，一路猜错。）
        #
        # ⭐ 这就是"两把尺子别混"的实操版：不是背一句"估算不准"，
        #    是【把不准的那部分量出来】，让它从"神秘误差"变成"已知常数"。
        # ══════════════════════════════════════════════════════════
        说明书字符 = len(json.dumps(哪些工具, ensure_ascii=False))
        print(f"🔧 工具说明书约 {说明书字符} 字（粗估 {int(说明书字符 * 0.7)} token）"
              f" —— 它不进 messages，尺子量不到，但每轮都真的发\n")

        传给模型的工具 = 哪些工具
        工具名集合 = set(电话簿)
        必填参数表 = {
            t["function"]["name"]: (t["function"]["parameters"].get("required") or [])
            for t in 哪些工具
        }

        # ⚠️ 不给 --问 就用各跑法的默认开场 —— 保证"跟 step5 一模一样"那条路还在，
        #    不然 _check_mcp_guard.py 那一类验收脚本的对照就断了。
        待问 = 问句们 if 问句们 else [默认开场(题面)]

        # ══════════════════════ 【新增】多轮的外层 ══════════════════════
        #
        # ⚠️ 这里是嵌套两层 while，但【别慌，它们管的是两件事】：
        #    外层 = 「用户说了几句话」（记忆的"轮"就是它）
        #    内层 = 「为了回这一句，模型来回往返了几次」（step5 那个循环，原样）
        #    第一层记忆的"轮"按【外层】数 —— 这正是 ★1 里"数 user"的道理：
        #    user 就是外层的刻度，assistant/tool 都是内层的产物。
        for 第几问, 问句 in enumerate(待问, 1):
            print(f"\n{'━' * 66}\n👤 第 {第几问}/{len(待问)} 问：{问句}\n{'━' * 66}")
            账本.append({"role": "user", "content": 问句})

            轮次 = 0
            while True:
                轮次 += 1

                # ── ⑤ 量 + 压（都在 create 之前）──────────────────
                # ⚠️ 顺序反了就不叫"压缩"了，叫"事后统计"。
                #    估的这把尺子的【唯一用途】就是在这里做决定。
                要发的 = 压一压(账本, 保留轮数) if 开压 else 账本
                量并报(账本, 要发的)

                if 轮次 > 上限:
                    # 收口那份也要记账本 —— 不记的话，下一轮读档就少一条，配平会错位
                    收口 = {"role": "system", "content": "轮次已用尽，请直接告诉用户目前查到了什么、还剩什么没查完"}
                    账本.append(收口)
                    要发的 = 压一压(账本, 保留轮数) if 开压 else 账本
                    resp = client.chat.completions.create(model="deepseek-chat", messages=要发的)
                    记真值(resp, 轮次)
                    print(f"\n⚠️ 轮次用尽（已转满 {上限} 轮）—— 下面是收口，不是正常完成")
                    print(f"🏁 它说：{resp.choices[0].message.content}")
                    存会话(会话号, 账本)
                    break

                print(f"\n════════ 第 {轮次} 轮 ════════")

                # ── ⑥ 调模型 ──────────────────────────────────────
                # ⚠️ 唯一的变化：messages=要发的（不再是 账本）。
                #    其余一字未改 —— 循环体不知道"发出去的可能被压过"，它也不该知道。
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=要发的,
                    tools=传给模型的工具,
                )
                记真值(resp, 轮次)

                msg = resp.choices[0].message

                # ⚠️⚠️ 这一行是【整个 step6 最容易翻车的一行】。
                #
                # step5 里写的是 messages.append(msg) —— 直接塞 openai SDK 的
                #   ChatCompletionMessage 对象。循环里能用（读 msg.tool_calls 一样读），
                #   所以看不出问题……直到你调 存会话()：
                #       TypeError: Object of type ChatCompletionMessage
                #                  is not JSON serializable
                #
                # ⭐ 正解不是"让存会话容忍对象"，是【记账本这一端就别混进对象】：
                #    model_dump(exclude_none=True) 换成纯字典，
                #    而且刚好就是 OpenAI 收得下的那套键（content/role/tool_calls）。
                #    exclude_none 是为了把 content=None 之类的空键剃掉 ——
                #    带着 tool_calls、content 为 null 的那条 assistant，是标准格式，不用怕。
                #
                # ⭐ 记住这个味道：**"存不进去"的根因常常不在"存"这一端，
                #    在账本里混进了不该混的东西。** 往上游找，比在下游加 try 强。
                账本.append(msg.model_dump(exclude_none=True))

                if not msg.tool_calls:
                    print(f"\n🏁 它说：{msg.content}")
                    存会话(会话号, 账本)
                    break

                for tc in msg.tool_calls:
                    if 注入坏JSON:
                        tc.function.arguments = tc.function.arguments[:-1]
                    if 注入假工具名:
                        tc.function.name = "飞上天"

                    if tc.function.name not in 工具名集合:
                        正文 = "\n".join(f"- {名}" for 名 in sorted(工具名集合))
                        正文 = f"{tc.function.name}不在可用工具里，请使用下面这些：\n{正文}"
                        print(f"  ⚠️ 模型瞎编工具名：{tc.function.name}")
                        账本.append({"role": "tool", "tool_call_id": tc.id, "content": 正文})
                        continue

                    try:
                        参 = json.loads(tc.function.arguments)
                    except Exception as e:
                        print(f"  ⚠️ arguments 不是合法 JSON：{type(e).__name__}: {e}")
                        账本.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"{tc.function.arguments}无效：{type(e).__name__}: {e}",
                        })
                        continue

                    if 注入坏参数:
                        缺 = 必填参数表.get(tc.function.name, [])
                        if 缺:
                            参.pop(缺[0], None)

                    print(f"  🔧 调用工具 {tc.function.name}  参数={参}")

                    结果 = await 电话簿[tc.function.name].call_tool(tc.function.name, 参)
                    块们 = []
                    for r in 结果.content:
                        if r.type == "text":
                            块们.append(r.text)
                    文本 = "".join(块们)

                    if 结果.is_error:
                        print(f"     ↳ 工具报错：{文本}")
                    else:
                        print(f"     ↳ 返回：{文本}")

                    账本.append({"role": "tool", "tool_call_id": tc.id, "content": 文本})

    # ══════════════════════ 散场盘点 ══════════════════════
    # ⚠️ 这一段存在的理由：证明"两个列表"确实分开了。
    #    压过的那一份没有落盘，账本一条没丢。
    print("\n" + "=" * 66)
    落点 = 存会话(会话号, 账本)
    量 = 量一量(账本)
    print(f"💾 账本落盘：{落点.name}  {落点.stat().st_size} 字节  "
          f"{量['条数']} 条 / 粗估 {量['粗估token']} token")
    print(f"🗂  档案卡：{len(读档案().get('事实') or [])} 条事实")
    print(f"🚪 下次接着聊：step6_memory.py {会话号}")
    if 开压:
        print(f"   （本次开了 --compress，但磁盘上存的是【没压过】的全量账本 —— 压只作用于发出去的那一份）")
    print("=" * 66)


def 建基础提示(题面: str | None) -> str:
    """这次对话的【基础】system 正文 —— 也就是 step5 里那一坨，不含档案。

    ⚠️ 为什么要跟档案分开、再交给 拼系统提示 拼起来：
       因为档案是【会变的】，基础提示是【不变的】。
       两块分开写，才能在"档案换了、人设没换"的时候一眼看出来。
       混成一个大字符串以后，你就分不清哪句是规则、哪句是从档案来的了。
    """
    if 题面 is None:
        return (
            f"今天是{today},记得说到日期的时候以今天/明天/后天,这样为准。"
            "无论用户用什么语言提问，始终用简体中文回答。"
        )
    return (
        f"今天是{today}。无论用户用什么语言提问，始终用简体中文回答。\n"
        "你在一个修 bug 的靶场里工作。规则：\n"
        "1. tests/ 只读，不许改 —— 改了就是作弊。\n"
        "2. 先读报错，再定位，改完必须跑 run_tests 验证，不许凭感觉说修好了。\n"
        "3. 最多改 3 轮。修不动就如实说修不动，别硬凑。\n"
        f"题面：\n{题面}"
    )


def 默认开场(题面: str | None) -> str:
    """不给 --问 时的开场 —— 跟 step5 那两条一字不差。"""
    if 题面 is None:
        return "帮我把『周五开会改到下午三点』记到笔记里，文件名就叫 会议变更.md"
    return "开始吧。"


# 守卫：定义在前，开跑在后。（跟 step5 同一条规矩）
if __name__ == "__main__":
    asyncio.run(main())
