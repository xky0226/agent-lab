"""第一次给【真的】RAG 服务打电话 —— 跨进程连通性验证

⚠️ 这个脚本故意要跑【两次】，顺序不能反：

    第一次：rag-knowledge-base 没起      → 看 tools.search_docs 的 except 分支
    第二次：uvicorn 起来（8000 在听）    → 看真的材料

为什么非要先跑失败那次：先看见失败长什么样，之后看见绿灯才敢信是真的。
（`_test_search.py` 打错接口还回 HTTP 200 那次，就是反面教材。）

跑法（agent-lab 目录下）：
    .venv/Scripts/python.exe _demo_rag.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # ⚠️ Windows 控制台默认 GBK，不转码连 emoji 都印不出来（会直接崩）

import tools

print("电话线那头是：", tools.RAGurl)
print("=" * 62)

# 这一行背后跑的是：json.dumps → encode → POST → 对面 retrieve_and_rerank
#                    → materials 列表 → 回来 → 这边排版成一段
结果 = tools.search_docs("年假有几天？")

print(结果)
print("=" * 62)
print(f"拿到 {len(结果)} 个字符。")
print()
print("👀 对一下这几件事：")
print("   ① 服务没起时 → 走的是哪条路？（提示：不是 materials 那条）")
print("   ② 服务起了   → 材料有几段？跟 _test_search.py 那次对得上吗？")
print("   ③ 开头是不是有个空行？（context 是从 '' 开始 += 的）")
