# agent-lab — 从零手写 AI Agent

> 不用 LangChain，不用任何 Agent 框架。用最原始的 API 调用，一步步把 Agent 的每一块零件拆开看明白。

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991)](https://platform.openai.com/docs/api-reference)
[![MCP](https://img.shields.io/badge/MCP-2.3.0-000000)](https://modelcontextprotocol.io/)

## 为什么不用框架

大多数人做 Agent 是从 `AgentExecutor.from_agent_and_tools(...)` 开始的 —— 三行代码跑起来，但说不清里面发生了什么。

这个项目反过来：**先手写，再理解**。每一步都是一个能独立跑起来的脚本，看得见每一轮模型往返的原始请求与响应。

## 学习路径（每一步都是可运行脚本）

| 脚本 | 做了什么 | 你会看见 |
|---|---|---|
| `step0_see_tool_calls.py` | 观察模型返回的原始 `tool_calls` 结构 | 模型「想调工具」到底长什么样 |
| `step1_manual_call.py` | 手动执行一次工具调用并把结果喂回去 | 一次完整的决策 → 执行 → 回灌 |
| `step2_loop.py` | 把上面那步套进 `while` 循环 | **Agent Loop 的本质就是一个循环** |
| `step3_agent.py` | 工具注册表 + 多工具调度 | 模型怎么在多个工具之间选 |
| `step4_guard.py` | 三条错误线：超时 / 参数错 / 编造工具名 | 失败路径怎么兜，循环不能崩 |
| `step5_mcp.py` | 接入 MCP Server（协议层） | 工具从「自己拧的电话线」变成「标准插头」 |
| `step6_memory.py` | 装上三层记忆 + 两把 token 尺子 | 记忆是**包在循环外面的壳**，循环体几乎没动 |

配套的 `_demo_*.py` 是每一步的**最小可运行实验**（例：`_demo_memory_grow.py` 实测 messages 膨胀，`_demo_is_relative_to.py` 实测路径越界判断的坑），`_check_*.py` 是每一步的**验收脚本**。

## 核心模块

### `mcp_server.py` — MCP 文件系统 Server

基于 [Model Context Protocol](https://modelcontextprotocol.io/) 2.3 自建的文件系统 Server：

- **7 个工具**：天气 / 汇率 / 待办 / 日程 / 文档检索 / 列文档 / 写笔记
- **1 个资源模板**：`file:///docs/{name}`（只读资料做成**资源**，需要模型主动执行的动作才做成**工具**）
- **路径越界防护**：用 `Path.resolve()` + `is_relative_to()` 做**层级白名单**，而不是 `str.startswith()` 字符串前缀匹配 —— 后者会被 `docs_bak` 这类兄弟目录绕过

```python
真实路径 = (写目录 / name).resolve()

if not 真实路径.is_relative_to(写目录):
    return "办不到，落点不在要写的目录里"
if 真实路径.exists():
    return "办不到，目录里已经存在这个文件"
```

> 💡 这里的 `return "..."` 是刻意的：工具函数的返回值会**原样回到模型眼里**，所以拒绝也要说人话，让模型知道下一步该怎么办。

### `memory.py` — 三层记忆

| 层 | 存什么 | 解决什么 |
|---|---|---|
| 工作记忆 | `messages` 列表 | 「我们刚才聊了啥」—— 它只增不减，是病根 |
| 会话记忆 | `sessions/<id>.json` | 「关掉进程还能接着聊」 |
| 长期记忆 | `profile.json` | 「你是谁」—— 跨会话的结构化事实，贴在 system 里 |

配合实测脚本 `_demo_memory_grow.py`：**4 轮对话，`prompt_tokens` 从 24 涨到 75（3.1 倍）**，而这 4 轮用户一共只说了 53 个字 —— 涨的是「整本账被重新寄了一遍」，不是新说的话。

关键设计：**账本（全量、存盘）和「发出去的那一份」（可能压过）是两个列表**。压过的结果一旦写回账本，被裁掉的历史就永久消失了，而且事后翻磁盘查不出来。

`step6_memory.py` 把三层层层接上循环，并在每轮同时打印两把尺子（事前的字数粗估 / 事后的 `usage.prompt_tokens` + 缓存命中）。同剧本 5 问的对照实测：不压 `prompt_tokens` 1154 → 1557，开了 `--compress` 是 1154 → 1357（省 4%）；但缓存命中一个涨到 1408、一个卡在 896 —— **省了 token 不等于省了钱**，压缩会打断前缀缓存。

## 快速开始

```bash
# 依赖只有 5 个，没有任何重量级模型库
pip install -e .

# 配置密钥（.env 已在 .gitignore 里）
echo "API_KEY=sk-你的key" > .env

# 从最基础的一步开始跑
python step0_see_tool_calls.py
```

## 设计原则

1. **只用手写，不引框架** —— 目的是理解机制，不是快速交付。
2. **每一步都能单独跑** —— 脚本之间不互相依赖，随时从中间捡起来。
3. **验收看副作用，不看出错信息** —— 例如判断「越界写入被挡住了」，判据是**文件确实没被创建**，而不是看接口是否返回了 error。
4. **不装重量级依赖** —— 项目里没有 `chromadb` / `sentence-transformers` / `torch`。需要向量检索时，**走 HTTP 调独立的 RAG 服务**，而不是把几个 GB 的模型拖进来。

## 技术栈

`Python 3.11+` · `openai`（OpenAI 兼容接口）· `mcp 2.3.0` · `FastAPI` · `uvicorn`

## License

MIT
