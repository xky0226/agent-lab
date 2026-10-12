"""
第 7 步 ②：把工具柜包成一个 MCP Server。

它和手写 Agent 的关系 —— 函数本体一个字没改，只换了一根电话线：

    step3_agent.py ──import──> tools.py                   同进程。自己拧的线。
    别的程序 ──JSON-RPC over stdio──> mcp_server.py        两个进程。标准插头。

形状上只有【一处】不一样：

    手写版：说明书是手写在 tools.py 里 TOOLS 列表的字典
            加一件工具要改【3 处】—— 函数本体 / TOOLS 里的字典 / TOOL_MAP 的登记
    MCP 版：说明书就是函数的 docstring
            加一件工具只动【1 处】，签名和 docstring 就是全部的登记

跑法：
    .venv\\Scripts\\python.exe mcp_server.py

    ⚠️ 跑起来什么都不打印、就那么停着 —— 【这是对的】。
       stdio 模式它在等客户端说话，没人连它就安静等着。不是卡死，别慌着 Ctrl+C。
    ⚠️ stdio 模式严禁 print()：你往 stdout 打一行字就污染了协议报文，客户端直接崩。
       要打印就打 stderr。

探针（不启动服务，把 server 导进来问它）：
    .venv\\Scripts\\python.exe _probe_tools.py
    ← 这个探针能跑，全靠文件末尾那句 if __name__ == "__main__" 守卫。

教材：D:\\toutiao\\MCP 从零入门课.md
      第 3 课 例题 + 逐行拆 / 第 4 课 裸 JSON-RPC 实录 / 第 5 课 Annotated 捡回参数说明
"""

# 本体一个字不改，还躺在 tools.py 里 —— 这里只是【引用】它，不是复制它。
# 写成 import tools 而不是 from tools import get_weather，是因为
# 下面那件工具的函数名也叫 get_weather，直接 import 进来会撞名。
import tools

from pathlib import Path

# Annotated[str, Field(description="…")] —— 参数字典里那句话的落点。
# Annotated 不改"是字符串"这个事实，只给这个位置挂一张便签；
# Field 写着便签的内容；Pydantic 从签名长 schema 时会把便签抄进 input_schema。
from typing import Annotated

from pydantic import Field

# mcp 2.x 把 FastMCP 改名成了 MCPServer。
# 网上 99% 的教程还是 1.x 的 `from mcp.server.fastmcp import FastMCP`，照抄会
# ModuleNotFoundError —— 而 site-packages/mcp/server/fastmcp.py 那个文件是
# 【故意 raise】的，它一行 API 都没有，唯一工作就是把迁移指南塞进报错里。
from mcp.server.mcpserver import MCPServer

# MCP 自己的异常类 —— 下面 read_doc 报错要用。
# 【只有这类异常保得住原话】：普通的 FileNotFoundError / ValueError 会被 SDK
# 吞成一句干巴巴的 "UnexpectedResourceError: Error creating resource from template …"，
# 你写的诊断一个字都到不了客户端。实测对照见 _demo_resource_error.py。
from mcp.server.mcpserver.exceptions import ResourceNotFoundError

上限 = 5000
# 名字。客户端连上来时能看见它。
server = MCPServer("demo")


# 装饰器 = 手写版"往 TOOLS 列表里加一本字典"那一步。
# 参数和说明书都是【从函数自己身上读】的：
#     签名（city: str, date: str）  →  input_schema
#     docstring                     →  description
# ⚠️ docstring 不写就是空字符串 ''，跟没配说明书一样。
#
# 下面是全部五件工具。五段 docstring 都是 tools.py 里 TOOLS[i].description 的
# 原话，逐字符一致（_check_mcp.py 对过账）。
@server.tool()
def get_weather(city: Annotated[str, Field(description="城市中文名，例如：成都、北京")],
                date: Annotated[str, Field(description="查询哪一天，格式必须是 YYYY-MM-DD，例如：2026-10-01")]) -> str:
    """查询指定城市某一天的天气。涉及天气的问题必须调用此工具，不得凭记忆回答。"""
    return tools.get_weather(city, date)


@server.tool()
def get_exchange_rate(from_currency: Annotated[str, Field(description="货币代码，三位大写字母。例如：美元=USD、人民币=CNY、日元=JPY、英镑=GBP")],
                      to_currency: Annotated[str, Field(description="货币代码，三位大写字母。例如：美元=USD、人民币=CNY、日元=JPY、英镑=GBP")]) -> str:
    """查询指定货币的汇率,并返回结果,涉及货币汇率的问题必须调用此工具,不得凭记忆回答"""
    return tools.get_exchange_rate(from_currency, to_currency)


@server.tool()
def add_todo(content: Annotated[str, Field(description="待办的内容，一句话，例如：买菜")],
             due_date: Annotated[str, Field(description="日期，格式必须是 YYYY-MM-DD，例如：2026-09-23")]) -> str:
    """给用户添加一条待办事项。用户说「帮我记一下」「加个提醒」「记到日程里」时必须调用此工具。"""
    return tools.add_todo(content, due_date)


@server.tool()
def get_calendar(date: Annotated[str, Field(description="查询待办的日期,查该日期的所有安排,格式必须是YYYY-MM-DD, 例如:2026-09-23")]) -> str:
    """查询用户输入日期的待办事项,用户说:「帮我看看今日安排」「帮我查看今日事情」「查看今日待办」时必须调用此工具。"""
    return tools.get_calendar(date)


@server.tool()
def search_docs(query: Annotated[str, Field(description="检索用的关键词或问题，例如：年假有几天")]) -> str:
    """在内部知识库（员工手册、公司规章制度、流程规范等）里检索资料。用户问公司制度、规定、流程时必须调用此工具，不得凭记忆回答。"""
    return tools.search_docs(query)


# ═════════════════════════════════════════════════════════════
# 上面五件 = 手写工具柜的 MCP 版。加一件工具只动【1 处】：
#   签名      →  input_schema（参数名、类型、必填）
#   docstring →  description
#   Annotated[str, Field(description="…")]  →  input_schema 里那句参数说明
# 手写版要改【3 处】（函数本体 / TOOLS 的字典 / TOOL_MAP 的登记），
# MCP 版的说明书是【从函数自己身上读的】，不写就没有（description 会是 ''）。
#
# ⚠️ 改签名是【结构】改动，会连带碰坏别的东西 —— 这叫【回归】：
#    重排 get_exchange_rate 签名时，它的 docstring 被挤掉了，description
#    变成 ''。（docstring 不是独立注解，它是【函数体的第一句字符串】，
#    动函数体就可能把它挤掉。）是 _check_mcp.py 的 ② 段当场抓出来的 ——
#    任务 1（docstring）和任务 2（参数说明）的验收写在【同一个脚本】里，
#    改 A 弄坏 B 藏不住；只跑 _probe_tools.py 看一眼"哦，5 件"会漏。
# ═════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════
# 下面 = 「文件系统 Server」—— 路线图第 7 步正菜
#
#   tool 是【动词】—— 模型伸手去拿，要"做"一件事
#   resource 是【名词】—— 一堆只读的资料摆在那儿，读不读由客户端说了算
#   餐厅类比：resource = 墙上的菜单 / 橱窗，你没点，它也在那儿
#
#   URI 里带 {name} 的叫【模板资源】——花括号那段是变量，函数的参数名
#   必须跟它一模一样（写 {name} 就得有个参数叫 name）。
#   不带花括号的是【静态资源】，那种函数不许有参数。
#
#   配套材料（都在本目录）：
#     _demo_path.py              文件那几招：/ 拼接、resolve、is_relative_to
#     _demo_resolve.py           .resolve() 干的三件事（第三件是快捷方式）
#     _demo_resource_example.py  一个完整能跑的 resource 例题
#     _demo_resource_guard.py    越界 URL 一发一发射，看谁穿得过 SDK 那道门
#     _demo_resource_error.py    抛哪种异常，原话才留得住
#     _check_mcp.py ④ 段        验收：本目录的 resource 值不值钱就看它
#   诱饵（专门用来打脸的）：
#     ../secret.txt              在 docs 外面
#     ../docs_bak/秘密.txt        兄弟目录，名字恰好以 docs 开头
#     docs/近路                  junction → docs_bak，字面一个可疑字符都没有
# ═════════════════════════════════════════════════════════════

# 白名单目录：只允许读这个目录底下的东西。
# .resolve() 让它变成绝对路径，好跟后面算出来的路径做比较。
资源目录 = (Path(__file__).parent / "docs").resolve()


@server.resource("file:///docs/{name}")
def read_doc(name: Annotated[str, Field(description="文件名，只写名字不带路径，例如：员工手册摘录.md")]) -> str:
    """读取内部资料库里的一个文件。用户要看资料、说明、清单时使用此工具。"""

    # ── 第一跳：把名字接到目录后面，得到一条"想去哪儿"的路径
    路径 = 资源目录 / name

    # ── 第二跳：让电脑算出这条路径【最终】指向哪儿。
    #    .resolve() 干三件事：相对→绝对 / 算平 . 和 .. / 把快捷方式展开成真身。
    #    ⚠️ 这一步不能省：字符串长什么样不作数，最终落在哪个文件夹才算数 ——
    #    跟 get_weather 那个 date 参数一个道理：判断要用"真的那个值"。
    真实路径 = 路径.resolve()

    # ── 第三跳：白名单 —— 真实路径还落在资源目录里面吗？
    #    is_relative_to 认的是【路径的层级】，不是【字符串的前几个字】：
    #        docs_bak\x.txt 前 4 个字也是 docs，startswith 会被它骗过去，这招不会。
    #
    #    为什么非要自己再写一道（SDK 不是已经把 ../ 挡了吗）：
    #      SDK 那道是【格式检查】——只认字符串长得像不像越界。它【不知道 docs 在哪】，
    #        也不认识 近路 那种 junction（实测 file:///docs/近路 整枪穿过，进到函数里）。
    #      这道是【范围检查】——resolve 完看落点，只有它答得了"在不在门里"。
    #      一句话：上游那把是黑名单（列出可疑形状），你这把是白名单（只放行门里的）。
    if not 真实路径.is_relative_to(资源目录):
        raise ResourceNotFoundError(f"越界：只允许读 docs 目录里的文件，不给读 {name}")

    # ── 第四跳：读出来。读不到要【好好说话】。
    #    ⚠️ 必须抛上面 import 的那个 MCP 异常类：普通异常的原话会被 SDK 吞掉，
    #       客户端只看到 "UnexpectedResourceError: ..."，你的诊断白写。
    #       （所以「文件不存在」和「给的是个目录」都归到 ResourceNotFoundError）
    try:
        内容 = 真实路径.read_text(encoding="utf-8")
    except OSError as e:
        raise ResourceNotFoundError(f"读不到 {name}：{e}") from e

    return 内容


# 自检：
#     .venv\Scripts\python.exe _check_mcp.py     ← ④ 段专验这个 resource
#   它会直接叫 read_doc() 去够 secret.txt / docs_bak/秘密.txt / 近路 ——
#   绕开 URI 那道门，模拟"上游那把锁哪天不在了"，看你自己那把顶不顶用。
#   过线标准：坏路径 5 枪全绿 + 「办不到」那两行是 ✅ 留住了（不是 ❌ 被吞）。
# ═════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════
# 四件套 ③：列目录（tool）
#
# 为什么是 tool 不是 resource —— 别只看"读世界变不变"（列目录也不改
# 世界），看【谁决定去读】：
#     resource = 东西摆在那儿，客户端应用决定什么时候读进来（被动）
#     tool     = 模型自己伸手要 —— "我想看看有什么"（主动）
# 列目录是模型主动想知道的 → tool。
# 反面：read_doc 只能是 resource —— 文件是【预先】摆在 docs/ 里的，
#       模型没得选；"列个清单"是它临时起意。一个是你摆的，一个是它要的。
#
# ⚠️ 注意它身上【没有白名单】—— 因为【它一个参数都没有】。
#    没有输入 → 没有"落点" → 没有越界可言。
#    攻击面就是"别人能往里塞东西的地方"；参数越少，面越小。
# ═════════════════════════════════════════════════════════════
@server.tool()
def list_docs() -> str:
    """列出内部资料库里有哪些文件。用户问「都有哪些资料」「资料库里有什么」时必须调用此工具。"""
    # 这一小段里塞了四件事（_check_mcp_fs.py 的 ② ③ 两节专验它）：
    #   ① iterdir() 给的是【一条队】（generator），不是列表 ——
    #      能 for，不能 len()、不能 [0]，而且【只能走一遍】。
    #      所以别存进名字叫 path 的变量里反复用："路"这个意象会骗你。
    #   ② .name / .is_file() 长在【每个元素】身上，不在那条队身上 —— path.name 会被驳。
    #   ③ 筛子站在 for 里：iterdir() 连目录一起给（docs/近路 就是），
    #      要的是【文件】，所以 is_file() 为 False 的直接跳过。
    #   ④ 空了就 return 一句话 —— 【不是 raise】。
    #      tool 里抛异常，你写的话会被换成干巴巴的 "Error executing tool list_docs"；
    #      连 return 一个异常【对象】也一样丢（实测见 _demo_return_types.py）。
    #      想让模型看见，出口只有一个：return 一个【字符串】。
    result = ""
    for n in 资源目录.iterdir():
        if n.is_file():
            result += f"{n.name}\n"

    if result == "":
        return "资料库为空,没有检索到资料"

    return result


# ═════════════════════════════════════════════════════════════
# 四件套 ④：写（tool）—— 今天的主菜
#
# 落点【不是】docs/（那是只读区，里面躺着员工手册和服务器的正本），
# 是 notes/（可写区，模型的作业本）。两把不同的钥匙。
#
# 四道锁，按顺序立：
#   ① 白名单   —— notes/ 里面的才准写（照抄 read_doc 那三跳，只换目录）
#   ② 已存在   —— 拒绝覆盖，报"办不到"（只增不改 = append-only）
#   ③ 大小上限 —— 挡模型一口气吐几千行（它是唯一"输入端是模型"的文件操作）
#   ④ 写进去   —— encoding="utf-8"，否则中文写成乱码
#
# ⚠️ 顺序有讲究：先把落点算出来、先过白名单，再谈覆盖和大小。
#    跟 read_doc 一样，错误一律 [return 一句"办不到"]，不是 raise ——
#    tool 报错不抛异常，是给模型看的信息（第 4 步学的那条）。
#
# 诱饵（跟 docs/近路 同一个套路）：notes/近路 → docs_bak
#    专打"白名单删了也看不出来"的脸 —— 它字面一个可疑字符都没有，
#    却落到写目录外面。没有它，越界那几枪会被"文件已存在"那道锁顺手拦下，
#    报出来的 ✅ 是【别的锁的功劳】。
# ═════════════════════════════════════════════════════════════
写目录 = (Path(__file__).parent / "notes").resolve()


@server.tool()
def write_note(name: Annotated[str, Field(description="文件名，只写名字不带路径，例如：读书笔记.md")],
               content: Annotated[str, Field(description="要写进文件的正文内容")]) -> str:
    """新建一个笔记文件，把内容写进去。用户说「帮我记下来」「存成文件」时必须调用此工具。
    只能新建，不能覆盖或修改已有文件。"""
    # ★2 第一跳 + 第二跳：落点、然后 resolve() 出真身
    #    （跟 read_doc 一字不差，只把 资源目录 换成 写目录；别省 resolve）
    路径 = 写目录 / name
    真实路径 = 路径.resolve()
    # ★3 第三跳：白名单 —— 落点不在 写目录 里面 → 返回一句"办不到"

    if not 真实路径.is_relative_to(写目录):
        return "办不到,落点不在要写的目录里"
    # ★4 已存在就不写 —— 返回一句"办不到"，把话说明白（只增不改）
    if  真实路径.exists():
        return "办不到,目录里已经存在这个文件"
    # ★5 写进去。⚠️ 写之前还有一道【大小上限】：content 太长就"办不到"，
    #    上限自己定个数（别让模型一口气吐几千行把盘塞满）
    if len(content) >= 上限:
        return "办不到,content过长"

    with open(真实路径, "w", encoding="utf-8") as f:
        f.write(content)
        return "已经写入"



# ⚠️ 守卫必须站在【全文件最后一行代码】。定义在前，开跑在后。
#
#    run("stdio") 是阻塞的：跑到它就进事件循环等客户端，不返回。
#    守卫要是站在工具定义【上面】，下面那些 @server.tool() 一件都登记不上。
#    import 也不是"只看一眼不执行"，它会把整个文件从上到下跑一遍 ——
#    所以同一个文件会有两个答案：
#        直接跑   → __name__ == "__main__"   → 跑到守卫就开跑，下面的全没执行
#        被 import → __name__ == "mcp_server" → 守卫整块跳过，一路跑到底，全登记
#    2026-10-08 实测：守卫摆在中间时，探针说 5 件、真客户端说 1 件。
#    探针绿 ≠ 服务对 —— 探针走的是 import 那条路。
if __name__ == "__main__":
    server.run("stdio")
