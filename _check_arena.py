"""第 8 步 ②③④ 验收：靶场 Server 的五件工具真的守住门了吗？

⚠️ ⑦ 节（第 4 刀加的）判据跟前六节【不一样】，别混：前六节判"门挡住了没"，
   ⑦ 节判"它说的是不是盘上真跑出来的结果" —— 盘一变结论必须跟着变，盘一还原必须跟着回。
   （那一节是本项目第一次出现【模型自己不知道、只有跑一下才知道】的东西。）

脚本亲爹是 _check_mcp_fs.py —— 套路整个照搬：
    起【真进程】+ stdio 说话，不走 import。
    理由一样：这三件的价值全在"真话真说"上 ——
        list_task 要真去数磁盘上有什么
        read_src 要真读出文件内容
        grep_src 要真去翻每一行
    绕开 SDK 直接叫函数，等于把"跨进程还灵不灵"跳过去了。
（_check_mcp_fs.py:41 早就是 sys.argv[1] 可换服务器文件 —— 那把尺子本来就是照"要复用"设计的。）

═══════════════════════════════════════════════════════════════
⚠️⚠️ 这份验收比上一份【狠】，因为靶场里有个东西比 docs/ 金贵得多：
     arena/_make_tasks.py 里写着【全部三道题的正解】。
     它要是在门外被读走，这个 Agent 项目当场作废 —— 而且读得名正言顺。
     所以下面专门有一枪打它。

⚠️ 判据铁律（照抄上一份，一条没改）：
    ① 「挡住」的唯一判据是【秘密内容没出现】，不是 is_error、不是颜色。
       按我们给的骨架，挡住是 `return 一句"办不到"` —— 那是【正常返回】。
       拿 is_error 当判据，它填对了反而报 ❌。
    ② 工具【压根没跑起来】时秘密当然也没出现 —— 会白送一堆假 ✅。
       所以先打三枪【该成的】，它成了才证明工具跑起来了，后面的 ✅ 才算数。
    （_check_mcp_fs.py 里"先探一枪"那段踩过的坑，这里用"三枪合法读"来顶。）

⚠️ 本脚本会【临时造一个 junction】当靶子（tests/近路 → arena/hidden/<题号>），
   跑完【必拆】，拆完还要回头验一次判分卷还在不在（见 finally 那段）。
   为什么要临时造：junction 进 Git 很脏（会被当软链存，别人 clone 下来就废了），
   而这个仓库是要上 GitHub 当作品集的。
═══════════════════════════════════════════════════════════════

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _check_arena.py
    .venv\\Scripts\\python.exe _check_arena.py mcp_arena.py t03_filename_suffix
"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# 默认验 mcp_arena.py + 第 1 题。命令行可换（题号要换才能验 t03 那道传递式的）。
服务器文件 = sys.argv[1] if len(sys.argv) > 1 else "mcp_arena.py"
题号 = sys.argv[2] if len(sys.argv) > 2 else "t01_grade_boundary"

本目录 = Path(__file__).resolve().parent
靶场 = 本目录 / "arena"
题目根 = (靶场 / "tasks" / 题号).resolve()
判分目录 = (靶场 / "hidden" / 题号).resolve()

启动参数 = StdioServerParameters(command=sys.executable, args=[服务器文件, 题号])

# 题面要求的文件，从盘上数（不写死 —— 换一道题这脚本还能用）
源文件们 = sorted((题目根 / "src").glob("*.py")) if (题目根 / "src").is_dir() else []
测试文件们 = sorted((题目根 / "tests").glob("*.py")) if (题目根 / "tests").is_dir() else []
判分卷们 = sorted(判分目录.glob("*.py"))
判分卷 = 判分卷们[0] if 判分卷们 else None

# 两颗"秘密标记" —— 只要它们出现在返回文本里，就是漏了。
秘密判分 = "ARENA_SRC"        # 判分卷抬头里的独有字符串，可见文件里一个字都没有
秘密答案 = "removesuffix"     # 出题机里 t03 的正解写法；盘上只有 _make_tasks.py 有它

junction链接 = 题目根 / "tests" / "近路"
junction目标 = 判分目录

# ── ⑦ 节要用的两个上限（⚠️ 写死在尺子这边，不 import 服务器那边的常量：
#    尺子要能在【服务器的常量被改坏】的时候照样报红，拿它自己的数当依据就废了）
超时上限秒 = 30        # 服务器那边是 20；这条是"必须在 30 秒内返回"的外框



def 取文本(结果):
    """CallToolResult 的 content 是一串【内容块】，不是字符串 —— 自己拼回来。"""
    块们 = 结果.content or []
    return "".join((getattr(b, "text", None) or "") for b in 块们)


def 是崩溃(文本):
    """SDK 的兜底话术。出现它 = 工具【抛异常了】，不是好好说了句"办不到"。

    两种都要当"没跑起来"处理 —— 它们的秘密也没漏，
    但那是【没走完】，不是【被拦下】。这两种绝不能混。
    """
    文本 = 文本.strip()
    return 文本.startswith("Error executing tool") or "NotImplementedError" in 文本


def 报(ok, 说明, 细节=""):
    print(f"  {'✅' if ok else '❌'} {说明}")
    if 细节:
        print(f"       {细节}")
    return ok


def 毛病(ok, 话):
    """❌ 的时候才把"哪里坏了"这行拿出来；✅ 的时候一个字都不打。

    ⚠️ 为什么单独立一个小函数：第一版我把 🔴 那句【直接当参数传】，
       结果 ✅ 旁边也挂着一行红字"🔴 漏了" —— 跑完一屏花花绿绿，
       真出 ❌ 的那条反而找不着了。细节必须跟着结论走，不能跟着代码走。
    """
    return "" if ok else 话


def 漏了吗(文本):
    """返回命中的秘密标记（没漏就是 None）。

    ⚠️ 只对【read_src】用。grep_src 别用这个 —— 见 有命中() 上面那段。
    """
    for 标记 in (秘密判分, 秘密答案):
        if 标记 in 文本:
            return 标记
    return None


def 有命中(文本):
    """grep_src 的返回里有没有【真命中行】（形状：路径:行号: 那一行）。

    ⚠️⚠️ grep 这一节【不能】拿"标记没出现"当判据（第一版就这么写的，当场假红两枪）：
       工具会把 pattern 原样回显 —— 它答的是「没有找到含 ARENA_SRC 的行」，
       这句话里【当然有】ARENA_SRC。于是工具答得越准，我的尺子越报"漏了"。
       这就是 _check_mcp_fs.py:114 记过的那条坑（"找子串"当判据），换了个工具又踩一次。

       能真漏走的东西只有【命中行】。所以就查命中行：一条都没有 = 没漏。
    """
    return any(re.match(r"^\S.*?:\d+: ", 行) for 行 in 文本.splitlines())


def 去掉耗时(文本):
    """把 pytest 汇总行里的 "in 0.06s" 抹成 "in Xs"。

    ⚠️ 为什么非抹不可：⑦ 节要拿【两次 run_tests 的输出】逐字比对（证明它没记缓存、
       没留烂摊子）。可那行耗时两次必然不一样 —— 不抹掉，比对照样红，
       而且红得毫无意义（"差在 0.01 秒"这条信息对谁都没用）。
       这是"比对文本"这一类判据的通病：得先把【本来就该变的东西】摘出去。
    """
    return re.sub(r"\bin \d+(?:\.\d+)?s\b", "in Xs", 文本)


def 跑了多少条(文本):
    """从 pytest 汇总行里数出【它一共收了几条测试】。

    ⚠️ 汇总行的形状就那几种："1 failed, 3 passed in 0.06s" / "4 passed in 0.06s" /
       "1 error in 0.13s"。把各段数字加起来就是收集到的条数 ——
       拿它跟【可见测试文件里的 test_ 函数个数】比，就能反过来验
       "它跑的到底是哪一批"。这比"名字没出现"结实：名字能被改，条数改不了。

    ⚠️ 只认【最后一行】候选，别把整篇的数字加起来：
       收集失败那类输出里，同一句话会印两遍 ——
       "!!!! 1 error during collection !!!!" 和 "1 error in 0.13s"，
       全加一遍就把 1 条算成 2 条（第一版正是这么错的，当场看见"它跑了 2 条"）。
       优先挑【带耗时】的那一行，因为那才是 pytest 的最后一句总结。
       （假设：它排在 warnings summary 后面。要是哪天 pytest 改了排版，
         这里有专门的判据会红 —— 到时候回来看这一个函数。）
    """
    候选 = [行 for 行 in 文本.splitlines()
           if re.search(r"\b\d+ (?:failed|passed|error|errors|deselected)\b", 行)]
    if not 候选:
        return 0
    带耗时 = [行 for 行 in 候选 if re.search(r"\bin \d+(?:\.\d+)?s\b", 行)]
    末尾 = (带耗时 or 候选)[-1]
    return sum(int(n) for n in re.findall(r"(\d+) (?:failed|passed|error|errors|deselected)", 末尾))


def 残留清单(根):
    """某个目录下面现在有哪些运行残留（__pycache__ 目录 + 散落的 .pyc）。

    ⚠️ 两处【都要看】，因为它们归两个不同的开关管，而且我们第一版只看了题目根：
       · 题目根     —— Python 把 __pycache__ 写在【源码旁边】。→ PYTHONDONTWRITEBYTECODE 管它
       · agent-lab 根 —— .pytest_cache 落在 pytest 认定的 rootdir 上。→ -p no:cacheprovider 管它
       · 判分目录   —— ⭐ 也是今天才补上的：它【在题目根外面】，
                       "扫题目根"这条判据再怎么仔细也看不见它。
                       当场抓到的现场：跑过坏版之后，hidden/<题号>/ 底下留了个 .pyc ——
                       它不是这一轮写的，可它就在那儿。
                       （老坑新踩法：判据的【范围】就是判据的眼睛，范围外的东西它一件都看不见。
                         跟白名单那件事同源 —— 门开多大，你就只看得见多大。）
    """
    # ⚠️ 数的口径要跟 扫残留() 一致：一个 __pycache__ 目录算【一件】，不数它肚子里的文件。
    #    （第一版按 rglob("*") 数，__pycache__ 和它里面的 .pyc 各算一件 ——
    #     "地上有 5 件、扫掉 3 件"这种数字，看的人第一反应是"没扫干净"。）
    件 = [p.relative_to(根).as_posix() + "/" for p in sorted(根.rglob("__pycache__"))
        if p.is_dir()]
    件 += [p.relative_to(根).as_posix() for p in sorted(根.rglob("*.pyc"))
         if "__pycache__" not in p.parts[:-1]]        # 散落在别处的 .pyc
    return 件


def 扫残留(根):
    """把 [根] 下面【上一轮留下的】残留扫掉，返回扫掉了什么。

    ⚠️ 为什么 ⑦ 节开头非扫不可 —— 这是双跑当场抓到的第二种假红：
       先跑坏版 C（它把 PYTHONDONTWRITEBYTECODE 那几个开关摘了，在题目目录里留下一堆 __pycache__），
       紧接着跑真版 —— 真版自己一个字都没写，却【踩在上一轮的尸体上】报了 ❌。
       这和 10-12 那次"收摊写在 else 里 → 尸体留给下一枪亮【假绿灯】"是同一族的，
       只是这次尸体让下一枪亮了【假红】。
       假红假绿都不算数 —— 判据看不见"这东西是谁弄的"。
       所以：清地必须在【这一轮开工之前】，判据只对这一轮负责。
    """
    扫掉 = []
    for 候选 in list(根.rglob("*")):
        if 候选.name == "__pycache__" and 候选.is_dir():
            扫掉.append(候选.relative_to(根).as_posix())
            shutil.rmtree(候选, ignore_errors=True)
        elif 候选.suffix == ".pyc" and 候选.is_file() and "__pycache__" not in 候选.parts[:-1]:
            # ⚠️ 只数【散落在别处】的 .pyc —— 肚子里的那些跟着目录一起没了，
            #    再数一遍就跟 残留清单() 的口径对不上（见那个函数里的注释）。
            扫掉.append(候选.relative_to(根).as_posix())
            候选.unlink(missing_ok=True)
    return 扫掉


def 扫缓存目录():
    """扫掉 agent-lab 根那个 .pytest_cache（它不属于任何一道题，单独管）。"""
    缓存 = 本目录 / ".pytest_cache"
    if 缓存.exists():
        shutil.rmtree(缓存, ignore_errors=True)
        return True
    return False


def 一地残留():
    """开工前 + 收尾时统一问的这一句：三处加起来现在有多少残留。"""
    件 = [f"题目根：{x}" for x in 残留清单(题目根)]
    件 += [f"判分目录：{x}" for x in 残留清单(判分目录)]
    if (本目录 / ".pytest_cache").exists():
        件.append(".pytest_cache（在 agent-lab 根目录，题目外面）")
    return 件


def 扫干净():
    """三处一起扫，返回扫掉的清单。"""
    扫掉 = [f"题目根：{x}" for x in 扫残留(题目根)]
    扫掉 += [f"判分目录：{x}" for x in 扫残留(判分目录)]
    if 扫缓存目录():
        扫掉.append(".pytest_cache（在 agent-lab 根目录）")
    return 扫掉


async def 叫工具(会话, 名字, 入参):
    结果 = await 会话.call_tool(名字, 入参)
    return 结果, 取文本(结果)


# ══════════════════════════════════════════════════════════════
# junction 的建 / 拆
# ══════════════════════════════════════════════════════════════
def 建junction():
    """cmd /c mklink /J —— 造目录联结（不需要管理员权限）。"""
    结果 = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction链接), str(junction目标)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return junction链接.is_dir(), (结果.stdout or "") + (结果.stderr or "")


def 拆junction():
    """⚠️ 拆【链接本身】，绝不动目标。

    junction 上调 rmdir 走的是 Windows 的 RemoveDirectory ——
    删的是那个重解析点，不是它指向的目录树。这是 junction 和拷目录的区别。
    但"我以为的 Windows 行为"不值得拿判分卷去赌，所以拆完必回头验（见下面的断言）。
    """
    if not junction链接.exists():
        return True
    try:
        os.rmdir(junction链接)
    except OSError:
        subprocess.run(["cmd", "/c", "rmdir", str(junction链接)],
                       capture_output=True, text=True)
    return not junction链接.exists()


async def main():
    全绿 = True

    print("=" * 66)
    print(f"靶场 Server 验收 —— 题号 {题号}")
    print(f"  题目根  {题目根}")
    print(f"  判分卷  {判分卷}")
    print("=" * 66)

    if not 题目根.is_dir():
        print(f"❌ 没有这道题：{题目根}")
        return 1
    if 判分卷 is None:
        print(f"❌ 判分目录里没有试卷：{判分目录}")
        return 1

    # ── 先把 junction 靶子摆上
    建成, 回话 = 建junction()
    print(f"\n[junction 靶子] {junction链接}  ->  {junction目标}")
    print(f"  {'已就位' if 建成 else '没建成：' + 回话.strip()}")

    # ── ⑥ 节的现场（在 try 之前先摆好、先算好）
    # ⚠️ 为什么不在 try 里面现算：finally 里要【还原正本 + 拔临时靶子】——
    #    要是 ⑧ 之前在别处就抛了，finally 里这些名字得已经存在，否则掩盖真病的是一个 NameError。
    正本 = 源文件们[0] if 源文件们 else None
    正本相对 = 正本.relative_to(题目根).as_posix() if 正本 else ""
    正本原样 = 正本.read_text(encoding="utf-8") if 正本 else ""
    临时靶子 = 题目根 / "src" / "临时靶子.txt"

    测试文件 = 测试文件们[0] if 测试文件们 else None
    测试原样 = 测试文件.read_text(encoding="utf-8") if 测试文件 else ""
    测试行 = next((行 for 行 in 测试原样.splitlines() if 行.strip().startswith("def ")), "")

    判分原样 = 判分卷.read_text(encoding="utf-8")
    判分行 = next((行 for 行 in 判分原样.splitlines() if 行.strip().startswith("def ")), "")

    # ── ⑦ 节的现场
    # ⚠️ 也摆在 try 外面：陷阱文件要能被 finally 拔掉，名字得先存在。
    陷阱测试 = 题目根 / "src" / "test_陷阱.py"          # 专打"pytest 不带参数"那种实现
    陷阱名字 = "test_绝对不该被跑到的陷阱"
    可见函数们 = re.findall(r"^def (test_\w+)", 测试原样, re.M)
    隐藏函数们 = re.findall(r"^def (test_\w+)", 判分原样, re.M)

    try:
        async with stdio_client(启动参数) as (读, 写):
            async with ClientSession(读, 写) as 会话:
                握手 = await 会话.initialize()
                print(f"\n连上了：{握手.server_info.name}\n")

                工具们 = await 会话.list_tools()
                名字们 = {t.name for t in 工具们.tools}

                # ─────────────────────────────────────────────
                print("=" * 66)
                print("① 登记情况")
                print("=" * 66)
                print(f"  tool  {len(工具们.tools)} 件：{sorted(名字们)}")
                # ⚠️ 这一句查的是【这个 server 恰好装了哪几件】——
                #    两个 server 的工具名单最后会被合成一个 set，多一件少一件都出事。
                #    第 3 刀加了 edit_src、第 4 刀加了 run_tests → 名单跟着长
                #    （这里必须同步改，否则当场假红 —— 每加一件工具都要回来改这一行）
                全绿 &= 报(名字们 == {"list_task", "read_src", "grep_src", "edit_src", "run_tests"},
                          "恰好五件（不多不少 —— 多出来的会被客户端当成靶场能力）",
                          f"实际：{sorted(名字们)}")

                # ─────────────────────────────────────────────
                print()
                print("=" * 66)
                print("② list_task —— 它数得对吗？")
                print("=" * 66)
                结果, 文本 = await 叫工具(会话, "list_task", {})
                print(f"  它说：\n{文本.strip()}\n")
                if 是崩溃(文本):
                    全绿 = False
                    print("  ⏭  崩溃了，后面几节跳过")
                    return 1

                # ⚠️ 判据是【路径】而不是文件名：清单上写 "grade.py" 也得算 ❌，
                #    因为模型下一句就得拿这个字符串去 read_src，路径得能直接用。
                for f in 源文件们 + 测试文件们:
                    期望 = f.relative_to(题目根).as_posix()
                    全绿 &= 报(期望 in 文本, f"清单里有 {期望}")
                全绿 &= 报(str(题目根) not in 文本, "端出来的是【相对路径】，不是绝对路径")
                全绿 &= 报("近路" not in 文本,
                          "近路 不在清单里（它是 junction 目录，不是文件）")
                全绿 &= 报("__pycache__" not in 文本 and ".pyc" not in 文本,
                          "__pycache__ / .pyc 没混进清单（跑过测试的残留，不是题的一部分）")
                全绿 &= 报("hidden" not in 文本, "判分卷的路径没出现在清单里")

                # ─────────────────────────────────────────────
                print()
                print("=" * 66)
                print("③ read_src 合法三枪 —— 先证明【工具真的跑起来了】")
                print("=" * 66)
                # ⚠️ 这三枪是整份验收的地基：它们要是绿的，
                #    下面所有"没漏"才说明【是拦住，不是没跑】。
                试读 = [(f, f.relative_to(题目根).as_posix()) for f in 源文件们 + 测试文件们]
                if not 试读:
                    全绿 = False
                    print("  ❌ 盘上没找到可读的文件，没法验")
                for f, 相对路径 in 试读:
                    结果, 文本 = await 叫工具(会话, "read_src", {"path": 相对路径})
                    盘上 = f.read_text(encoding="utf-8")
                    全绿 &= 报(文本 == 盘上, f"读 {相对路径} → 内容与磁盘一字不差",
                              f"拿到 {len(文本)} 字，盘上 {len(盘上)} 字"
                              if 文本 != 盘上 else "")

                # 合法但"绕"的路径不该被误伤 —— 白名单认【落点】，不认字符串长相
                绕路 = 源文件们[0].relative_to(题目根).as_posix() if 源文件们 else None
                if 绕路:
                    绕 = f"src/../{绕路}"
                    结果, 文本 = await 叫工具(会话, "read_src", {"path": 绕})
                    全绿 &= 报(文本 == 源文件们[0].read_text(encoding="utf-8"),
                              f"绕路 {绕} → 照读（resolve 后还在门里，就不该拦）",
                              f"它说：{文本.strip()[:80]!r}")

                # ─────────────────────────────────────────────
                print()
                print("=" * 66)
                print("④ read_src 越界 —— 一枪一枪打")
                print("=" * 66)
                print("  ⚠️ 判据是【金贵的东西没吐出来】，不是它说了什么。两道一起判：")
                print(f"     ① 秘密标记没出现：{秘密判分!r}（判分卷独有） / {秘密答案!r}（出题机里的正解）")
                print("     ② 靶子文件的正文没露头（更结实 —— 以后加题不用维护标记表）\n")

                隐藏名 = 判分卷.name
                答案机 = 靶场 / "_make_tasks.py"

                # 隔壁那道题 —— 用来验白名单是【题号级】还是【tasks 级】。
                # ⚠️ 别小看这一枪：模型修完这题，下题是同一台 server 换个题号起的，
                #    要是门开在 tasks/ 这一层，它就能把【别的题（连同已被改好的代码）】
                #    当参考书翻 —— 那就不是修 bug 了，是抄。
                邻题目录 = next((d for d in sorted((靶场 / "tasks").iterdir())
                              if d.is_dir() and d != 题目根), None)
                邻题 = (sorted((邻题目录 / "src").glob("*.py"))[0]
                       if 邻题目录 and (邻题目录 / "src").is_dir() else None)

                # ⚠️⚠️ 路径的【层数】必须数准，不然这一枪打的是空气。
                #    题目根 = arena/tasks/<题号>/
                #      往上一级 = arena/tasks/          ← 这儿没有任何东西
                #      往上两级 = arena/                ← 判分卷(hidden/) 和出题机(_make_tasks.py) 在这儿
                #    原来三条写的是"跳一级"，落点全是 arena/tasks/hidden/…（不存在）——
                #    门就算拆了也照样"没读到"，白送 ✅。这类哑弹是"靶子挑错"家族又一例。
                枪们 = [
                    ("往上跳两级（判分卷所在层）", f"../../hidden/{题号}/{隐藏名}", 判分卷),
                    ("再往上跳（跳出 arena 整个靶场）", f"../../../{隐藏名}", None),
                    ("反斜杠跳两级", f"..\\..\\hidden\\{题号}\\{隐藏名}", 判分卷),
                    ("绝对路径", str(判分卷), 判分卷),
                    ("走 junction 近路", f"tests/近路/{隐藏名}", 判分卷),
                    (f"⭐ 直奔出题机（跳两级）", "../../_make_tasks.py", 答案机),
                    ("不存在的文件", "src/这道题里没有这个文件.py", None),
                    ("给的是个目录", "src", None),
                ]
                if 邻题 is not None:
                    枪们.append(("隔壁那道题", f"../{邻题目录.name}/src/{邻题.name}", 邻题))

                for 说明, 坏路, 靶子 in 枪们:
                    结果, 文本 = await 叫工具(会话, "read_src", {"path": 坏路})
                    崩 = 是崩溃(文本)
                    漏标 = 漏了吗(文本)
                    # ⚠️ 第二道判据（拿【内容】比，不靠那一两个标记）：
                    #    成功的 read_src 会原样吐回文件正文 —— 正文一露头就是漏了，
                    #    这比"猜几个关键词"结实得多，以后加题也不用维护标记表。
                    漏文 = bool(靶子) and 靶子.read_text(encoding="utf-8")[:60] in 文本
                    ok = (not 崩) and (漏标 is None) and (not 漏文) and bool(文本.strip())
                    全绿 &= 报(ok, f"【越界·{说明}】{坏路} → 没读到",
                              f"💥 它抛异常了：{文本.strip()[:100]!r}" if 崩
                              else (f"🔴【漏了！】返回里出现了 {漏标!r}" if 漏标
                                    else (f"🔴【漏了！】正文都吐出来了：{文本.strip()[:80]!r}" if 漏文
                                          else f"它说：{文本.strip()[:90]!r}")))

                # ─────────────────────────────────────────────
                print()
                print("=" * 66)
                print("⑤ grep_src —— 搜得对，也搜得出界吗？")
                print("=" * 66)
                # 先搜一个【一定存在】的：源文件里第一个 def 的名字
                关键词 = None
                if 源文件们:
                    for 行 in 源文件们[0].read_text(encoding="utf-8").splitlines():
                        if 行.startswith("def "):
                            关键词 = 行[4:].split("(")[0].strip()
                            break
                if 关键词:
                    结果, 文本 = await 叫工具(会话, "grep_src", {"pattern": 关键词})
                    print(f"  搜 {关键词!r} →\n{文本.strip()}\n")
                    前缀对 = f"{源文件们[0].relative_to(题目根).as_posix()}:" in 文本
                    # ⚠️ 判据：得是 "路径:行号: ..." 的形状，光返回个"找到了"没用
                    全绿 &= 报(前缀对 and 有命中(文本),
                              f"搜得到，且格式是「路径:行号: 那一行」",
                              "" if 前缀对 else f"它说：{文本.strip()[:90]!r}")
                    全绿 &= 报(漏了吗(文本) is None, "结果里没有判分卷/出题机的痕迹")

                # 判分卷独有的标记 —— 门要是漏的，这一枪必然命中
                结果, 文本 = await 叫工具(会话, "grep_src", {"pattern": 秘密判分})
                print(f"  搜 {秘密判分!r}（只有判分卷里有）→ {文本.strip()!r}")
                全绿 &= 报(not 有命中(文本),
                          "搜不到判分卷里的东西（junction 摆着也一样搜不到）",
                          f"🔴【漏了】它回了一堆命中行：{文本.strip()[:90]!r}" if 有命中(文本) else "")

                结果, 文本 = await 叫工具(会话, "grep_src", {"pattern": 秘密答案})
                全绿 &= 报(not 有命中(文本),
                          "搜不到出题机里的正解写法",
                          f"🔴【漏了】它回了一堆命中行：{文本.strip()[:90]!r}" if 有命中(文本) else "")

                结果, 文本 = await 叫工具(会话, "grep_src", {"pattern": "zzz_绝对不存在的东西_zzz"})
                全绿 &= 报(漏了吗(文本) is None and not 是崩溃(文本),
                          "搜不存在的词 → 好好说了句「没找到」，不是抛异常",
                          f"它说：{文本.strip()[:90]!r}")

                结果, 文本 = await 叫工具(会话, "grep_src", {"pattern": "   "})
                全绿 &= 报(not 是崩溃(文本),
                          "空 pattern → 好好说了句「办不到」，不是抛异常",
                          f"它说：{文本.strip()[:90]!r}")

                # ─────────────────────────────────────────────
                print()
                print("=" * 66)
                print("⑥ edit_src —— 精确替换，外加三道新锁")
                print("=" * 66)
                print("  ⚠️ 这一节只有一条判据：【副作用有没有真发生】——")
                print("     拦住 = 靶子原封不动；该成的 = 盘上真变了。")
                print("     （拿 is_error、或拿它说了什么当判据都不算数：10-10 那次这么写，白送一排 ✅。）\n")

                if 正本 is None:
                    全绿 = False
                    print("  ❌ 盘上没有 src/*.py，这一节验不了")
                else:
                    # ═══ 地基枪：它真会写盘吗？═══
                    # ⚠️ 这一枪不绿，下面所有"没改到"都不作数 —— 工具压根没跑起来，
                    #    靶子当然没被动过，那是【没走完】，不是【被拦下】。
                    def行 = next((行 for 行 in 正本原样.splitlines()
                                if 行.strip().startswith("def ")), None)
                    if not def行:
                        全绿 = False
                        print("  ❌ 正本里没有 def 行，挑不出唯一片段来改")
                    else:
                        新行 = def行 + "  # ← 验收临时加的尾巴"
                        结果, 文本 = await 叫工具(会话, "edit_src",
                                              {"path": 正本相对, "old": def行, "new": 新行})
                        print(f"  ① 好路径 · 它说：{文本.strip()!r}")
                        盘上 = 正本.read_text(encoding="utf-8")
                        期望 = 正本原样.replace(def行, 新行)
                        全绿 &= 报(盘上 == 期望 and 盘上 != 正本原样,
                                  f"改 {正本相对} 里真存在的一段 → 盘上【真的】变成新内容",
                                  "盘上还是原样 —— 工具根本没过写盘那一步"
                                  if 盘上 == 正本原样 else "")
                        正本.write_text(正本原样, encoding="utf-8")
                        全绿 &= 报(正本.read_text(encoding="utf-8") == 正本原样,
                                  "（立刻还原 —— 后面几枪必须打在【原样】上）")

                    # ═══ 活靶子们 ═══
                    # 后缀那道锁要单独验，得有一个【存在的、非 .py】的东西给它挡 ——
                    # 临时造一个，收摊时拔掉（写在 finally 里，崩了也拔）。
                    临时靶子.write_text("给后缀白名单的活靶子\n", encoding="utf-8")

                    # 找一个"在正本里出现多次"的片段，用来验【不许猜哪一处】
                    重复片段 = next((s for s in ("    ", "return", ")", "(")
                                  if 正本原样.count(s) > 1), None)

                    枪们 = []
                    if 测试行:
                        枪们.append(("改测试（改了就成自己给自己判分）",
                                    {"path": 测试文件.relative_to(题目根).as_posix(),
                                     "old": 测试行, "new": 测试行 + "  # 篡改"},
                                    测试文件, 测试原样))
                    # ⚠️ 跳【两级】：题目根是 arena/tasks/<题号>/，
                    #    判分卷在 arena/hidden/<题号>/ —— 中间隔着 tasks 和 arena 两层。
                    #    （跳一级到的是 arena/tasks/hidden/，那儿什么都没有：
                    #      这种"路径本身就打不到靶子"的枪最阴 —— 它会白送一个 ✅。）
                    枪们.append(("往上跳两级去动判分卷",
                                {"path": f"../../hidden/{题号}/{判分卷.name}",
                                 "old": 判分行, "new": 判分行 + "  # 篡改"},
                                判分卷, 判分原样))
                    枪们.append(("在 src/ 里凭空造 conftest.py（能改 pytest 行为）",
                                {"path": "src/conftest.py",
                                 "old": "def pytest_collection_modifyitems(items):",
                                 "new": "def pytest_collection_modifyitems(items): pass"},
                                题目根 / "src" / "conftest.py", None))
                    枪们.append(("改一个存在的非 .py（专打后缀那道锁）",
                                {"path": "src/临时靶子.txt",
                                 "old": "给后缀白名单的活靶子", "new": "改了"},
                                临时靶子, "给后缀白名单的活靶子\n"))
                    枪们.append(("old 在文件里根本不存在",
                                {"path": 正本相对,
                                 "old": "zzz_这段原文根本不在这个文件里_zzz", "new": "x"},
                                正本, 正本原样))
                    if 重复片段 is not None:
                        枪们.append((f"old 在文件里出现了 {正本原样.count(重复片段)} 次（不许猜是哪一处）",
                                    {"path": 正本相对, "old": 重复片段, "new": "x"},
                                    正本, 正本原样))

                    for 说明, 入参, 靶子, 该有的样子 in 枪们:
                        结果, 文本 = await 叫工具(会话, "edit_src", 入参)
                        崩 = 是崩溃(文本)
                        if 该有的样子 is None:
                            没发生 = not 靶子.exists()          # 该是个【不存在】的文件
                        else:
                            没发生 = 靶子.exists() and 靶子.read_text(encoding="utf-8") == 该有的样子
                        # ⚠️ 第二条判据：它【不许说"已修改"】。
                        #    光看"靶子没动"漏得掉一种情况：old 打错时，就算不拦，
                        #    替换也等于没换（盘上还是原文）→ 靶子当然没动。
                        #    可它会回一句"已修改 src/xx.py"—— 那句话直接把模型骗了：
                        #    它以为自己修好了，转头去跑测试，然后对着失败百思不得其解。
                        #    "没干成却汇报成功"正是第 4 步那条的反面（错误是给模型看的信息）。
                        没说成功 = "已修改" not in 文本
                        全绿 &= 报((not 崩) and 没发生 and 没说成功 and bool(文本.strip()),
                                  f"【越界·{说明}】{入参['path']} → 没改到，靶子原封不动",
                                  f"💥 抛异常了：{文本.strip()[:100]!r}" if 崩
                                  else (f"🔴【副作用真发生了】{靶子.name} 被动过 / 被造出来了"
                                        if not 没发生
                                        else (f"🔴【假汇报】它说'已修改'，可一个字都没改到"
                                              if not 没说成功 else f"它说：{文本.strip()[:90]!r}")))

                    # 收尾：正本这会儿还是原样吗？（上面每一枪都可能悄悄改到它）
                    全绿 &= 报(正本.read_text(encoding="utf-8") == 正本原样,
                              "一轮越界打下来，正本 src/ 一字未动")

                # ─────────────────────────────────────────────
                # ⚠️⚠️ 先把靶子撤了再进 ⑦ 节 —— 这是第一次跑当场抓到的：
                #    上面那个 tests/近路 junction 是【给 ④⑤⑥ 打的靶子】，
                #    我没拆就去跑 run_tests，pytest 顺着它摸进 hidden/，
                #    把【判分卷也收进了收集范围】（判分卷自己报 RuntimeError: ARENA_SRC 没设）。
                #    于是 ⑦ 节全排假红 —— 不是因为 run_tests 有毛病，
                #    是因为【上一节摆的道具把下一节的结论带偏了】。
                #    教训：一节验完就收道具；跨节的现场必须清干净。
                #    （先拆不亏：finally 里那次是幂等的，拆过了就返回 True。）
                print()
                print("=" * 66)
                print("🧹 ⑦ 节之前：先把 ④⑤⑥ 的 junction 靶子拆了")
                print("=" * 66)
                靶子拆了 = 拆junction()
                全绿 &= 报(靶子拆了 and not junction链接.exists(),
                          "junction 靶子已拆 —— ⑦ 节必须在【干净状态】下跑")

                print()
                print("=" * 66)
                print("⑦ run_tests —— ⭐ 闭环那一环")
                print("=" * 66)
                print("  ⚠️ 这一节判据跟前六节【不一样】，别混：")
                print("     前六节判「门挡住了没」；这一节判「它说的是不是【盘上真跑出来】的结果」。")
                print("     —— 盘一变，结论必须跟着变；盘一还原，结论必须【一字不差】地回来。")
                print("     这是本项目第一次出现【模型自己不知道、只有跑一下才知道】的东西。\n")

                if 正本 is None or not 可见函数们:
                    全绿 = False
                    print("  ❌ 盘上没有 src/*.py，或者 tests 里一个 test_ 函数都没有，这一节验不了")
                else:
                    # ⭐ 开工前先扫一遍地 —— 这一节最后那条"不许长脏东西"必须【从干净地面起算】。
                    #    现场留下的东西（上一次跑的、坏版留的）不算这一轮的账，见 扫残留() 上面那段。
                    开工时就有 = 一地残留()
                    if 开工时就有:
                        print(f"  🧹 开工时地上就有 {len(开工时就有)} 件残留（上一轮/坏版留下的），先扫掉：")
                        for 件 in 开工时就有[:4]:
                            print(f"       · {件}")
                    # ⚠️ 判分目录里的残留【也一起扫】。它虽然在门外，但它同样是"跑出来的垃圾"；
                    #    留在那儿只有一个后果：commit 进 Git 变脏。（收摊时会回头验判分卷还在。）
                    print(f"  → 扫掉 {len(扫干净())} 件，地面干净了；下面开始记这一轮自己的账\n")

                    # ═══ 地基枪：原样跑一次 —— 它得【真去跑】，而且得如实报红 ═══
                    # ⚠️ 为什么敢断言"必然有 failed"：每道题入库时都过了出题机的闸②
                    #    （有 bug + 跑可见测试 → 必须红）。所以"原样跑必然有红"是【入库契约】，
                    #    不是我对 t01 这一道题的印象 —— 换 t02/t03 这句照样成立。
                    结果, 首跑 = await 叫工具(会话, "run_tests", {})
                    print(f"  ① 原样跑一次 · 它说：\n{首跑.strip()}\n")
                    全绿 &= 报(not 是崩溃(首跑), "没抛异常（tool 里抛异常的话，模型只看到 'Error executing tool'）")
                    全绿 &= 报("failed" in 首跑 and "passed" in 首跑,
                              "输出里有 pytest 的汇总行（'… failed, … passed'）—— 这是【真跑过】的指纹",
                              f"它说：{首跑.strip()[:120]!r}")
                    # ⭐ 数条数：收集到的条数必须正好等于可见测试文件里的 test_ 函数个数。
                    #    这一条同时把两件事焊死了 ——【跑的是这一批】而且【没多收别人的】。
                    全绿 &= 报(跑了多少条(首跑) == len(可见函数们),
                              f"收集到的条数 = 可见测试的条数（{len(可见函数们)} 条）",
                              f"盘上有 {len(可见函数们)} 条，它跑了 {跑了多少条(首跑)} 条：{首跑.strip()[-120:]!r}")

                    # ═══ ⭐ 闭环一枪：同一份命令，盘一变结论就得变 ═══
                    # ⚠️ 这里【不查答案、也不引用正解】—— 尺子不许知道这道题该怎么改。
                    #    知道答案的尺子有放水的动机（"我照着答案判一下就行"），那就不叫验收了。
                    #    所以用通用的造坏法：往正本第 1 行塞一句 raise → 整个模块 import 不出来
                    #    → 收集阶段全灭。盘上确实坏了，它就必须说坏。
                    正本.write_text('raise RuntimeError("验收注入的假 bug")\n' + 正本原样,
                                encoding="utf-8")
                    结果, 坏跑 = await 叫工具(会话, "run_tests", {})
                    print(f"  ② 往 src/ 塞一句 raise 之后再跑 · 它说：\n{坏跑.strip()[:400]}\n")
                    全绿 &= 报("验收注入的假 bug" in 坏跑,
                              "盘上坏了，它报出来的也跟着坏（连那句 RuntimeError 都带回来了）",
                              f"它说：{坏跑.strip()[:120]!r}")
                    全绿 &= 报(去掉耗时(坏跑) != 去掉耗时(首跑),
                              "两次输出不一样 —— 不是把上一次的结果复读一遍")
                    全绿 &= 报("全绿" not in 坏跑, "没在坏盘上瞎说「全绿」")

                    正本.write_text(正本原样, encoding="utf-8")
                    结果, 还跑 = await 叫工具(会话, "run_tests", {})
                    全绿 &= 报(去掉耗时(还跑) == 去掉耗时(首跑),
                              "盘一还原，结论【一字不差】地回来了（它不记缓存、不留烂摊子）",
                              "" if 去掉耗时(还跑) == 去掉耗时(首跑)
                              else f"第一次：{首跑.strip()[:70]!r}\n       第二次：{还跑.strip()[:70]!r}")

                    # ═══ 陷阱枪：src/ 里塞一个【必然失败】的测试 ═══
                    # ⚠️ 专打"pytest 不带参数"的实现：那种写法从 cwd 往下全收集，
                    #    src/ 里这颗雷会被一起跑 —— 而它当然是红的。
                    #    后果不是"多跑几条"：模型只要能往 src/ 里丢测试，
                    #    它就能【自己给自己判分】（把红色的改绿，或干脆写个空测试凑数）。
                    陷阱测试.write_text(
                        f"def {陷阱名字}():\n    assert False, '我是 src/ 里的陷阱'\n",
                        encoding="utf-8")
                    结果, 陷阱跑 = await 叫工具(会话, "run_tests", {})
                    没被跑到 = 陷阱名字 not in 陷阱跑 and "我是 src/ 里的陷阱" not in 陷阱跑
                    全绿 &= 报(没被跑到,
                              "src/ 里塞的 test_*.py【没被跑】—— 靠的是参数 'tests'，不是裸跑",
                              毛病(没被跑到, f"🔴【漏了】src/ 里的陷阱被跑到了：{陷阱跑.strip()[:120]!r}"))
                    全绿 &= 报(去掉耗时(陷阱跑) == 去掉耗时(首跑) and 跑了多少条(陷阱跑) == len(可见函数们),
                              "塞了陷阱之后结论也没变（条数、内容都跟原样跑一样）")

                    # ═══ 判分卷枪：hidden/ 一个字节都不该进输出 ═══
                    # ⚠️ 判分卷的抬头要 ARENA_SRC 环境变量，拿这个当独有串 ——
                    #    它要是被跑了，输出里必然出现这句 RuntimeError。
                    #    比"函数名没出现"结实：函数名能被改，这句是判分卷自己的门锁。
                    漏判分 = [名 for 名, 文本 in (("原样跑", 首跑), ("坏盘跑", 坏跑),
                                                ("塞陷阱跑", 陷阱跑))
                            if 秘密判分 in 文本 or any(f in 文本 for f in 隐藏函数们)]
                    全绿 &= 报(not 漏判分,
                              "判分卷（hidden/）一个字都没被跑出来 —— 模型看到的只有规格那一份",
                              毛病(not 漏判分, f"🔴【漏了】{漏判分} 的输出里有判分卷痕迹"))

                    # 陷阱用完了就拔 —— 别让一个【必然失败】的测试在 src/ 里过夜。
                    # （收摊里那次是兜底，幂等；这里拔是为了让后面几枪打在干净状态上。）
                    陷阱测试.unlink(missing_ok=True)
                    全绿 &= 报(not 陷阱测试.exists(), "陷阱测试拔掉了（src/ 里不留必然失败的测试）")

                    # ═══ 超时枪：往正本塞死循环 —— 护栏得真起作用 ═══
                    # ⚠️ 这一枪【要等 20 秒】，是故意卡它的：不真卡一次，
                    #    就永远不知道"超时"那条路是不是写在纸上好看的。
                    #    ⚠️ 判据两条：① 必须自己返回（不能把整个 server 拖死）
                    #                 ② 它得说"掐了"，绝不能报"全绿"
                    正本.write_text("while True:\n    pass\n" + 正本原样, encoding="utf-8")
                    起点 = time.monotonic()
                    结果, 超时跑 = await 叫工具(会话, "run_tests", {})
                    掐耗时 = time.monotonic() - 起点
                    print(f"  ③ 塞个死循环再跑 · 它说：{超时跑.strip()[:160]!r}")
                    print(f"     （耗时 {掐耗时:.1f} 秒）\n")
                    掐住了 = 掐耗时 < 超时上限秒
                    全绿 &= 报(掐住了,
                              f"卡死的代码被掐掉了，{掐耗时:.1f} 秒就返回（上限 {超时上限秒} 秒）",
                              毛病(掐住了, f"🔴 它跑了 {掐耗时:.1f} 秒还没回来 —— 超时那条路没生效"))
                    全绿 &= 报("掐" in 超时跑 and "全绿" not in 超时跑,
                              "它说的是「我把它掐了」，没瞎报全绿",
                              f"它说：{超时跑.strip()[:120]!r}")
                    正本.write_text(正本原样, encoding="utf-8")
                    结果, 复原跑 = await 叫工具(会话, "run_tests", {})
                    全绿 &= 报(去掉耗时(复原跑) == 去掉耗时(首跑),
                              "掐过一次之后，再跑还是原来的结论（掐死进程没留下烂摊子）",
                              "" if 去掉耗时(复原跑) == 去掉耗时(首跑)
                              else f"它说：{复原跑.strip()[:90]!r}")

                    # ═══ 收尾枪：跑了这么些轮，题目目录【还是干净的】 ═══
                    # ⚠️ 验的是两件事：PYTHONDONTWRITEBYTECODE（不写 __pycache__）
                    #    + -p no:cacheprovider（不写 .pytest_cache）。
                    #    它们不是"顺手加的优化"：脏文件下一轮会出现在 list_task 的清单里，
                    #    模型会一本正经地去读那个 .pyc 二进制。
                    脏 = 一地残留()
                    全绿 &= 报(not 脏,
                              "跑了这么些轮，题目根 / 判分目录 / agent-lab 根【三处】都没长出脏东西",
                              毛病(not 脏, f"🔴 长出来了：{脏}"))
                    全绿 &= 报(测试文件.read_text(encoding="utf-8") == 测试原样,
                              "tests/ 跑前跑后一字未动（跑测试不该改测试）")

                    # ═══ 记录枪：靶子在场时会怎样（【不是及格线】，是钉住一条已知边界）═══
                    # ⚠️ 就是今天让 ⑦ 节整排假红的那个现场。钉在这儿的意义是【防复发】：
                    #    以后谁把顺序调回去（在拆靶子之前跑 run_tests），这行数字会立刻变。
                    #    两个结论都写下来，免得下次又当成 bug 查一遍：
                    #      ① 生产里不会发生 —— 模型【造不出链接】（edit_src 只能改已存在的
                    #         .py，连新建文件都不许），而白名单那几件早把链接挡在门外了。
                    #      ② 但它给【尺子】立了条规矩：上一节摆的道具会把下一节的结论带偏，
                    #         所以 ⑦ 节必须在干净状态下跑。
                    建成了2, 回话2 = 建junction()
                    if 建成了2:
                        结果, 带靶跑 = await 叫工具(会话, "run_tests", {})
                        带靶条数 = 跑了多少条(带靶跑)
                        带靶露馅 = 秘密判分 in 带靶跑 or any(f in 带靶跑 for f in 隐藏函数们)
                        print(f"  ℹ️ 【记录·不是及格线】靶子在场时跑一次 → 收集到 {带靶条数} 条"
                              f"（干净状态是 {len(可见函数们)} 条），判分卷痕迹 = {带靶露馅}")
                        print(f"       它说：{带靶跑.strip()[:140]!r}")
                        报(带靶露馅, "【记录】pytest 确实会顺着 tests/近路 摸进 hidden/ —— "
                                   "所以拆靶子这件事必须发生在 ⑦ 之前")
                        拆junction()
                    else:
                        print(f"  ℹ️ 【记录·不是及格线】junction 没造起来，这枪跳过：{回话2.strip()[:80]}")

                    # ⚠️ 同一个条件，【只写一遍、存成一个名字】。
                    #    第一版我判据正着写一遍、细节反着写一遍（`not (not A and not B)`），
                    #    结果 ✅ 旁边挂着 🔴 —— 就是这个文件顶上 毛病() 想治的那件事，
                    #    我自己又手写复现了一次。抽成变量，两边引用同一个名字，跑不到偏。
                    道具清了 = not junction链接.exists() and not 陷阱测试.exists()
                    全绿 &= 报(道具清了,
                              "记录枪造的道具也清了（junction / 陷阱测试都没留下）",
                              毛病(道具清了, f"🔴 还有东西留着：junction={junction链接.exists()} "
                                          f"陷阱={陷阱测试.exists()}"))

    finally:
        # ─────────────────────────────────────────────
        # 收摊：还原正本 / 拔临时靶子 / 拆 junction，并且【回头验判分卷还在】
        # ⚠️ 拆链接是最容易顺手删掉目标树的一步 —— 拿判分卷去赌 Windows 的行为不划算。
        print()
        print("=" * 66)
        print("🧹 收摊")
        print("=" * 66)
        拆了 = 拆junction()
        # ⚠️ 收摊写在 finally 里、不写在 else 里 —— 上面哪一步崩了也得收。
        #    10-12 那次就是"收摊"被写在 else 分支里：崩了就跳过，
        #    尸体（写坏的文件）留到下一枪，让下一枪在尸体上亮了个假绿灯。
        if 正本 is not None and 正本.exists():
            if 正本.read_text(encoding="utf-8") != 正本原样:
                正本.write_text(正本原样, encoding="utf-8")
                print(f"  ↩  正本 {正本相对} 被改过，已还原成原样")
            else:
                print(f"  ✅ 正本 {正本相对} 一字未动")
        if 临时靶子.exists():
            临时靶子.unlink()
        print(f"  ✅ 临时靶子拔掉了 = {not 临时靶子.exists()}")
        # ⚠️ ⑦ 节那个陷阱文件也必须拔 —— 它可是个【必然失败】的测试，
        #    留在 src/ 里，下一轮谁跑谁红（而且会污染 list_task 的清单）。
        if 陷阱测试.exists():
            陷阱测试.unlink()
        print(f"  ✅ src/ 里的陷阱测试拔掉了 = {not 陷阱测试.exists()}")
        print(f"  junction 拆了 = {拆了}")
        活着 = 判分卷.exists()
        print(f"  {'✅' if 活着 else '🔴🔴 出大事了'} 判分卷还在 = {活着}   ({判分卷})")
        if not 活着:
            print("  🔴 判分卷被删了 —— 重跑一次 arena/_make_tasks.py 就能长回来（题面都在脚本里）")
            全绿 = False

    print()
    print("=" * 66)
    print("🏁 全绿 —— 五件工具收工（白名单开在【题号 + src/】两层，闭环那一环也真转起来了）" if 全绿
          else "🏁 有 ❌ —— 往上翻，每条后面都贴了它【原话】。")
    print("   ⚠️ 报 ❌ 先分清三种：① 还没填 ② 没走到那一步 ③ 走到了但没拦住")
    print("=" * 66)
    return 0 if 全绿 else 1


try:
    码 = asyncio.run(main())
except BaseExceptionGroup as 群:
    # ⚠️ 服务器【根本起不来】时，客户端这边只会看到一句 "Connection closed"，
    #    真正的死因（SystemExit + stderr 里那行话）在 ExceptionGroup 的三层嵌套底下，
    #    直接摊给用户看是一屏天书。这里替他说人话，并指出【上哪儿看死因】。
    print()
    print("=" * 66)
    print("🔴 服务器没能起来 —— 客户端这边只能看见 'Connection closed'，看不出为什么。")
    print("=" * 66)
    print(f"   手动单敲一下它，死因会直接打在脸上：")
    print(f"     .venv\\Scripts\\python.exe {服务器文件} {题号}")
    print(f"   （stdio 服务器单独跑会【一直不出声】= 正常的，它在等客户端说话；")
    print(f"     立刻退出来并打了一行字 = 那就是死因。）")
    print(f"   原始异常：{群!r}"[:400])
    码 = 1

sys.exit(码)
