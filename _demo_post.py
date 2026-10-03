"""验证 _http_post_json 零件 —— 拿 Python 自带的 http.server 当【假的对端】

为什么要假的：真的对面（rag 服务）要等 ④ 才起。
先拿假货把流水线跑通 —— 跟 search_docs 先写桩是同一个思路。

跑法（agent-lab 目录下）：.venv/Scripts/python.exe _demo_post.py
⚠️ 没写 _http_post_json 之前跑，会在最后一行报 AttributeError —— 那是故意的，写完就好
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import tools


class 假的对端(BaseHTTPRequestHandler):
    """一个只有 5 行的假 rag 服务：收到什么，回声什么（外加两条假材料）"""

    def do_POST(self):
        长度 = int(self.headers["Content-Length"])
        收到的 = json.loads(self.rfile.read(长度).decode("utf-8"))

        回话 = json.dumps(
            {"你发给我的": 收到的, "materials": ["假材料 A", "假材料 B"], "count": 2},
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(回话)))
        self.end_headers()
        self.wfile.write(回话)

    def log_message(self, *a):
        pass          # 别让它刷屏


服务器 = HTTPServer(("127.0.0.1", 8765), 假的对端)
threading.Thread(target=服务器.serve_forever, daemon=True).start()

要发的 = {"query": "年假有几天？"}
print("① 零件【发出去】的是：", 要发的)

结果 = tools._http_post_json("http://127.0.0.1:8765/api/rag/search", 要发的)

print("② 零件【拿回来】的是：", 结果)
print()
print("③ 对面收到的那句话对不对？ ->", 结果.get("你发给我的"))
