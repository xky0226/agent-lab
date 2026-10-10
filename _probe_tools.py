"""
探针：不启动服务，直接把 server 对象拿过来问。

⚠️ 这个探针能跑，全靠 mcp_server.py 最后那句 `if __name__ == "__main__":`
   —— 没那个守卫，import 这一行就会抢走 stdin 卡死在这儿。

              课程第 3 课 —「怎么确认它真的活了？」

跑法：
    cd D:\\toutiao\\agent-lab
    .venv\\Scripts\\python.exe _probe_tools.py
"""

import asyncio
import sys

# Windows 控制台默认 GBK，中文会打成乱码 —— 看着像"输出坏了"，其实只是编码没对齐。
sys.stdout.reconfigure(encoding="utf-8")

from mcp_server import server


async def main():
    工具们 = await server.list_tools()          # ⚠️ 是 async，要 await
    print(f"这个 server 上挂着 {len(工具们)} 件工具\n")
    for t in 工具们:
        print(f"  ┌─ {t.name}")
        print(f"  │  说明书 = {t.description!r}")
        print(f"  └─ 参数   = {t.input_schema}")
        print()

    # 顺带把注册的资源也问一遍 —— 任务 3 加进来之后，两种登记分开放。
    还有资源 = await server.list_resource_templates()
    print(f"另外挂着 {len(还有资源)} 个模板资源：")
    for r in 还有资源:
        print(f"  ┌─ URI 模板 = {r.uri_template!r}")
        print(f"  └─ 对应函数 = {r.name}")


asyncio.run(main())
