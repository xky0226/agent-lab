"""
⑦ 验收：文件系统 Server 的那几件，真的顶用吗？

跟 _check_mcp.py 的区别 ——
    _check_mcp.py    import 进来直接叫函数（同一个进程，绕开一切）
    这个             起真进程 + stdio 说话（走的全是客户端那条路）

为什么非要走真进程：这两件工具的价值【全在"真会落地"】上 ——
    列目录要真去数磁盘上有什么
    写要真落到 notes/ 里
绕开 SDK 直接叫函数，等于把"跨进程还灵不灵"跳过去了。

⚠️ 本脚本会【真写文件】—— 这是故意的（写工具的验收只能这么验）。
   但它只碰自己的临时文件 _验收临时.md，跑完自己删；
   使用说明.txt 只读不动。

⭐ 判据的两条铁律（这份脚本自己踩过一遍才改对的）：
   ① 「挡住」的唯一判据是【副作用没发生】，不是 is_error、不是颜色。
      按我们给的骨架，挡住是 `return 一句"办不到"` —— 那算【正常返回】，
      is_error 会是 False。拿 is_error 当判据，他一填对反而报 ❌。
   ② 工具【压根没跑起来】时，副作用同样没发生 ——
      「挡住」会白送一堆假 ✅。所以开头先探一枪：它到底跑没跑。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _check_mcp_fs.py
    .venv\\Scripts\\python.exe _check_mcp_fs.py 别的_server.py   ← 可选：换一个验
"""

import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# 默认验 mcp_server.py。允许在命令行换一个 ——
# 这样这把尺子本身可以被"标准答案"验一遍（别拿没验过的尺子量人）。
服务器文件 = sys.argv[1] if len(sys.argv) > 1 else "mcp_server.py"
启动参数 = StdioServerParameters(command=sys.executable, args=[服务器文件])

本目录 = Path(__file__).resolve().parent
资源目录 = (本目录 / "docs").resolve()   # 跟 mcp_server.py 里那个保持一致
写区 = 本目录 / "notes"
临时文件 = 写区 / "_验收临时.md"
不许动 = 写区 / "使用说明.txt"   # 覆盖那一枪的靶子 —— 只读不动


def 取文本(结果):
    """CallToolResult 的 content 是一串【内容块】，不是字符串 —— 自己拼回来。"""
    块们 = 结果.content or []
    return "".join((getattr(b, "text", None) or "") for b in 块们)


def 是崩溃(文本):
    """SDK 的兜底话术。出现它 = 工具【抛异常了】，不是好好说了句"办不到"。

    两种都要当"没跑起来"处理 —— 它们的副作用也没发生，
    但那是【没走完】，不是【被拦下】。这两种绝不能混。
    """
    文本 = 文本.strip()
    return 文本.startswith("Error executing tool") or "NotImplementedError" in 文本


def 报(ok, 说明, 细节=""):
    print(f"  {'✅' if ok else '❌'} {说明}")
    if 细节:
        print(f"       {细节}")
    return ok


async def 叫工具(会话, 名字, 入参):
    结果 = await 会话.call_tool(名字, 入参)
    return 结果, 取文本(结果)


async def main():
    全绿 = True

    async with stdio_client(启动参数) as (读, 写):
        async with ClientSession(读, 写) as 会话:
            握手 = await 会话.initialize()
            print(f"连上了：{握手.server_info.name}\n")

            工具们 = await 会话.list_tools()
            名字们 = {t.name for t in 工具们.tools}
            # ⚠️ list_resource_templates() 给回来的是一个【结果对象】，
            #    模板列表在它的 .resource_templates 里 —— 不能直接 len() 它。
            #    （server 那侧的同名方法返回的是列表，两边形状不一样，踩过一次）
            资源们 = (await 会话.list_resource_templates()).resource_templates
            print("=" * 66)
            print("① 登记情况")
            print("=" * 66)
            print(f"  tool     {len(工具们.tools)} 件：{sorted(名字们)}")
            print(f"  resource {len(资源们)} 件模板：{[t.uri_template for t in 资源们]}")
            全绿 &= 报({"list_docs", "write_note"} <= 名字们,
                      "两件新工具都登记上了（探针绿 ≠ 服务对，这里走的是 __main__ 那条路）")

            # ─────────────────────────────────────────────
            print()
            print("=" * 66)
            print("② ③ 列目录 —— 它数得对吗？")
            print("=" * 66)
            结果, 文本 = await 叫工具(会话, "list_docs", {})
            print(f"  它说：{文本.strip()!r}\n")
            if 是崩溃(文本):
                全绿 = False
                print("  ⏭  list_docs 还没填（★1）—— 这节先跳过")
            else:
                全绿 &= 报("员工手册摘录.md" in 文本, "员工手册摘录.md 在清单里")
                全绿 &= 报("服务器清单.txt" in 文本, "服务器清单.txt 在清单里")
                # ⚠️ 上面两条判据是【找子串】—— 全路径里也含文件名，照样能过。
                #    所以再加一条：返回的必须是【名字】，不是【一条路径】。
                #    这就是"变量名撒谎"的照妖镜：变量叫 name，装的是不是名字？
                路径泄漏 = str(资源目录) in 文本
                全绿 &= 报(not 路径泄漏, "返回的是【名字】不是【路径】",
                          f"它把整条路径端出来了：{文本.strip()!r}" if 路径泄漏 else "")
                # 近路是 junction → 指向 docs_bak 目录。要的是"文件"，它不该出现。
                全绿 &= 报("近路" not in 文本,
                          "近路 不在清单里（它是目录不是文件 —— 提示 B 的答案）")
                if "近路" in 文本:
                    print("       ⚠️ 它把 junction 也列出来了：你数的是「里头所有的东西」")
                    print("          而不是「文件」。IS_FILE() 那一下漏了。")

            # ─────────────────────────────────────────────
            print()
            print("=" * 66)
            print("④ 写 —— 四道锁挨个撞")
            print("=" * 66)

            太长 = 写区 / "太长.md"

            # ⚠️ 开跑前先【清场】—— 2026-10-12 实测踩出来的盲区：
            #    write_note 在 f.write 之后 return None，会在 return 那一步被 SDK
            #    拦下（-> str 是【出厂检验】，见 func_metadata → pydantic)，
            #    可是【副作用早就发生了】—— 文件已经躺在盘上。
            #    而下面"收摊"那两行写在 else 分支里，一崩溃就跳过 → 尸体留到下一枪。
            #    下一枪里，尸体让 ★4「已存在」先开火，那是个【合法字符串】，
            #    于是不崩了，④ 节反而报【全绿】。绿在上一枪的尸体上。
            #    跟越界靶子同一条规矩：【靶子必须本来不存在】。
            #    —— 这条规矩当时只给越界那 5 枪用了，忘了管自己这一枪。
            临时文件.unlink(missing_ok=True)
            太长.unlink(missing_ok=True)

            # 先探一枪：工具到底跑没跑起来？
            # 没跑起来的话，下面那些"副作用没发生"全都会变成假 ✅。
            结果, 文本 = await 叫工具(会话, "write_note",
                                    {"name": "_验收临时.md", "content": "第一条验收内容"})
            if 是崩溃(文本):
                print(f"  ⏭  write_note 还没填好，或者里面抛异常了：{文本.strip()!r}")
                print("     这节【整节跳过】—— 理由：下面每条「挡住」的判据都是")
                print("     「副作用没发生」，工具没跑起来时副作用当然也没发生，")
                print("     会给出一串假 ✅。（报告 ❌ 不代表防线坏了，是尺子不适用）")
                全绿 = False
            else:
                存在 = 临时文件.exists()
                内容对 = 存在 and 临时文件.read_text(encoding="utf-8") == "第一条验收内容"
                全绿 &= 报(not 结果.is_error and 存在 and 内容对,
                          "【该成的成了】新建文件 → 真落到磁盘上、内容一字不差",
                          f"文件在={存在} 内容对={内容对}；它说：{文本.strip()[:80]!r}")

                # ── 锁②：只增不改
                原本 = 不许动.read_text(encoding="utf-8") if 不许动.exists() else None
                结果, 文本 = await 叫工具(会话, "write_note",
                                        {"name": "使用说明.txt", "content": "我要把你盖掉"})
                之后 = 不许动.read_text(encoding="utf-8") if 不许动.exists() else None
                全绿 &= 报(原本 == 之后,
                          "【只增不改】覆盖已有文件 → 原文件一个字没变",
                          f"没动={原本 == 之后}；它说：{文本.strip()[:80]!r}")

                # ── 锁①：白名单（四枪）
                #
                # ⚠️ 靶子必须挑【本来不存在】的文件名 —— 这是踩出来的：
                #    一开始拿 ../secret.txt 当靶子，结果"已有"那道锁顺手把它拦了，
                #    报出来的 ✅ 是【别的锁的功劳】，白名单漏了也看不出来。
                #    （跟 10-01 那次「顺路路径验证不了坏路径」同一个病）
                #    换成不存在的名字之后，就只剩白名单能拦住 —— 判据才干净。
                for 说明, 坏名, 落点 in [
                    ("往上跳一级", "../越界写.txt", 本目录 / "越界写.txt"),
                    ("反斜杠跳级", "..\\越界写2.txt", 本目录 / "越界写2.txt"),
                    ("跳到上一层的上一层", "../../越界写3.txt", 本目录.parent / "越界写3.txt"),
                    ("绝对路径", str(本目录 / "越界写4.txt"), 本目录 / "越界写4.txt"),
                    ("走 junction 近路", "近路/偷偷写.md", 本目录 / "docs_bak" / "偷偷写.md"),
                ]:
                    落点.unlink(missing_ok=True)
                    结果, 文本 = await 叫工具(会话, "write_note",
                                            {"name": 坏名, "content": "越界写"})
                    全绿 &= 报(not 落点.exists(),
                              f"【越界·{说明}】{坏名} → 没落地",
                              f"它说：{文本.strip()[:80]!r}")
                    落点.unlink(missing_ok=True)

                # ── 锁③：大小上限
                结果, 文本 = await 叫工具(会话, "write_note",
                                        {"name": "太长.md", "content": "哗" * 200000})
                全绿 &= 报(not 太长.exists(),
                          "【大小上限】20 万字的内容 → 没落盘",
                          f"它说：{文本.strip()[:80]!r}")

            # 收摊：只删自己造的那两个。
            # ⚠️ 这一句原来写在上面的 else 里 —— 工具一崩溃就跳过，尸体留到下一枪。
            #    现在挪到 if/else【外面】，正常、崩溃两条路都收摊。
            临时文件.unlink(missing_ok=True)
            太长.unlink(missing_ok=True)
            print(f"\n  🧹 临时文件已删：{临时文件.name} / 太长.md（若有）")

    print()
    print("=" * 66)
    print("🏁 全绿 —— 四件套齐了（读/写/列/搜），文件系统 Server 收工" if 全绿
          else "🏁 有 ❌ —— 往上翻，每条后面都贴了它【原话】。")
    print("   ⚠️ 报 ❌ 先分清三种：① 还没填  ② 没走到那一步  ③ 走到了但没拦住")
    print("=" * 66)


asyncio.run(main())
