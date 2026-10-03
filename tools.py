"""第 3 步 A：把工具搬进【工具柜】

第 2 步所有东西挤在一个文件里，2 个工具还行，5 个就撑爆了 —— 该拆家当了。
这个文件只装三样东西：

    ① 函数本体   —— 给【Python】跑的代码
    ② TOOLS      —— 给【模型】看的说明书（schema）：模型靠这张菜单认识你的工具
    ③ TOOL_MAP   —— 把「模型念的名字」翻译成「Python 里的函数」（电话簿）

⚠️ 注意：这个文件里【没有】client、【没有】messages、【没有】while ——
   它不认识模型，模型也不认识它。它只是一柜子工具。
   循环归循环，工具归工具，两边通过 TOOLS / TOOL_MAP 打招呼。

验证（在 agent-lab 目录下跑）：
    .venv/Scripts/python.exe -c "import tools; print([t['function']['name'] for t in tools.TOOLS])"
    .venv/Scripts/python.exe -c "import tools,datetime; print(tools.get_weather('成都', datetime.date.today().isoformat()))"
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

# ══════════════════════════════════════════════════════════
# 零件一：公共的「打电话」函数
#
#   5 个工具里 2 个要联网，与其各写各的，不如共用一个。
#   顺便复习 RAG 那条老流水线 —— 一模一样：
#
#       网络 → 字节(bytes) → decode → 字符串(str) → json.loads → dict
#
#   ⚠️ 下划线开头 = 内部用的零件，不是给模型点的菜。它不上 TOOLS。
# ══════════════════════════════════════════════════════════
def _http_get_json(url: str, timeout: float = 8.0) -> dict:
    """发请求 → 拿字节 → 解码 → 变成 dict。

    timeout：等多久还不回话就放弃（第 4 步要拿它做文章）。
    """
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        原始字节 = r.read()
    文本 = 原始字节.decode("utf-8")
    return json.loads(文本)



def _http_post_json(url: str, payload: dict, timeout: float = 8.0) -> dict:
    """发 POST → 拿字节 → 解码 → 变成 dict。

    跟 _http_get_json 是一家的兄弟，只多了两样：
    ① data=         ← 这就是 GET / POST 的【开关本身】
    ② Content-Type  ← 声明"我发出去的是 JSON"
    """
    information = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=information,
        headers={"User-Agent": "curl/8", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        原始字节 = r.read()
    return json.loads(原始字节.decode("utf-8"))


# ══════════════════════════════════════════════════════════
# 工具 1：get_weather —— 查天气（联网 + 能力边界）
#
#   两个细节，看仔细：
#     ① 函数里【没有 print】—— 返回值是「给模型看的」，不是给人看的。
#        你在终端看到天气，是因为【你】在打印返回值。
#     ② 出错了【自己接住】，把「错误」当成【正常返回】交给模型 ——
#        模型比代码会说话，它会替你跟用户说「抱歉查不到，稍后再试」。
#        要是直接 raise 抛出去，整个程序就当场死在那儿了。
#
#   ⚠️ 能力边界（2026-10-01 加）：只服务【今天起 3 天】。
#      wttr.in 的 data["weather"] 是 3 个元素的列表（今天/明天/后天），
#      超出范围就在代码里直接返回"查不到"，不给模型"凑"的机会。
#
#      为什么非得有这条：模型不知道今天几号时，会拿相近的数据顶替
#      （"明日天气"四个字，底下贴的是今天的实况）。而【明确的失败】
#      它反而老实认账 —— 09-29 在 add_todo 上验过同一件事。
#
#   ⚠️ date 参数【不发给】wttr.in —— 它只当"守门员"：在本地跟
#      data["weather"][i]["date"] 比一下（字符串相等），就完事。
#      请求 URL 里永远只有城市名。
# ══════════════════════════════════════════════════════════
def get_weather(city: str, date: str) -> str:
    try:
        # ⚠️ URL 里不能有中文 —— 必须先用 quote() 转义成 %XX 形式。
        #    城市是"中文名"这件事，是 schema 告诉模型的；那转义就是我们自己的活。
        城市转义 = urllib.parse.quote(city)
        data = _http_get_json(f"https://wttr.in/{城市转义}?format=j1")

    except Exception as e:
        return f"查询 {city} 天气失败：{type(e).__name__}: {e}"

    # 挑：在 3 天里找 date 对得上的那一天
    #   day = None 必须在循环【之前】立好 —— 万一一圈都没匹配上，
    #   后面的 if not day 才有东西可读（否则是 UnboundLocalError，不是 None）
    day = None
    for d in data["weather"]:
        if d["date"] == date:
            day = d          # 留【整块】那一天 —— 只留 d["date"] 的话，温度和降水就丢了
    if not day:
        w = data["weather"]
        return f"查不到 {date} 的天气。我只能查 {w[0]['date']} 到 {w[-1]['date']} 这三天。"

    return (
        f"{city} {day['date']}：{day['hourly'][4]['weatherDesc'][0]['value'].strip()}，"
        f"{day['mintempC']}~{day['maxtempC']}℃，"
        f"降水概率 {day['hourly'][4]['chanceofrain']}%"
    )




# ══════════════════════════════════════════════════════════
# 工具 2：get_exchange_rate —— 查汇率
# ══════════════════════════════════════════════════════════
def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """把一种货币换成另一种。

    数据源（免 key）：
        https://api.exchangerate-api.com/v4/latest/USD
    返回长这样：
        {"base": "USD", "date": "2026-09-22",
         "rates": {"CNY": 7.12, "JPY": 147.3, "EUR": 0.92, ...}}

    ⚠️ 这个接口只认【一个】base，但一次把所有货币的汇率全给你。
       所以"CNY 换 JPY"它给不了现成的 —— 得自己算：
       rates 里的数是「1 美元 = 多少 X」，所以 A→B = rates[B] ÷ rates[A]。
       谁除谁搞反了，答案能差 50 倍。

    边界情况：
        · 模型给了不存在的货币代码 → rates[...] KeyError → 当成"失败"返回
        · 小汇率币种（如 1 VND ≈ 0.000042 USD）→ 固定 4 位小数会全变 0，
          所以按大小切两种精度，末尾再去掉多余的 0
    """

    try:
        data = _http_get_json("https://api.exchangerate-api.com/v4/latest/USD")
        if from_currency not in data["rates"]:
            return f"{from_currency}是不存在的货币"
        if to_currency not in data["rates"]:
            return f"{to_currency}是不存在的货币"
    except Exception as e:
        return f"查询{from_currency}转{to_currency}的汇率失败:{type(e).__name__}: {e}"

    fr = data["rates"][from_currency]
    to = data["rates"][to_currency]

    result = to / fr
    res = f"{result:.4f}" if result >= 1 else f"{result:.8f}"
    res = res.rstrip("0").rstrip(".")

    return f"在{data['date']}，1 {from_currency} ≈ {res} {to_currency}"


# ══════════════════════════════════════════════════════════
# 零件二：待办的「账本」—— 存在硬盘上的一个 json 文件
#
#   为什么存文件、不存内存里的一个 list？
#     内存里的东西【程序一关就没了】—— 那 Agent 就没真正"改变世界"。
#     关掉重开还在，才算真的动了手。
#
#   顺便把上次学的 json 四兄弟用上 —— 这次是【文件版】那两个：
#       读：json.load(f)       ← 不打 s，手里拿的是文件
#       写：json.dump(obj, f)   ← 不打 s，手里拿的是文件
# ══════════════════════════════════════════════════════════
待办账本 = Path(__file__).parent / "todos.json"
# 👆 __file__ = "我这个脚本自己的位置"。所以它总能在【脚本旁边】找到账本，
#    不管你在哪个目录敲命令。比写死一个 "todos.json" 稳得多。


def _读待办() -> list:
    """把账本读进来。文件还没建 → 当成空账本（这是正常的，不是错误）。"""
    if not 待办账本.exists():
        return []
    with open(待办账本, encoding="utf-8") as f:
        return json.load(f)


def _写待办(todos: list) -> None:
    """把账本写回去。

    ensure_ascii=False —— 不加这句，中文会被写成 \\u83dc\\u4e70 那种鬼画符。
    """
    with open(待办账本, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════
# 工具 3：add_todo —— 第一个【会改变世界】的工具
#
#   前两个工具都是"看一眼"（天气、汇率），世界没变。
#   这个不一样：跑完之后，硬盘上真的多了一条记录。
#
#   这就是 Agent 和聊天机器人的分界线：
#       聊天机器人只会【说话】，Agent 能【动手】。
# ══════════════════════════════════════════════════════════
def add_todo(content: str, due_date: str) -> str:
    try:
        todos = _读待办()                                     # ① 读出来
        todos.append({"content": content, "due_date": due_date})   # ② 加一条
        _写待办(todos)                                        # ③ 写回去
    except Exception as e:
        return f"添加待办失败：{type(e).__name__}: {e}"
    return f"已添加：{content}（{due_date}），当前共 {len(todos)} 条待办"
    # 注意这三步是【读—改—写】。为什么不直接 append 到文件？
    # 因为文件是一整块，没法像 list 那样从尾巴塞进去 —— 只能整块读出来、改完、整块写回去。


# ══════════════════════════════════════════════════════════
# 工具 4：get_calendar —— 读账本（和 add_todo 一写一读，同一本账本）
# ══════════════════════════════════════════════════════════
def get_calendar(date: str) -> str:
    """查某一天的安排。

    账本里每条记录长这样：
        {"content": "买菜", "due_date": "2026-09-23"}

    需求是「把这一天的安排【都】列出来」—— 是"全部"，不是"第几个"，
    所以全程用 for 循环把匹配的【攒】起来，不用方括号去取某一条。
    """
    try:
        todos = _读待办()

        # ① 挑：把 due_date 等于 date 的【内容】一条条攒进「匹配」
        匹配 = []
        for i in todos:
            if i["due_date"] == date:
                匹配.append(i["content"])

        # ② 空：一条都没攒到 —— 注意判断在【循环外面】，判断的是「攒出来的这堆是不是空的」
        if len(匹配) == 0:
            return f"{date} 没有安排"
            # 这里用 date（你要查的那一天），不是用 匹配
            # 用 匹配 的话只会打印出一个 [] ，模型看不懂

        # ③ 拼：把攒到的每一条，变成"一行文字"
        行们 = []
        for c in 匹配:
            行们.append(f"- {c}")

        # ④ 缝："\n".join(列表) = 拿换行符，把这一串字符串【缝】成一整段文字
        正文 = "\n".join(行们)
        return f"{date} 共 {len(匹配)} 项安排：\n{正文}"

    except Exception as e:
        # 调试期把真错误也带出来 —— 不然只看到"失败：XXError"，不知道错在哪
        return f"查找安排失败：{type(e).__name__}: {e}"






# ══════════════════════════════════════════════════════════
# 工具 5：search_docs —— 跨进程去【真 RAG】要材料
#
#   电话线那头是另一个项目：rag-knowledge-base（有自己的 .venv、
#   langchain、两个本地模型）。两个进程各跑各的，靠 HTTP 说话。
#
#   为什么不直接 import retriever？—— 那样 agent-lab 也得装上
#   langchain + torch + bge 两个模型（几个 G），只为了检索这一件事。
#   分家，才能让这头保持【轻】。
#
#   ⚠️ 这条线是【机器对机器】：接口交回来的是【一堆】原始材料（materials），
#      本工具负责把它【排版成一段】再交给模型 —— 因为模型读的是人话。
# ══════════════════════════════════════════════════════════

# 电话线那头在哪 —— rag-knowledge-base 起的服务（uvicorn 默认 8000）
RAGurl = "http://127.0.0.1:8000"


def search_docs(query: str) -> str:
    """在知识库里检索资料（真的跨进程打电话）。

      ⚠️两种"没结果"必须【分开说】：
        · 服务挂了   → except 接住 → "检索失败"
        · 知识库没有 → materials 是空的 → "没有相关资料"
        混成一句话，Agent 就分不清"真没有"和"坏了"。
    """
    try:
        data = _http_post_json(f"{RAGurl}/api/rag/search", {"query": query})
    except Exception as e:
        return f"查询 {query} 失败：{type(e).__name__}: {e}"

    materials = data["materials"]
    if not materials:
        return f"没有查询到{query}"

    context = ""
    for i, mate in enumerate(materials):
        context += f"\n材料 {i + 1}：\n{mate}\n"

    return context




# ══════════════════════════════════════════════════════════
# 零件的「说明书」—— 给模型看的菜单
#
#   模型看不见你的 Python 代码，它只能看见这个列表。
#   所以：description 怎么写，模型就怎么理解你这个工具。
# ══════════════════════════════════════════════════════════
TOOLS = [
    # ── 工具 1 的说明书：我写好了，你【照着这个模子】写工具 2 的 ──
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            # 说明书只管【格式】【例子】【必须调用】。
            # "查不到就说查不到，别凑数"那句软约束已退休 —— 代码里的边界是真的，
            # 不必再求它（软约束磨了三代，"明日天气"的标题一步没退）。
            # ⚠️ 别在 description 里写"只能查3天"—— 那会改变模型行为，
            #    以后调边界就分不清是代码的功劳还是话术的功劳了。一次只动一个变量。
            "description": "查询指定城市某一天的天气。涉及天气的问题必须调用此工具，不得凭记忆回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市中文名，例如：成都、北京",
                    },
                    "date": {
                        "type": "string",
                        "description": "查询哪一天，格式必须是 YYYY-MM-DD，例如：2026-10-01",
                    },
                },
                "required": ["city", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "查询指定货币的汇率,并返回结果,涉及货币汇率的问题必须调用此工具,不得凭记忆回答",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string",
                                      "description": "货币代码，三位大写字母。例如：美元=USD、人民币=CNY、日元=JPY、英镑=GBP"
                                      },
                    "to_currency": {"type": "string",
                                    "description": "货币代码，三位大写字母。例如：美元=USD、人民币=CNY、日元=JPY、英镑=GBP"
                                    },

                },
                "required": ["from_currency", "to_currency"],
            },
        },
    },

    # ── 工具 3 的说明书：我也写好了，你可以对照一下「有副作用」的工具怎么措辞 ──
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "给用户添加一条待办事项。用户说「帮我记一下」「加个提醒」「记到日程里」时必须调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "待办的内容，一句话，例如：买菜",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "日期，格式必须是 YYYY-MM-DD，例如：2026-09-23",
                    },
                },
                "required": ["content", "due_date"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_calendar",
            "description": "查询用户输入日期的待办事项,用户说:「帮我看看今日安排」「帮我查看今日事情」「查看今日待办」时必须调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "查询待办的日期,查该日期的所有安排,格式必须是YYYY-MM-DD, 例如:2026-09-23",
                    },
                },
                "required": ["date"],
            },
        },
    },

    # ── 工具 5 的说明书：实现从「桩」换成「真 RAG」，这张 schema 一字未改。
    #    这就是第 3 步把 函数体 / TOOLS / TOOL_MAP 分三份的回报：换引擎，不换菜单 ──
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "在内部知识库（员工手册、公司规章制度、流程规范等）里检索资料。用户问公司制度、规定、流程时必须调用此工具，不得凭记忆回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索用的关键词或问题，例如：年假有几天",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ══════════════════════════════════════════════════════════
# 电话簿：模型念名字（字符串），你查电话簿找到函数（可调用的东西）
# ══════════════════════════════════════════════════════════
TOOL_MAP = {
    "get_weather": get_weather,
    "get_exchange_rate": get_exchange_rate,
    "add_todo": add_todo,
    "search_docs": search_docs,
    "get_calendar": get_calendar,
    # ⚠️ key 必须和 schema 里的 name 一字不差。三处（函数名 / schema name / 这里）
    #    对不上，就是「模型点了一道菜，电话簿里没这个号」→ KeyError
}
