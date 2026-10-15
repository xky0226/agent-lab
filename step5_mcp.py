"""第 5 步：同一个循环、同四条防线 —— 换成隔着 MCP 说话。

对照物：step4_guard.py —— 手写版，一个字没动，留着并排放。
同一个 while、同四条防线，只有【接工具那一段】换了。
（prompt 2026-10-12 换过一次：从"查天气→记待办"改成"记笔记"，
  为了单独考 docstring 顶不顶用。step4_guard.py 那边没跟着换，对照时注意。）

手写版 → MCP 版，一共 5 处：

    位置                 手写版                      MCP 版
    ─────────────────────────────────────────────────────────────────────
    1  工具说明书       tools.TOOLS               list_tools() + 格式翻译
    2  假工具名那条线    name not in TOOL_MAP      比一份名字的名单
    3  怎么调           函数(**参数)               await 会话.call_tool(...)
    4  怎么判错         try/except                  if 结果.is_error
    5  怎么取文本        结果本身就是字符串          从 .content 拆块取 .text

不动的一处（重要）：① 坏 JSON 那条线一个字不改 —— 它发生在【你这边的 json.loads】，
跟工具有没有跨进程毫无关系。改架构时能一眼看出"哪些没动"，是好设计的标志。

验收：_check_mcp_guard.py（四条防线）、_check_mcp_tools.py（格式翻译对账）

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe step5_mcp.py

═══════════════════════════════════════════════════════════════════════════
🆕 2026-10-13 第 5 刀：从【一个 server】扩成【两个 server】

    资料柜  mcp_server.py   文档资料柜（docs/ 只读、notes/ 只增不改）
    靶场    mcp_arena.py    修 bug 靶场（arena/tasks/<题号>/，只有 src/ 可写）

跑法多了一个【可选】的题号：

    .venv\\Scripts\\python.exe step5_mcp.py                     ← 老模式：只连资料柜，跑"记笔记"
    .venv\\Scripts\\python.exe step5_mcp.py t01_grade_boundary  ← 新模式：两个都连 + 题面 + 修 bug

⚠️ 为什么【留两个模式】，不是顺手把 prompt 换掉就算了：
   _check_mcp_guard.py 是【import 这个文件、再调 main()】去验四条防线的。
   要是这里直接换成"修 bug"，那个脚本就会去靶场里真改真跑 ——
   ① 它判出来的红绿不再等于"防线在不在"（改了代码、跑过测试，模型行为全变了）
   ② 它会真把 t01 的 bug 修掉，第二次跑就【没得修了】，验收变成一次性的
   验防线的那条路必须【零副作用】，所以默认那条一个字没动。

⚠️ 两条路的链子完全不同：老模式【不连靶场】= 不开 pytest 进程；
   新模式才连靶场。要不要动盘、动哪个盘，取决于命令行给没给题号。
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

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
)

# ══════════════════════════════════════════════════════════════
# 要连几个 server —— 命令行说了算
#
# ⚠️ 题号由【启动方】给，不让模型给（跟 mcp_arena.py 开头那条规矩同源）：
#    模型能自己挑题号，就等于它能换一道题去读。
# ══════════════════════════════════════════════════════════════
题号 = sys.argv[1] if len(sys.argv) > 1 else None

# 本文件住在 agent-lab/ 根，arena/ 是它楼下的一层
arena根 = Path(__file__).resolve().parent / "arena"


def 要连的服务器们():
    """(显示名, 启动参数) 的清单 —— 题号给了才把靶场接上。

    ⚠️ 两件事都跟 _client_demo.py 里那套一样：
       ① command 用 sys.executable —— 让子进程用【当前这个解释器】跑，
          免得 PATH 里的 python 是另一个、没装 mcp。
       ② args 里【每个参数各占一格】。写成 args=["mcp_arena.py t01_xxx"] 是错的，
          子进程会去找一个名字就叫「mcp_arena.py t01_xxx」的文件。
    """
    清单 = [("资料柜", StdioServerParameters(command=sys.executable, args=["mcp_server.py"]))]
    if 题号 is not None:
        清单.append(("靶场", StdioServerParameters(command=sys.executable, args=["mcp_arena.py", 题号])))
    return 清单


def 读题面():
    """把 task.md 原文读进来（题面 = 这次要修的那道题）。

    ⚠️ 读不到就【当场退出】，不退的话它会在一道不存在的题上瞎改 ——
       而它自己并不知道题面是空的（它没有"应该长什么样"的参照物）。
    """
    落点 = arena根 / "tasks" / 题号 / "task.md"
    if not 落点.is_file():
        print(f"没有这道题：{落点}", file=sys.stderr)
        raise SystemExit(2)
    return 落点.read_text(encoding="utf-8")

# ══════ 四个可调参数（前三个跟 step4_guard.py 一字不差）══════
注入坏JSON = False     # 测试开关：让 arguments 坏掉（模拟 ①）
注入坏参数 = False     # 测试开关：删掉一个必填参数（模拟 ③）
注入假工具名 = False   # 测试开关：把工具名改成不存在的（模拟 ②）—— 手写版没有这个开关
上限 = 8               # 轮次上限：测试用 1（逼出"半成品"）；上线值 8~10

today = date.today().isoformat()


# ══════════════════════════════════════════════════════════════
# 格式翻译：MCP 的 Tool 对象  →  OpenAI 要的两层壳
#
# 两边说的其实是同一种话：JSON Schema。MCP 没发明新格式，它用的是大家都认的
# 那个"普通话"—— 所以这个翻译函数只要套壳，不需要逐字段搬运。
#
#   手写版（tools.TOOLS[i]）：{"type": "function",
#                              "function": {"name": …, "description": …, "parameters": …}}
#   MCP 递来的 t：          name / description / input_schema —— 三个【属性】，没有壳
#
# 关键：t.input_schema 那坨【本身就是一个装满的箱子】—— 整个搬进 "parameters" 就行。
#   踩过的坑：一开始写成 "properties": t.input_schema，等于把箱子塞进了箱子里的一格
#   —— parameters 底下多出一层 properties，同时顶层的 required 也没了。
#   对账脚本（_check_mcp_tools.py）一跑就现形：报错路径是
#   function.parameters.properties.properties（从外往里念，两层 properties）。
#
# ⚠️ 壳里那个键叫 "parameters"，不叫 "input_schema"。名字照搬，OpenAI 当场不认。
# ══════════════════════════════════════════════════════════════
def 转成openai工具(t) -> dict:
    """把 MCP 的 Tool 对象，装成 OpenAI 要的那两层壳。"""
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema,
        },
    }


async def main():
    题面 = 读题面() if 题号 is not None else None

    # ① 拉起服务端 —— 每一个都是【真的新进程】，不是 import
    #
    # ⚠️ 这里从"写死的一层 async with"改成了 AsyncExitStack：
    #    server 的【个数】现在是运行时才知道的（给没给题号），嵌套 with 写不出来。
    #    栈的规矩：后进去的先出来 —— 跟两层嵌套 async with 完全一样的顺序，
    #    只是改成"有几个就攒几个"，退出时它自己挨个关。
    async with contextlib.AsyncExitStack() as 栈:
        会话们 = {}
        for 名字, 参数 in 要连的服务器们():
            # ② 拉起进程 → 握手：说好协议版本、交换能力清单
            读, 写 = await 栈.enter_async_context(stdio_client(参数))
            会话 = await 栈.enter_async_context(ClientSession(读, 写))
            握手 = await 会话.initialize()
            会话们[名字] = 会话
            print(f"连上了：{握手.server_info.name}  version={握手.server_info.version}")
            print(f"协议版本：{握手.protocol_version}")

        # ③ 把每个 server 的工具【并成一份菜单】，同时留一张【名字 → 会话】的电话簿
        #
        # ⚠️ 这张电话簿就是"双 server"多出来的那件东西：手写版有 TOOL_MAP
        #    （名字 → 函数），MCP 单 server 版靠"只有一个会话，不用挑"，
        #    现在两个会话了，就必须回答"这个名字该问谁"。
        哪些工具 = []
        电话簿 = {}
        for 名字, 会话 in 会话们.items():
            这柜子的工具 = (await 会话.list_tools()).tools
            print(f"  {名字}：{len(这柜子的工具)} 件")
            for t in 这柜子的工具:
                if t.name in 电话簿:
                    # ⚠️ 设计文档 §7 坑 1，在这里把它变成代码：
                    #    重名会【静默去重】—— 名单里少一件看不出来，
                    #    模型点了这个名字，到底发给哪个 server 只有字典知道。
                    #    所以不许安静地覆盖：当场炸，比事后猜便宜。
                    raise SystemExit(f"两个 server 有重名工具：{t.name}（名字必须全局唯一）")
                电话簿[t.name] = 会话
                哪些工具.append(转成openai工具(t))
        print(f"合计 {len(哪些工具)} 件工具\n")

        # 手写版这里传的是 tools.TOOLS —— 说明书自己写死在 tools.py 里。
        # 现在传的是刚从服务端拿回来、翻译好的这批 —— 说明书是【别人给的】。
        传给模型的工具 = 哪些工具

        # 手写版第二道防线比的是 tools.TOOL_MAP（名字 → 函数的"电话簿"），
        # 因为那时候函数得自己执行。现在执行发生在服务端那侧，我们只需要
        # 知道"哪些名字是合法的"，所以从工具清单里抠一份名字出来。
        #
        # ⚠️ 2026-10-12 改成 set：`名字 in 名单` 是"看一眼就知道在不在"的
        #    判断题，set 一次命中、list 挨个找。五件工具时无所谓，多了才显出来。
        #
        # ⚠️ 2026-10-13 改成【直接抄电话簿的钥匙】：名单和路由从此【同一个来源】，
        #    不可能出现"名单里有、电话簿里没有"这种对不上的状态。
        工具名集合 = set(电话簿)

        # 每件工具"必填参数"的名字 —— 只给下面「注入坏参数」那一枪用。
        # ⚠️ 别再写死参数名。原来写的是 参数.pop("due_date", None)，只因为当时
        #    的 prompt 会让模型去调 add_todo。2026-10-12 把 prompt 换成 write_note
        #    之后，due_date 根本不是它的参数 —— 这一枪【当场失效】
        #    （_check_mcp_guard.py ③ 报 ❌，且是"没走到那一步"型，不是"没拦住"型）。
        #    改成【照当前这个工具现挑】，换任务、换工具都不用再动这里。
        必填参数表 = {
            t["function"]["name"]: (t["function"]["parameters"].get("required") or [])
            for t in 哪些工具
        }

        # ══════════════════════ 开场 ══════════════════════
        # ⚠️ 2026-10-13：开场从"一句话"变成了"两条路"，但【两条路都不碰循环】——
        #    prompt 是循环的输入，不是循环本身。
        if 题面 is None:
            # 老模式：2026-10-12 的任务，考【docstring 顶不顶用】——
            # 只让它"记笔记"，prompt 里一个工具名都不提，看它自己认不认 write_note。
            # 结果：它自己点了 write_note，文件名照抄用户说的，盘上真落地。
            #
            # （上一版是"先查天气 → 再记待办"的两步走任务，专门考「半成品」配平
            #   —— 那段设计还在 step4_guard.py 里，别删。）
            #
            # ⚠️ 想换回天气任务的话：别写成"下周五" —— 今天是周五的话它会落到
            #    3 天窗口外面，撞上 get_weather 的能力边界，看不到完整正常路径。
            messages = [
                {"role": "system", "content": f"今天是{today},记得说到日期的时候以今天/明天/后天,这样为准。无论用户用什么语言提问，始终用简体中文回答。"},
                {"role": "user", "content": "帮我把『周五开会改到下午三点』记到笔记里，文件名就叫 会议变更.md"},
            ]
        else:
            # 新模式：题面进 system，【不是】进第一条 user。
            #
            # ⚠️ 为什么题面要放 system：它是这次任务的【规格】，跟"你是修 bug 的"一个级别，
            #    不是某一次对话里说的话。多轮之后 user 那条会被越推越远，
            #    system 始终在每一轮的【最前面】—— 规格要站在那里。
            #
            # ⚠️ 第 3 条那句"修不动就说修不动"不是客套，是【故意把凑答案的收益打掉】：
            #    不说这句，轮到上限时它会编一个看起来对的改动交差（第 4 步那次实测过）。
            #    对应工具侧那件事：让"办不到"变成一个【说出来不亏】的选项。
            messages = [
                {"role": "system", "content": (
                    f"今天是{today}。无论用户用什么语言提问，始终用简体中文回答。\n"
                    "你在一个修 bug 的靶场里工作。规则：\n"
                    "1. tests/ 只读，不许改 —— 改了就是作弊。\n"
                    "2. 先读报错，再定位，改完必须跑 run_tests 验证，不许凭感觉说修好了。\n"
                    "3. 最多改 3 轮。修不动就如实说修不动，别硬凑。\n"
                    f"题面：\n{题面}"
                )},
                {"role": "user", "content": "开始吧。"},
            ]

        轮次 = 0

        while True:
            轮次 += 1

            if 轮次 > 上限:
                messages.append({"role": "system", "content": "轮次已用尽，请直接告诉用户目前查到了什么、还剩什么没查完"})
                resp = client.chat.completions.create(model="deepseek-chat", messages=messages)  # ← 没带 tools
                end_result = resp.choices[0].message.content
                print(f"\n⚠️ 轮次用尽（已转满 {上限} 轮）—— 下面是收口，不是正常完成")
                print(f"🏁 它说：{end_result}")
                break

            print(f"\n════════ 第 {轮次} 轮 ════════")

            # ── ① 调模型 ──────────────────────────────────────
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=传给模型的工具,
            )
            msg = resp.choices[0].message
            messages.append(msg)

            # ── ② 出口：它不点菜了，就是在说话 ──────────────────
            if not msg.tool_calls:
                print(f"\n🏁 它说：{msg.content}")
                break

            # ── ③ 它点菜了 —— 可能一次点好几个，一个个做 ──────────
            for tc in msg.tool_calls:
                if 注入坏JSON:
                    tc.function.arguments = tc.function.arguments[:-1]
                if 注入假工具名:
                    tc.function.name = "飞上天"      # ② 假工具名：模型绝不会主动编的名字

                # ② 假工具名：手写版查的是"在不在电话簿里"，现在查"在不在名单上"。
                #    跟手写版一样用 if 提前拦 —— 这是"看一眼就知道"的判断题。
                if tc.function.name not in 工具名集合:
                    正文 = "\n".join(f"- {名}" for 名 in sorted(工具名集合))
                    正文 = f"{tc.function.name}不在可用工具里，请使用下面这些：\n{正文}"
                    print(f"  ⚠️ 模型瞎编工具名：{tc.function.name}")
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": 正文})
                    continue

                # ── 坏 JSON 这条线：一个字不改 ─────────────────
                # 它发生在【我们这边】的 json.loads，跟工具有没有跨进程无关。
                try:
                    参数 = json.loads(tc.function.arguments)
                except Exception as e:
                    print(f"  ⚠️ arguments 不是合法 JSON：{type(e).__name__}: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"{tc.function.arguments}无效：{type(e).__name__}: {e}",
                    })
                    continue

                if 注入坏参数:
                    # 摘掉【当前这个工具】的一个必填参数 → 服务端 Pydantic 报校验错。
                    # 现挑，不写死 —— 理由见上面 必填参数表 那段。
                    缺 = 必填参数表.get(tc.function.name, [])
                    if 缺:
                        参数.pop(缺[0], None)

                print(f"  🔧 调用工具 {tc.function.name}  参数={参数}")

                # ── 执行：请管子对面的进程做事 ──────────────────────────
                # 手写版是两句：先查电话簿拿函数（tools.TOOL_MAP[...]），再 函数(**参数)。
                # MCP 单 server 版一句：会话.call_tool(工具名, 参数字典)。
                # 双 server 版多一步：先问【电话簿】"这个名字归谁管"，再让那个会话去调。
                #   ⚠️ 手写版的电话簿是【名字 → 这里的一个函数】；这里的电话簿是
                #      【名字 → 那一边的一个会话】。函数在哪一侧，才是第 7 步真正的变化。
                #
                # ⚠️ 判错换了：手写版用 try/except —— 因为函数出错会【抛异常】。
                #    MCP 里工具出错【不抛异常】，它变成结果上的 is_error 字段返回。
                #    依据 _probe_call_error.py：少传必填参数时 is_error=True。
                #    → try 抓不到，必须换成 if 结果.is_error。
                #    这么设计的理由：错误本身是【给模型看的信息】，模型看见
                #    is_error 会自己改参数重试；抛异常链路就断了，模型永远看不到。
                #
                # ⚠️ 取文本换了：手写版 结果 本身就是字符串，直接塞进 messages。
                #    MCP 的结果是【一串内容块】（content）—— 一次调用可能同时回
                #    文字+图片+文件，每块自己声明 type，正文在 .text。
                #    → 自己拆块，把 type=="text" 的拼成一整串。
                #
                # ⚠️ 连"块"的箱子两边都不是同一个：
                #      MCP 的块：TextContent(type='text', text='…')   ← 对象，用 . 取
                #      OpenAI 的块：{"type": "text", "text": "…"}      ← dict，用 [] 取
                #    所以不能把 MCP 的块原样丢给 OpenAI。最稳的桥是【退回两边
                #    都认的共同形式：一串纯文字】。实测直接把列表 ["查不到…"]
                #    塞进 content 会 422（content 要么是纯字符串，要么是块 dict）。
                结果 = await 电话簿[tc.function.name].call_tool(tc.function.name, 参数)

                块们 = []
                for r in 结果.content:
                    if r.type == "text":
                        块们.append(r.text)

                # ⚠️ 先拼好，再打印 —— 顺序反了，日志就撒谎（2026-10-12 实测）：
                #    原来 print 打的是【列表】块们（屏幕上：['已经写入']），
                #    而真正塞进 messages、给模型看的是【拼好的字符串】（已经写入）。
                #    两个不同的东西。内容短看不出，多行/多块时你照着日志
                #    根本认不出模型的处境，只能靠猜。
                文本 = "".join(块们)

                if 结果.is_error:
                    print(f"     ↳ 工具报错：{文本}")
                else:
                    print(f"     ↳ 返回：{文本}")

                messages.append({"role": "tool", "tool_call_id": tc.id, "content": 文本})

                # ⚠️ 铁律没变：每个 tool_call_id 都必须回一条账（配平），
                #    对错都要回 —— 因为【错误本身也是给模型看的信息】。
                #
                # ✅ 那条"已知瑕疵"（print 打 块们、发出去的却是 文本）2026-10-13 已修：
                #    两句 print 现在都排在 文本 = "".join(块们) 之后，日志跟发出去的是同一个东西。
                #    留这条记录，是因为它只踩过一次就够贵了 —— 日志撒谎的时候，
                #    你会照着日志去猜"模型到底看到了什么"，然后一路猜错。
                #
                # 🔪 第 5 刀在【循环体里只改了上面那一行】（会话 → 电话簿[名字]）。
                #    四条防线、配平、收口、两条 print，一个字没动。
                #    "改了架构后哪些没动一眼能看出来" —— 跟本文件开头那句是一回事。
                #
                # 结构上顺带简化了：手写版那【两层嵌套 try】现在只剩一层。
                #    外层 try 管"JSON 坏没坏"，内层 try 管"调用成没成"。
                #    内层那个没了 —— 调用不再抛异常。四条防线
                #    从「两层 try + 一个 if」变成「一层 try + 两个 if」。


# 守卫：定义在前，开跑在后。（跟 mcp_server.py 同一条规矩）
# 少了它，对账脚本 import 这个文件时会【顺手把服务器再拉一个】。
if __name__ == "__main__":
    asyncio.run(main())
