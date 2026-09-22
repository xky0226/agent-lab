"""拆开看：一次网络请求，到底分几跳？

跑法：在 agent-lab 目录下
    .venv/Scripts/python.exe _demo_urllib.py
"""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://wttr.in/Chengdu?format=j1"

print("═" * 56)
print("【第 1 跳】Request —— 写拨号单（打给谁 + 报上名号）")
print("═" * 56)
req = urllib.request.Request(URL, headers={"User-Agent": "curl/8"})
print("  拿到的是：", type(req))
print("  打给谁：  ", req.full_url)
print("  报的名号：", req.headers)

print()
print("═" * 56)
print("【第 2 跳】urlopen —— 拨号、等接通")
print("═" * 56)
r = urllib.request.urlopen(req, timeout=8)
print("  接通了！拿到的是：", type(r))
print("  HTTP 状态码：     ", r.status)
print("  ⚠️ 此刻你【还没拿到内容】——只是接通了，内容还在对面手里")

print()
print("═" * 56)
print("【第 3 跳】read —— 把对面说的话吸出来")
print("═" * 56)
原始字节 = r.read()
print("  吸到的是：      ", type(原始字节))
print("  前 50 个：      ", 原始字节[:50])
print("  长度：          ", len(原始字节), "个字节")
print("  ⚠️ 是【字节】不是文字 —— 电脑只认 0 和 1，谁告诉你它是什么编码？")

print()
print("═" * 56)
print("【第 4 跳】decode —— 字节 → 文字")
print("═" * 56)
文本 = 原始字节.decode("utf-8")
print("  现在是：        ", type(文本))
print("  前 50 个字：    ", 文本[:50])

print()
print("═" * 56)
print("【第 5 跳】json.loads —— 文字 → dict")
print("═" * 56)
数据 = json.loads(文本)
print("  现在是：        ", type(数据))
print("  里面的 key：    ", list(数据.keys())[:6])

r.close()  # with ... as r: 就是自动帮你干这一下

print()
print("═" * 56)
print("【反面教材】出错的时候长什么样")
print("═" * 56)

print("\n① 域名本身就不对（还没连上就挂了）→ URLError")
try:
    urllib.request.urlopen("https://meiyouzhegeyuming.example", timeout=5)
except urllib.error.URLError as e:
    print("    抓到：", type(e).__name__, "→", e)

print("\n② 域名对，但对面说「没这页」（404）→ HTTPError")
try:
    urllib.request.urlopen(
        "https://api.exchangerate-api.com/v4/latest/XXXX", timeout=8
    )
except urllib.error.HTTPError as e:
    print("    抓到：", type(e).__name__, "→ 状态码", e.code, e.reason)
    print("    （HTTPError 是 URLError 的小弟，两个都接得住）")

print("\n③ 通了但内容是坏的 → json.JSONDecodeError")
try:
    json.loads("这不是 json")
except json.JSONDecodeError as e:
    print("    抓到：", type(e).__name__, "→", e)

print("\n④ 所以 get_weather 里写的 except Exception 是什么？")
print("   它是【总闸】——上面三种、加上 KeyError、TypeError、超时……全兜住。")
print("   在工具函数里这么做是【故意的】：我们要把错误变成一句话交给模型，")
print("   而不是让整个 Agent 程序当场崩掉。")
