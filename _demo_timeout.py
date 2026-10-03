"""陪练：把「超时线」单独拉出来跑一遍（补第 4 步欠的那笔账）

为什么非要单独验：get_weather 内部有个 try 把什么都接住了 —— 网络正常时
这条线【永远不会出现】，顺路跑一百次也看不见它。这跟"顺路路径验证不了
坏路径"是同一个道理，得专门制造。

做法：不改 tools.py 的生产值（timeout=8.0 留着），只在【内存里】临时把
     _http_get_json 换成"1 毫秒版"，跑完立刻换回来 —— 硬盘上零改动。

跑法（在 agent-lab 目录下）：
    .venv/Scripts/python.exe _demo_timeout.py
"""
import tools

真超时 = tools._http_get_json          # 先留个备份，等下要换回来
今天 = "2026-10-03"

print("=" * 62)
print("【第 1 层】零件单独试 —— timeout=0.001 秒，它抛的是什么？")
print("=" * 62)
try:
    tools._http_get_json("https://wttr.in/Chengdu?format=j1", timeout=0.001)
    print("❓ 居然没抛？网太快了，换成更小的值再来")
except Exception as e:
    print(f"抛出来的类：{type(e).__name__}")
    print(f"它说的话  ：{e}")
    print(f"再往里看  ：{getattr(e, 'reason', '（这层没有 reason）')}")

print()
print("=" * 62)
print("【第 2 层】工具层 —— get_weather 拿到它，交回给【模型】的是什么？")
print("=" * 62)

tools._http_get_json = lambda url: 真超时(url, timeout=0.001)   # 临时换上 1 毫秒版
try:
    print("超时版 get_weather 返回：")
    print("   " + tools.get_weather("成都", 今天))
finally:
    tools._http_get_json = 真超时                               # 立刻换回来

print()
print("对照 —— 正常的 8 秒版：")
print("   " + tools.get_weather("成都", 今天))

print()
print("=" * 62)
print("【第 3 层】另外两个 except 也照一下 —— 它们的「失败」带没带详情？")
print("=" * 62)

tools._http_get_json = lambda url: 真超时(url, timeout=0.001)
try:
    print("汇率：" + tools.get_exchange_rate("USD", "CNY"))
finally:
    tools._http_get_json = 真超时

