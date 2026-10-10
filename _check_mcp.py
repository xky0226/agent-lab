"""
对账：手写版 tools.TOOLS  vs  MCP 版 server.list_tools()

验四样：
  ① 件数对不对（5 件都搬过来了吗）
  ② description 是不是一字不差（任务 1 的核心要求）
  ③ input_schema 跟手写版差在哪（任务 2 要捡的东西）
  ④ resource 登记没有 + 白名单挡不挡得住（任务 3）

⚠️ 为什么任务 3 的验收要写进【同一个脚本】：
   任务 1（docstring）和任务 2（参数说明）分开两次验的话，
   改签名把 docstring 挤掉那次就漏过去了 —— 改 A 弄坏 B，
   只有"每次都全量跑一遍"才抓得住。

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _check_mcp.py
"""

import asyncio
import sys
from pathlib import Path

# Windows 控制台默认 GBK，打不出 ✅（直接 UnicodeEncodeError 崩掉）。掰成 utf-8。
sys.stdout.reconfigure(encoding="utf-8")

import tools
from mcp_server import read_doc, server


async def main():
    MCP版 = {t.name: t for t in await server.list_tools()}
    手写版 = {s["function"]["name"]: s["function"] for s in tools.TOOLS}

    print("=" * 66)
    print(f"① 件数：手写版 {len(手写版)} 件 / MCP 版 {len(MCP版)} 件")
    print("=" * 66)
    print(f"  手写版有: {sorted(手写版)}")
    print(f"  MCP 版有: {sorted(MCP版)}")
    print(f"  两边名字集合一致 → {set(手写版) == set(MCP版)}")

    print()
    print("=" * 66)
    print("② description 一字不差？（任务 1 的核心要求）")
    print("=" * 66)
    全对 = True
    for 名, f in 手写版.items():
        m = MCP版.get(名)
        if m is None:
            print(f"  ❌ {名}  —— MCP 版里没有这件工具")
            全对 = False
            continue
        一致 = m.description == f["description"]
        全对 = 全对 and 一致
        print(f"  {'✅' if 一致 else '❌'} {名}")
        if not 一致:
            print(f"       手写原话: {f['description']!r}")
            print(f"       你写的  : {m.description!r}")
    print(f"\n  → 五件全对：{全对}")

    print()
    print("=" * 66)
    print("③ 参数说明书：手写版 vs MCP 自动生成的（任务 2 的靶子）")
    print("=" * 66)
    for 名, f in 手写版.items():
        m = MCP版.get(名)
        if m is None:
            continue
        手写参 = f["parameters"]["properties"]
        mcp参 = m.input_schema.get("properties", {})
        名字一致 = set(手写参) == set(mcp参)
        必填一致 = set(f["parameters"].get("required", [])) == set(m.input_schema.get("required", []))
        print(f"\n  【{名}】  参数名一致 {名字一致} / required 一致 {必填一致}")
        for k in 手写参:
            print(f"      {k}")
            print(f"          手写版 说明: {手写参[k].get('description')!r}")
            print(f"          MCP 版 说明: {mcp参.get(k, {}).get('description')!r}")

    print()
    print("=" * 66)
    print("④ 任务 3：resource 登记没有？白名单挡不挡得住？")
    print("=" * 66)

    print(f"  普通资源: {await server.list_resources()}")
    模板表 = await server.list_resource_templates()
    print(f"  模板资源: {模板表}")
    print(f"  → 模板登记上了：{len(模板表) > 0}")
    for t in 模板表:
        print(f"     URI 模板 {t.uri_template!r}  →  函数 {t.name}({', '.join(t.uri_template.split('{')[1].rstrip('}').split(',')) if '{' in t.uri_template else '无参数'})")

    print()
    print("  ── 正常路径：真读一个文件 ──")
    try:
        正文 = read_doc("服务器清单.txt")
        print(f"  ✅ 读到 {len(正文)} 个字符：{正文.strip().splitlines()[0]!r} …")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")

    # 诱饵文件里写着"不该被读到"这几个字。够着了 → 白名单没挡住。
    诱饵标记 = "不该被读到"

    # 下面这些枪的靶子全是【同一个诱饵文件】，所以判据统一：
    # 返回/报错里出现「不该被读到」四个字，就是越界成功了。
    诱饵文件 = Path(__file__).resolve().parent / "secret.txt"

    print()
    print("  ── 坏路径：绕开 URI 那道门，直接叫 read_doc() 去够外面的东西 ──")
    print("     （等于模拟「上游那把锁哪天不在了」，看你自己那把锁顶不顶用）")
    for 说明, 名字 in [
        ("往上跳一级", "../secret.txt"),
        ("跳到 docs_bak/ → 名字以 docs 开头的那一招", "../docs_bak/秘密.txt"),
        ("绝对路径 → 直接报上诱饵文件的全名", str(诱饵文件)),
        ("反斜杠跳级", "..\\secret.txt"),
        ("走 junction 近路 → 字面在 docs 里，真身在 docs_bak", "近路/秘密.txt"),
    ]:
        try:
            结果 = read_doc(名字)
            if 诱饵标记 in 结果:
                print(f"  ❌ 【{说明}】越界成功！它读到了外面：{结果.strip()[:40]!r}")
            else:
                print(f"  ✅ 【{说明}】没读到外面（它返回了话）：{结果.strip()[:40]!r}")
        except Exception as e:
            if 诱饵标记 in str(e):
                # 消息里带内容 = 它先把文件读了才报错，等于漏了
                print(f"  ❌ 【{说明}】越界成功！报错消息里带出了内容：{e}")
            else:
                print(f"  ✅ 【{说明}】被挡：{type(e).__name__}: {e}")

    print()
    print("  ── 办不到的那几种，话有没有好好说？ ──")
    print("     ⚠️ 这几枪必须走 server.read_resource()，不能直接叫函数 ——")
    print("        因为「原话会不会被吞」是【SDK 那一层】干的事，绕过去就测不到了。")
    for 说明, uri in [
        ("文件根本不存在", "file:///docs/根本没有这个文件.md"),
        ("给的是个目录不是文件", "file:///docs/."),
    ]:
        try:
            结果 = await server.read_resource(uri)
            print(f"  ⚠️ 【{说明}】没报错，返回：{str(list(结果)).strip()[:50]!r}")
        except Exception as e:
            # UnexpectedResourceError = 你的原话被 SDK 吞了，客户端只看到"出错了"
            吞了 = type(e).__name__ == "UnexpectedResourceError"
            print(f"  {'❌ 被吞' if 吞了 else '✅ 留住了'} 【{说明}】{type(e).__name__}: {e}")

    print()
    print("=" * 66)
    print("附：函数签名（MCP 的 schema 就是从这儿长出来的）")
    print("=" * 66)
    import inspect
    源码树 = __import__("ast").parse(open("mcp_server.py", encoding="utf-8").read())
    for 节点 in 源码树.body:
        if isinstance(节点, __import__("ast").FunctionDef):
            参数 = ", ".join(a.arg for a in 节点.args.args)
            print(f"  def {节点.name}({参数})")


asyncio.run(main())
