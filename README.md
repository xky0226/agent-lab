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

配套的 `_demo_*.py` 是每一步的**最小可运行实验**（例：`_demo_memory_grow.py` 实测 messages 膨胀，`_demo_is_relative_to.py` 实测路径越界判断的坑），`_check_*.py` 是每一步的**验收脚本**。

## 核心模块

### `mcp_server.py` — MCP 文件系统 Server

基于 [Model Context Protocol](https://modelcontextprotocol.io/) 2.3 自建的文件系统 Server：

- **4 个工具**：读文件 / 写文件 / 列目录 / 搜内容
- **1 个资源模板**：`file:///docs/{name}`
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
