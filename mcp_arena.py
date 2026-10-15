"""第 8 步 ②③④：靶场 Server —— 修 bug Agent 的工具集（只读三件 + 精确修改一件 + 跑测试一件）。

它和 `mcp_server.py` 的关系：**同一个 MCP 模式，装了两套不同的能力。**
    mcp_server.py   文档资料柜 —— 白名单是 docs/（只读）和 notes/（只增不改）
    mcp_arena.py    修 bug 靶场 —— 白名单是 arena/tasks/<题号>/（可改，但只在 src/）

为什么不塞进 mcp_server.py（三条，一条比一条硬）：
    ① 语义相反 —— write_note 的铁律是"只增不改"，而修 bug【必须覆盖】src/ 的文件。
    ② 会拖坏 4 个验收脚本 —— _check_mcp_tools.py 记着上次加两件工具时当场假红过。
    ③ 白捡一套验收 —— _check_mcp_fs.py 早就是 sys.argv[1] 可换服务器文件。

跑法（⚠️ 必须带题号 —— 不传就是不知道该守哪道题的门）：
    .venv\\Scripts\\python.exe mcp_arena.py t01_grade_boundary

⚠️ stdio 模式禁止 print()：往 stdout 打一行字就污染协议报文，客户端直接崩。要打印就打 stderr。

验收：_check_arena.py
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from pydantic import Field

# mcp 2.x：FastMCP 已改名 MCPServer（网上 99% 教程还是 1.x 的写法，照抄会 ModuleNotFoundError）
from mcp.server.mcpserver import MCPServer

# ══════════════════════════════════════════════════════════════
# 门立在哪儿 —— 【题号级】，不是 arena 级
#
# ⚠️⚠️ 这条是整套设计里最不能错的一处：
#     arena/_make_tasks.py 里写着【全部三道题的正解】（src_对）。
#     白名单要是开到 arena/ 这一层，模型 read_src("../_make_tasks.py")
#     一次就把答案全读走了 —— 而且读得名正言顺，一个字都不越界。
#
#     所以根必须是 arena/tasks/<题号>/：那台"答案机器"在门外。
#
# ⚠️ 为什么靠【命令行参数】而不是让模型传题号：
#     传题号 = 模型可以自己换一道题去读 —— 那就是又开了一扇门。
#     由启动方钉死，模型连"有别的题"都不知道。
# ══════════════════════════════════════════════════════════════
if len(sys.argv) < 2:
    print("用法: mcp_arena.py <题号>   例如 mcp_arena.py t01_grade_boundary", file=sys.stderr)
    raise SystemExit(2)

题号 = sys.argv[1]
# ⚠️ 本文件就住在 agent-lab/ 根目录，跟 mcp_server.py 并排 ——
#    设计文档 §7 起的接法就是 args=["mcp_arena.py", 题号]，两边一个规格。
#    所以 arena/ 得【从本文件往外走一步】拿，不能拿 __file__ 的 parent 当靶场。
#    （第一次跑就栽在这儿：parent 拿到的是 agent-lab，题目根算成了 tasks/xxx
#      —— 服务直接"没有这道题"退出，客户端那边只看到一句 Connection closed。
#      踩点：报错在最远的地方，病根在最近的地方。）
arena根 = Path(__file__).resolve().parent / "arena"
题目根 = (arena根 / "tasks" / 题号).resolve()

if not 题目根.is_dir():
    print(f"没有这道题：{题目根}", file=sys.stderr)
    raise SystemExit(2)

server = MCPServer("arena")

# 输出上限 —— 这三件的返回值都是【给模型看的】，不是给人看的。
# 不设上限，一个 grep 就能把上下文塞爆（而且白烧 token）。
grep上限行数 = 60
grep每条最长 = 200
列表上限 = 200

# 可写分区白名单 —— 整个题目里【只有这一个子目录】能动。
# ⚠️ 为什么搞成常量：以后要放宽（比如某道题得改 data/）就改这一行，
#    判断逻辑一个字不动 —— 「改值不改比较符」（第 4 步那次的教训）。
可写分区 = "src"

# run_tests 的两个数（都不写死在函数里，理由同上：调它只改这一行）
测试超时秒 = 20       # 卡死护栏。⚠️ 是【护栏】不是【沙箱】—— 见下面 run_tests 那段注释
输出上限字 = 3000     # 一次测试的输出喂给模型的字数上限


# ══════════════════════════════════════════════════════════════
# 安全走目录：一边走、一边筛【落点】，不信任字面路径
#
# ⚠️ 不能只用 iterdir() 就信了。题目目录里完全可能出现一个 junction
#    （mcp_server.py 那边的 docs/近路 就是这么一颗雷）：
#    它字面名字干干净净，一个可疑字符都没有，可落点在门外。
#
#    .resolve() 干的三件事里第三件就是【把快捷方式展开成真身】——
#    展开完再问一句"还在门里吗"，junction 就现形了。
#    判据认的是【层级】，不是【字符串前几个字】。
# ══════════════════════════════════════════════════════════════
def 是垃圾(候选: Path) -> bool:
    """靶场自己的运行残留，不算【题的一部分】。

    ⚠️ __pycache__ / *.pyc 是 run_tests 一跑就会长出来的东西（第 4 刀补的实测：
       跑一次 pytest，src/ 和 tests/ 底下各冒一个 __pycache__）。
       不管它的话，下一轮 list_task 直接给模型端出一堆
       "src/__pycache__/grade.cpython-314.pyc" —— 又吵又费 token，
       而且它会一本正经地去读那个二进制文件。
       点开头的（.pytest_cache 之类）同理。

    ⚠️ 这一件是【第二道】。第一道在 run_tests 里（PYTHONDONTWRITEBYTECODE +
       -p no:cacheprovider：从源头不让它长）。两道都留着 —— 纵深防御的规矩，
       不是"哪道更管用"：哪天别处（_eval.py、手工敲）跑了 pytest，这道还兜着。
    """
    for 段 in 候选.parts:
        if 段 == "__pycache__" or 段.startswith("."):
            return True
    return 候选.suffix == ".pyc"


def 题目内的文件():
    """产出题目目录里【真正落在门内】的文件（绝对路径）。"""
    for 候选 in 题目根.rglob("*"):
        if 是垃圾(候选):
            continue
        try:
            真 = 候选.resolve()
        except OSError:
            continue          # 断掉的链接之类，跳过
        if not 真.is_file():
            continue          # ⚠️ 要的是【文件】：目录（含 junction 目录本身）不算
        if not 真.is_relative_to(题目根):
            continue          # ← junction 漏进来的，在这一行被筛掉
        yield 真


def 相对(真路径: Path) -> str:
    """显示用相对路径。⚠️ as_posix()：屏幕上给正斜杠，模型照抄回来两边都认。"""
    return 真路径.relative_to(题目根).as_posix()


# ══════════════════════════════════════════════════════════════
# ① list_task —— 只给【路径】，不给内容
#
# 为什么不是 resource：resource 是"东西摆在那儿，客户端决定读不读"（被动），
# 而"这题有哪些文件"是模型自己临时起意想知道的 → 主动 → tool。
# （跟 mcp_server.py 里 list_docs 的判据同一条。）
# ══════════════════════════════════════════════════════════════
@server.tool()
def list_task() -> str:
    """列出当前题目里有哪些文件。用户/你需要先知道某道题的文件清单时调用，只返回路径不返回内容。"""
    文件们 = sorted(相对(真) for 真 in 题目内的文件())
    if not 文件们:
        return "题目目录里没有文件"
    return "\n".join(文件们[:列表上限])


# ══════════════════════════════════════════════════════════════
# ② read_src —— 读题目的一个文件
#
# ⚠️ 报错一律【return 一句"办不到"】，不是 raise。
#    tool 里抛异常，你写的话会被换成干巴巴的 "Error executing tool read_src"，
#    模型什么都看不见。（resource 那边才反过来 —— 必须抛 MCP 的异常类。）
#    铁律：错误本身是【给模型看的信息】，不是程序的失败。
#
# ⚠️ tests/ 也允许读 —— 它是【规格】，模型本来就该看见。
#    只读不写：写那条锁在 edit_src（第 3 刀）里，不在这件工具身上。
# ══════════════════════════════════════════════════════════════
@server.tool()
def read_src(path: Annotated[str, Field(
    description="相对题目目录的路径，例如：src/grade.py 或 tests/test_grade.py")]) -> str:
    """读取当前题目里的一个文件（源码或测试）。要看清某个文件写了什么时必须调用此工具，不得凭记忆猜。"""
    if not path.strip():
        return "办不到,path 是空的"

    # 第一跳：拼落点（绝对路径会直接把前面的 题目根 顶掉 —— 正是要拦的东西之一）
    落点 = (题目根 / path).resolve()

    # 第二跳：白名单 —— 落点还在题目目录里吗？（../hidden、绝对路径、junction 全在这一行现形）
    if not 落点.is_relative_to(题目根):
        return f"办不到,只能读当前题目目录里的文件。{path} 的落点跑到题目目录外面去了"

    # 第三跳：得是个【文件】。不存在、或者给的是目录，都归到这里。
    if not 落点.is_file():
        return f"办不到,{path} 不是一个文件（可能不存在，也可能是个目录）"

    try:
        return 落点.read_text(encoding="utf-8")
    except OSError as e:
        return f"办不到,读不到 {path}：{type(e).__name__}: {e}"


# ══════════════════════════════════════════════════════════════
# ③ grep_src —— 在题目里按【子串】搜
#
# 这件工具是给"定位"用的：报错指着 B 函数，你得去代码里搜关键词，
# 才知道该读哪个文件 —— 所以【第二轮读什么，取决于第一轮搜到什么】。
# （判据第一问就靠它成立。）
#
# ⚠️ 走的是同一台 题目内的文件()：junction 那边一样筛掉，
#    不用在这儿重写一遍安全检查 —— 一处写、两处用。
# ══════════════════════════════════════════════════════════════
@server.tool()
def grep_src(pattern: Annotated[str, Field(
    description="要搜索的代码片段或名字，例如：strip_ext、rstrip")]) -> str:
    """在当前题目的源码和测试里按子串搜索（区分大小写），返回「路径:行号: 那一行」。要定位某个名字/写法出现在哪时必须调用此工具。"""
    if not pattern.strip():
        return "办不到,pattern 是空的"
    if len(pattern) > 200:
        return "办不到,pattern 太长了"

    行们 = []
    命中总数 = 0

    for 真 in 题目内的文件():
        try:
            文本 = 真.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue          # 读不了/不是文本，跳过 —— 别为它把整次搜索搞崩
        for 序, 行 in enumerate(文本.splitlines(), 1):
            if pattern in 行:
                命中总数 += 1
                if len(行们) < grep上限行数:
                    行们.append(f"{相对(真)}:{序}: {行.strip()[:grep每条最长]}")

    if 命中总数 == 0:
        return f"没有找到含 {pattern} 的行"

    正文 = "\n".join(行们)
    if 命中总数 > len(行们):
        正文 += f"\n...(还有 {命中总数 - len(行们)} 行没显示)"
    return 正文


# ══════════════════════════════════════════════════════════════
# ④ edit_src —— ⭐ 精确替换，【不是】整文件覆盖
#
# 为什么不做成 write_src(path, content)（三条，一条比一条硬）：
#   ① 安全性 —— 整文件覆盖时"先读一遍"只是【嘴上的礼貌】，模型可以直接糊一份新文件。
#      精确替换要求 old 必须【真实存在于现文件里】→「改之前必须读过」从约定变成代码强制。
#   ② 可度量 —— 每次调用天然是 diff（old 几行 → new 几行）→ 平均改动行数是白捡的数字。
#   ③ 防跑偏 —— 整文件覆盖时它爱顺手重写整段；精确替换从工具形状上就堵死了这条路。
#
# ⚠️ 这道门比 read_src【多三道锁】（前两跳照抄，后面是新的）：
#   ① 目录白名单        —— 落点还在题目目录里（已抄）
#   ② 分区白名单        —— tests/ 只读不动（写测试 = 自己给自己判分）
#   ③ 后缀+已存在白名单 —— 【只放行 src/ 下已存在的 *.py】
#      ⭐ 第三道才是真正干活的那道，前两道都拦不住这些：
#        conftest.py / pytest.ini  → 改收集规则，测试【照样亮绿灯】
#        sitecustomize.py          → Python 启动时自动 import → 在 pytest 进程里任意代码执行（RCE）
#      黑名单列不全这些名字（你永远猜不到它还想到哪个），所以只能反过来【只放行认得的】。
# ══════════════════════════════════════════════════════════════
@server.tool()
def edit_src(
    path: Annotated[str, Field(
        description="要修改的文件，相对题目目录的路径，例如：src/grade.py")],
    old: Annotated[str, Field(
        description="文件里【现在真实存在】的一段原文，必须一字不差（含缩进）。要改动一个函数时，多带几行上下文，避免它出现多次。")],
    new: Annotated[str, Field(
        description="用来替换 old 的新文字。只写要改的那一小段，不要重写整个文件。")],
) -> str:
    """修改当前题目里的一个文件：把 old 这一段原文精确替换成 new。改代码前必须先用 read_src 把文件读出来。"""
    if not path.strip():
        return "办不到,path 是空的"
    if not old:
        return "办不到,old 是空的（旧文字一段都没给，我没法定位要改哪儿）"

    # 第一跳：拼落点（绝对路径会直接把前面的 题目根 顶掉 —— 要拦的正是它）
    落点 = (题目根 / path).resolve()

    # 第二跳：目录白名单 —— 落点还在题目目录里吗？
    if not 落点.is_relative_to(题目根):
        return f"办不到,{path} 的落点跑到题目目录外面去了"

    # ⭐ 分区白名单：只许改 src/，测试只读。
    #    写法是【把白名单的根往下挪一层】：第一道锁问"还在题目里吗"，
    #    这道锁问"还在 src/ 里吗" —— 同一个原语（is_relative_to），只换了比较的基准。
    #    ⚠️ 为什么不用 `落点.relative_to(题目根).parts[0] != "src"`：
    #       ① 落点正好等于题目根时 parts 是空元组 → 取 [0] 会 IndexError（还得再加一个 not 相对段）
    #       ② 拼字符串的写法一眼看不出"这是白名单"，而 is_relative_to 摆在眼前就是在划范围
    #    实测能挡：tests/test_grade.py（改测试=自己给自己判分）、src/../tests/...（resolve 后现形）
    if not 落点.is_relative_to(题目根 / 可写分区):
        return f"办不到,只能改 {可写分区}/ 里的文件。{path} 不在 {可写分区}/ 下（tests/ 是规格，只读不写）"

    # ⭐ 后缀 + 已存在白名单：【只放行 src/ 下已存在的 *.py】
    #    顺序是"先问在不在，再问是什么" —— 两个条件各挡一批，报错话术也就分得清：
    #      exists()  → 挡"在 src/ 里凭空造一个新文件"（conftest.py / sitecustomize.py 全在这一枪倒下）
    #      .suffix   → 挡"往 src/ 塞一个非 .py 的东西"（pytest.ini 这种能改 pytest 行为的也算）
    #    ⚠️ 必须【两道都写】。只写后端那道（后缀）＝ 模型照样能造 conftest.py；
    #       只写前面那道（存在）＝ 哪天某道题的 src/ 里放了数据文件，它就能被改掉。
    #       纵深防御的意思不是"哪道更管用"，是"哪道倒了还有另一道"。
    if not 落点.exists():
        return (f"办不到,{path} 现在不存在。这件工具只改【已有】的文件，不新建"
                f"（免得凭空造出 conftest.py / sitecustomize.py 这类能改变判分行为的东西）")
    if 落点.suffix != ".py":
        return f"办不到,只能改 .py 文件。{path} 不是（pytest.ini 这类能改 pytest 行为的文件一律不许碰）"

    # 第三跳：把原文读出来（读不到就直说，别硬写）
    try:
        原文 = 落点.read_text(encoding="utf-8")
    except OSError as e:
        return f"办不到,读不到 {path}：{type(e).__name__}: {e}"

    # ⭐ 精确替换的两条铁律：old 必须【找得到】，而且必须【只找到一处】
    #    ⚠️ 为什么不许"换第一个"（replace(old, new, 1)）或"全换"（replace(old, new)）：
    #       两种都可能改错地方，而且改完【看不出来】—— 这题的 bug 在 A 函数，
    #       它把 B 函数里长得一样的那行也改了，测试照样绿（B 没人测），等第 7 刀判分才炸。
    #       这里宁可用着难用，也不要它改错：逼它多带上下文 ≈ 逼它【再回去读一遍】。
    次数 = 原文.count(old)
    if 次数 == 0:
        return (f"办不到,old 这段原文在 {path} 里找不到。你确定读过这个文件吗？"
                f"一个字都不能差 —— 空格、缩进、行尾都算。先用 read_src 把文件读出来，从里面【原样复制】要改的那几行")
    if 次数 > 1:
        return (f"办不到,old 在 {path} 里出现了 {次数} 次，我不敢猜你指的是哪一处。"
                f"多带几行上下文（前后各留一行），或者只挑一段【唯一】的给我")

    新文 = 原文.replace(old, new)
    try:
        落点.write_text(新文, encoding="utf-8")
    except OSError as e:
        return f"办不到,写不进 {path}：{type(e).__name__}: {e}"

    # 返回值带上【改了多大一块】—— 这是要报的 6 个数字里"平均改动行数"的原料：
    # 模型自己看得见"我只动了 2 行"，也就更容易保持最小改动。
    # ⚠️ encoding="utf-8" 必须显式写：Windows 上默认编码是 GBK，中文一进去就是乱码/报错。
    return f"已修改 {path}：替换 1 处（{len(old.splitlines())} 行 → {len(new.splitlines())} 行）"


# ══════════════════════════════════════════════════════════════
# ⑤ run_tests —— ⭐ 闭环的那一环
#
# 为什么这一件是【整个项目的分水岭】：
#     只读三件 + edit_src 凑起来，跟"一个能改文件的聊天机器人"没有区别 ——
#     改完照样只能【声称】自己修好了。
#     加上 run_tests，项目里第一次出现了【模型自己不知道、只有跑一下才知道】的东西
#     ——「判据第二问」硬满足 → 多轮是逼出来的，不是设计出来的。
#
# ⚠️⚠️⚠️ 这一件【不是沙箱】。写在最显眼的地方，面试也要自己先说：
#     pytest 会 import src/ 里那些【模型刚写的】代码，而 import 就等于执行。
#     while True 能卡死（所以配了超时）、os.system 能删文件、socket 能往外连。
#     超时是【别卡死】用的护栏，不是【关得住】的边界。
#     现在敢用，是因为：① 只跑我们自己出的题 ② 白名单让模型只碰得到题目目录。
#     真正把它关起来是第 8 刀（Docker）—— 那才是边界。
#
# ⚠️ 只跑 tests/（规格），【绝不跑 hidden/】（判分卷）：
#     判分卷跑给模型看 = 把 private test 摊开 → 它开始针对那几条用例调参（过拟合），
#     最后交付的是"判分卷绿"，不是"真修好了"。
#     正确分工：模型的 run_tests 只跑 tests/；hidden/ 由 _eval.py 在 Agent 收工后自己跑。
#     （= Kaggle 的 public / private split：两份都要跑，但【跑的人不同】。）
# ══════════════════════════════════════════════════════════════
def 留两头(文本: str) -> str:
    """超长就【掐中间、留两头】，不是从尾巴上砍一刀。

    ⚠️ 为什么不出头也不出尾：
       pytest -q 的正文里，【第一条失败的完整 traceback】在最前面（说清哪儿错了，最有用），
       而【最后那行汇总】"1 failed, 3 passed" 在最末尾（说清还剩几条，第二有用）。
       只留头 → 模型永远看不到"还有几条没过"，它会以为就一条，修完这条就收工。
       只留尾 → 得看到最后一条失败才明白第一条错在哪，中间那几条它全靠猜。
       两头都留、中间扔掉 —— 扔掉的正是最不值钱的"第 2~n 条 traceback"。
    """
    if len(文本) <= 输出上限字:
        return 文本
    前段 = 输出上限字 * 2 // 3
    尾段 = 输出上限字 - 前段
    掐掉 = len(文本) - 输出上限字
    return (文本[:前段]
            + f"\n…（中间 {掐掉} 字掐掉了 —— 上面是头几条失败，下面是最后的汇总）…\n"
            + 文本[-尾段:])


@server.tool()
def run_tests() -> str:
    """跑当前题目的测试（tests/ 目录），把 pytest 的输出原样拿回来。改完代码必须调用它验证，不许凭感觉说修好了。"""
    测试目录 = 题目根 / "tests"
    if not 测试目录.is_dir():
        return "办不到,这道题没有 tests/ 目录，没有测试可跑"

    # ⚠️ 这三个环境变量是【必须】的，不是"顺手加的"（都踩过才写的）：
    #    PYTHONDONTWRITEBYTECODE=1 —— 不写 __pycache__
    #        （实测：不设它，跑一次 pytest，src/ 和 tests/ 底下各冒出一个 __pycache__）
    #    PYTHONIOENCODING=utf-8    —— 子进程按 utf-8 往管道里吐字
    #        （管道不是控制台，默认会走 GBK —— 中文一进去就是乱码。
    #          ⚠️ 这条是有【验收证据】的：坏版验收里把它去掉之后，
    #             子进程按 GBK 吐、我们按 utf-8 收 —— 报错里的中文全成了乱码，
    #             "盘上坏了它报的也跟着坏"那一枪当场变红。模型看乱码照样能瞎猜，
    #             但它猜的是"哪里错了"，这一步就不该让它猜。）
    #    PYTHONUTF8=1              —— 连它自己读源码也按 utf-8
    #    ⚠️ 前两个治的是【我们这边收得到什么】，第三个治的是【它那边读得到什么】。
    #       只设一个，另一边照样炸。
    环境 = os.environ.copy()
    环境["PYTHONDONTWRITEBYTECODE"] = "1"
    环境["PYTHONIOENCODING"] = "utf-8"
    环境["PYTHONUTF8"] = "1"

    # ⚠️ 命令里每一段都在挡一件具体的事，少一段就漏一种：
    #    sys.executable  —— 用【起这个 server 的那个解释器】，不是 PATH 上碰运气的那个
    #                       （换台机器跑时，PATH 上的 pytest 可能属于另一个 Python，
    #                         那边没装被测的依赖；sys.executable 跟 server 同生共死）
    #    -m pytest       —— 当模块跑，不用去找 pytest.exe
    #    tests           —— ⭐ 只跑 tests/。【这一位绝对不能省】：
    #                       省了 pytest 就从 cwd 往下全收集 ——
    #                       src/ 里但凡被塞进一个 test_*.py，也会被一起跑。
    #                       （自己写的测试给自己判分 = 自己给自己发及格证。）
    #                       顺带：hidden/ 在题目目录【外面】，本来就不在 cwd 底下 ——
    #                       但"我记得它在外边"不算安全，靠的是参数，不是记忆。
    #    -q              —— 少打点没用的（有用的都还在）
    #    --color=no      —— 别把 ANSI 颜色码喂进模型上下文：它读不了，还白烧 token
    #    -p no:cacheprovider —— 不写 .pytest_cache
    #        （⚠️ 实测：它落的地方是【rootdir】= agent-lab/ 根目录，
    #          不是题目目录 —— 所以这条不加，脏的是【仓库根】，会被 git 看见。
    #          两个"不写"管的是两个地方，别以为一条顶两条。）
    命令 = [sys.executable, "-m", "pytest", "tests",
            "-q", "--color=no", "-p", "no:cacheprovider"]

    try:
        结果 = subprocess.run(命令, cwd=题目根, capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                            env=环境, timeout=测试超时秒)
    except subprocess.TimeoutExpired as e:
        # ⚠️ 超时这里【必须】给模型一句人话，而且要点明"多半是死循环"：
        #    不然它只看到"失败了"，会回去乱改断言 —— 而真正的病根是它自己写的那个循环。
        #    e.stdout 是掐之前已经吐出来的那半截（可能只有几十个字）—— 有就带上。
        半截 = e.stdout or ""
        if isinstance(半截, bytes):          # ⚠️ text=True 时它是 str，但不赌这个承诺
            半截 = 半截.decode("utf-8", "replace")
        # ⚠️ 掐死时【经常一个字都没有】—— 实测（t01 上塞 while True）：
        #    e.stdout 是空串。因为 pytest 是攒着一次性吐的，卡在 import 阶段时
        #    它连第一个报告都没开始写，管道里当然什么都没有。
        #    "空输出"对模型来说是【没有信息】，所以这里必须替它把这句话补上，
        #    否则它只知道"失败了"，会跑去乱改断言，而病根是它自己写的死循环。
        if 半截.strip():
            尾巴 = f"\n------ 掐之前它已经吐出来的 ------\n{留两头(半截)}"
        else:
            尾巴 = ("\n（它一个字都没吐出来 —— 多半是卡在 import 阶段："
                    "pytest 还没轮到报错，就被你的代码堵在门口了。"
                    "先去 src/ 里找【模块级】的死循环 / 阻塞调用。）")
        return (f"办不到,测试跑了 {测试超时秒} 秒还没结束，我把它掐了。\n"
                f"最常见的是【死循环 / 卡住】——比如凑答案写了 while True，"
                f"或者某个函数在边界值上永远不收敛。\n"
                f"先回去读你自己刚改的那段代码，别急着改测试。{尾巴}")
    except OSError as e:
        return f"办不到,测试进程起不来：{type(e).__name__}: {e}"

    # pytest 把两路输出分开吐：正常报告走 stdout，pytest 自己的故障/警告走 stderr。
    # ⚠️ 只收 stdout 会漏掉"pytest 自己崩了"这一类 —— 那种时候 stdout 是空的，
    #    模型会拿到一句空话，然后当成"没问题"。
    输出 = (结果.stdout or "") + (结果.stderr or "")
    if isinstance(输出, bytes):
        输出 = 输出.decode("utf-8", "replace")

    # 退出码翻译成人话 ——「1」和「5」对模型下一步该干什么，含义完全不同：
    #    1 = 有测试没过（正常，接着修）
    #    5 = 一条都没收集到（不正常：测试被删了？收集规则被改了？）
    #    区分不开，模型就会把"没跑起来"当成"跑过了没事"。
    码 = 结果.returncode
    判词 = {
        0: "全绿 —— 这道题的测试全过了",
        1: "有测试没过",
        2: "被中途打断",
        3: "pytest 自己出错了（⚠️ 不等于测试没过）",
        4: "pytest 命令行用错了（这是我们这个工具自己的 bug）",
        5: "一条测试都没收集到（tests/ 里还有测试文件吗？）",
    }.get(码, f"退出码 {码}（pytest 没定义过的码）")

    正文 = 留两头(输出.strip()) if 输出.strip() else "（一句话都没输出）"

    # ⚠️ 这行抬头【必须从 命令 拼出来】，不许手写成一句说明。
    #    第一版就是手写的 —— 坏版验收时把 "tests" 这一位去掉了（裸跑），
    #    可抬头还在照念老台词 "$ python -m pytest tests …"，
    #    于是"工具实际干了什么"和"它告诉模型自己干了什么"对不上。
    #    自报家门的东西一旦是手写的，它就一定会过期 —— 过期的那天没人发现。
    抬头 = "$ python" + "".join(f" {段}" for 段 in 命令[1:])

    return (f"退出码 {码}：{判词}\n"
            f"{抬头}\n"
            f"------ pytest 输出 ------\n{正文}")


# ⚠️ 守卫必须站在【全文件最后一行代码】。定义在前，开跑在后。
#    守卫要是站在工具定义【上面】，下面那些 @server.tool() 一件都登记不上 ——
#    实测过：探针说 5 件、真客户端说 1 件（探针走 import 那条路，守卫整块跳过）。
#    ⚠️ 本文件还有第二道：题目根 是在 import 期就算好的，所以【带不带题号】
#       这件事在 import 那一刻就决定了。_probe 之类的脚本 import 本文件，
#       得自己先往 sys.argv 里塞个题号，否则连 import 都过不去。
if __name__ == "__main__":
    server.run("stdio")
