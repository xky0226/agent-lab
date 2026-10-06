"""
门禁线实测：422 和 401，到底谁先拦？

背景
────
复习时说"门禁线 = 422 → 401 → 403 → 404"。这句话到底是
    (a) 语义上的【设计顺序】该从谁问起，还是
    (b) 框架【真的】就是这么跑的？
光用嘴讲不算数 —— 跑一下，让电脑自己说。

这里是个【不碰数据库、不碰 Redis】的最小 FastAPI，
只有一个鉴权依赖 + 一个整数查询参数，专门用来把"谁先拦"这一件事逼出来。

跑法
────
    cd D:\\toutiao\\agent-lab
    uv run --with httpx python _demo_gate.py

⚠️ httpx 只借给 TestClient 用（它负责假装发 HTTP 请求），不进项目依赖。
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

app = FastAPI()


# ── 门卫 1：查身份 ────────────────────────────────────────────
# 真实项目里这玩意儿叫 get_current_user，会去解 token、查用户。
# 这里压扁成"token 是不是 Bearer good"。
def check_token(authorization: str = Header(default=None)) -> str:
    if authorization != "Bearer good":
        raise HTTPException(status_code=401, detail="身份不对")
    return "user-1"


# ── 门卫 2：资源存在性 ────────────────────────────────────────
# 注意它【住在函数体里面】，不在签名上 —— 这一点后面有用。
def get_news(news_id: int) -> dict:
    if news_id != 123:
        raise HTTPException(status_code=404, detail="新闻不存在")
    return {"news_id": news_id}


# ── 端点 ──────────────────────────────────────────────────────
@app.get("/only-auth")
def only_auth(who: str = Depends(check_token)):
    """只有身份这一道门。"""
    return {"who": who}


@app.get("/with-param")
def with_param(news_id: int, who: str = Depends(check_token)):
    """两道门：参数字段 news_id 的格式校验 + 身份。"""
    return {"news_id": news_id, "who": who}


@app.get("/with-404")
def with_404(news_id: int, who: str = Depends(check_token)):
    """三道门：格式 → 身份 → 资源在不在。"""
    return get_news(news_id)


client = TestClient(app)


def 打(标题: str, r) -> None:
    print(f"  {标题}")
    print(f"      → {r.status_code}   {r.json()}")


print("=" * 64)
print("实验一：只挂身份这一道门（没有参数要校验）")
print("=" * 64)
打("token 合法            GET /only-auth  [Bearer good]",
  client.get("/only-auth", headers={"Authorization": "Bearer good"}))
打("没带 token            GET /only-auth",
  client.get("/only-auth"))

print()
print("=" * 64)
print("实验二：★核心★ 参数格式 + 身份，两道门都在")
print("=" * 64)
打("参数合法 + 没带 token   ← 只犯一个错",
  client.get("/with-param", params={"news_id": "123"}))
打("参数非法 + 没带 token   ← 两个错都犯！谁先开火？",
  client.get("/with-param", params={"news_id": "abc"}))
打("参数非法 + token 合法",
  client.get("/with-param", params={"news_id": "abc"},
             headers={"Authorization": "Bearer good"}))
打("参数合法 + token 合法",
  client.get("/with-param", params={"news_id": "123"},
             headers={"Authorization": "Bearer good"}))

print()
print("=" * 64)
print("实验三：三道门（格式 → 身份 → 资源在不在）")
print("=" * 64)
打("全合法，但那篇新闻不存在（news_id=999）",
  client.get("/with-404", params={"news_id": "999"},
             headers={"Authorization": "Bearer good"}))
打("新闻不存在 + 没带 token   ← 404 和 401 谁先？",
  client.get("/with-404", params={"news_id": "999"}))
