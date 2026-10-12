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
"""

import asyncio
import json
import os
import sys
from datetime import date

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

# 跟 _client_demo.py 里那套一样：让子进程用【当前这个解释器】去跑 mcp_server.py，
# 免得 PATH 里的 python 是另一个、没装 mcp。
启动参数 = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server.py"],
)

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
    # ① 拉起服务端 —— 这是一个【真的新进程】，不是 import
    async with stdio_client(启动参数) as (读, 写):
        # ② 握手：说好协议版本、交换能力清单
        async with ClientSession(读, 写) as 会话:
            握手 = await 会话.initialize()
            print(f"连上了：{握手.server_info.name}  version={握手.server_info.version}")
            print(f"协议版本：{握手.protocol_version}")

            工具清单 = (await 会话.list_tools()).tools
            哪些工具 = [转成openai工具(t) for t in 工具清单]
            print(f"从 MCP 拿到 {len(哪些工具)} 件工具\n")

            # 手写版这里传的是 tools.TOOLS —— 说明书自己写死在 tools.py 里。
            # 现在传的是刚从服务端拿回来、翻译好的这批 —— 说明书是【别人给的】。
            传给模型的工具 = 哪些工具

            # 手写版第二道防线比的是 tools.TOOL_MAP（名字 → 函数的"电话簿"），
            # 因为那时候函数得自己执行。现在执行发生在服务端那侧，我们只需要
            # 知道"哪些名字是合法的"，所以从工具清单里抠一份名字出来。
            #
            # ⚠️ 2026-10-12 改成 set：`名字 in 名单` 是"看一眼就知道在不在"的
            #    判断题，set 一次命中、list 挨个找。五件工具时无所谓，多了才显出来。
            工具名集合 = {t["function"]["name"] for t in 哪些工具}

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
            # 2026-10-12 换的任务：考【docstring 顶不顶用】——
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
                    # MCP 版一句：call_tool(工具名, 参数字典)。电话簿在服务端那侧。
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
                    结果 = await 会话.call_tool(tc.function.name, 参数)

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
                    # ⚠️ 已知瑕疵（待改）：上面两句 print 打的是 块们（列表，拼接【前】），
                    #    而真正发出去的是 文本。日志和实际发出去的不是同一个东西 ——
                    #    以后排查会把人带沟里。改法：把 print 挪到 文本 = "".join(块们) 之后。
                    #
                    # 结构上顺带简化了：手写版那【两层嵌套 try】现在只剩一层。
                    #    外层 try 管"JSON 坏没坏"，内层 try 管"调用成没成"。
                    #    内层那个没了 —— 调用不再抛异常。四条防线
                    #    从「两层 try + 一个 if」变成「一层 try + 两个 if」。


# 守卫：定义在前，开跑在后。（跟 mcp_server.py 同一条规矩）
# 少了它，对账脚本 import 这个文件时会【顺手把服务器再拉一个】。
if __name__ == "__main__":
    asyncio.run(main())
