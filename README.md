<div align="center">

  <h1>🤖 easyAgent</h1>

  **一个简单易用的多Agent协作框架**

  [![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)](https://fastapi.tiangolo.com)
  [![React](https://img.shields.io/badge/React-19+-cyan.svg)](https://react.dev)

  [快速开始](#-快速开始) • [功能特性](#-核心特性) • [文档](#-文档) • [API](#-api-接口)

</div>

---

## 📖 项目简介

**easyAgent** 是一个轻量级、易扩展的多Agent协作框架，通过多个专业化Agent的智能协作来处理复杂任务。框架提供完整的Agent生命周期管理、动态插件加载、流式响应和会话管理功能。

### ✨ 为什么选择 easyAgent？

- 🎯 **开箱即用** - 内置完整的Agent管理系统，几分钟即可启动
- 🔌 **插件化架构** - 动态加载Agent插件，轻松扩展功能
- 🤝 **智能协作** - Agent间自动任务传递和上下文共享
- 📡 **MCP协议支持** - 原生支持Model Context Protocol
- 💾 **会话管理** - 完整的对话历史持久化
- 🚀 **高性能** - 基于FastAPI和React，支持SSE流式响应
- 🎨 **Web界面** - 现代化React UI，实时流式对话体验

---

## 🌟 核心特性

### 1. 多Agent协作系统
- ✅ 智能任务路由和分发
- ✅ Agent间任务自动传递
- ✅ 完整的对话上下文管理
- ✅ 支持任务拆分和并行处理

### 2. MCP协议支持
- ✅ Model Context Protocol集成
- ✅ 远端MCP服务器连接（SSE）
- ✅ 自动工具调用和结果处理
- ✅ 健康检查和错误恢复

### 3. 会话管理
- ✅ 多会话支持
- ✅ 对话历史持久化
- ✅ 会话标题自动生成
- ✅ 对话导出功能

### 4. 流式响应
- ✅ Server-Sent Events (SSE)
- ✅ 实时Agent状态更新
- ✅ 增量内容输出
- ✅ 错误事件推送

### 5. 强大的动态可扩展性 🌟
- ✅ **零配置加载** - 将Agent文件放入`plugin/`目录即可自动加载
- ✅ **热插拔支持** - 无需重启服务，API触发重新加载即可生效
- ✅ **简单开发** - 只需继承Agent基类，实现run方法
- ✅ **智能封装** - 返回值自动标准化，支持多种返回类型
- ✅ **统一接口** - 所有Agent遵循相同的接口规范
- ✅ **完整示例** - 提供demo_agent.py作为开发模板

---

## 🏗️ 项目架构

```
easyAgent/
├── core/                    # 核心框架模块
│   ├── agent_manager.py    # Agent管理器（核心协调器）
│   ├── agent.py            # Agent基类和AgentLoader
│   ├── plugin_manager.py   # 插件管理器
│   ├── mcp_client.py       # MCP协议客户端
│   ├── context_manager.py  # 上下文和会话管理
│   ├── base_model.py       # Message数据模型
│   ├── agents/             # 内置Agent实现
│   │   ├── entrance_agent.py  # 入口Agent
│   │   ├── general_agent.py   # 通用Agent
│   │   ├── demand_agent.py    # 需求处理Agent
│   │   └── mcp_agent.py       # MCP协议Agent
│   └── prompt/             # 提示词模板系统
│
├── api/                    # FastAPI服务
│   ├── server.py          # API服务器
│   ├── database.py        # 数据库服务
│   └── models.py          # Pydantic数据模型
│
├── web/                    # React前端
│   ├── src/
│   │   ├── components/    # React组件
│   │   ├── pages/         # 页面组件
│   │   └── services/      # API服务封装
│   └── package.json
│
├── data/                   # 数据存储目录
│   └── conversations.db    # SQLite数据库
│
├── example/                # Agent示例代码
│   ├── demo_agent.py      # 数学计算Agent（推荐阅读）
│   └── sql_agent.py       # SQL查询Agent
│
├── main.py                 # 主程序入口（支持CLI和API模式）
├── config.py              # 配置管理
├── requirements.txt        # Python依赖
├── .env.example           # 配置模板
└── README.md              # 项目文档
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **Node.js**: 18+ (如需使用Web界面)
- **LLM服务**: OpenAI API或兼容服务

### 1. 克隆项目

```bash
git clone https://github.com/your-username/easyAgent.git
cd easyAgent
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装Python依赖
pip install -r requirements.txt
```

### 3. 配置环境

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，配置LLM服务
# LLM_BASE_URL=http://127.0.0.1:9999/v1
# LLM_API_KEY=your-api-key
# LLM_MODEL_NAME=gpt-4
```

### 4. 启动服务

#### 选项A: 启动完整服务（后端+前端）

```bash
# 终端1: 启动后端API
python main.py --api

# 终端2: 启动前端
cd web
npm install
npm run dev

# 访问 http://localhost:5173 使用Web界面
```

#### 选项B: 仅启动后端API

```bash
# 生产模式
python main.py --api

# 开发模式（自动重载）
python main.py --api --dev

# 访问 http://localhost:8000/docs 查看API文档
```

#### 选项C: 命令行模式

```bash
# 运行默认查询示例
python main.py

# 运行自定义查询
python main.py "帮我查询图书信息"

# 流式输出
python main.py --stream "帮我查询图书信息"
```

### 5. 验证安装

```bash
# 健康检查
curl http://localhost:8000/health

# 预期响应:
# {"status":"ok","service":"easyAgent API","version":"0.1.0","agents_loaded":4}
```

### 6. 体验动态扩展性 🌟

```bash
# 1️⃣ 复制示例Agent到plugin目录
cp example/demo_agent.py plugin/

# 2️⃣ 触发热重载（两种方式）

# 方式A: CLI模式（重启自动加载）
python main.py "计算 123 加 456"

# 方式B: API模式（无需重启）
# 先启动API服务
python main.py --api

# 然后调用重载接口
curl -X POST http://localhost:8000/agents/reload

# 立即可用！
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "计算 123 加 456"}'
```

**说明**：
- CLI模式：每次运行时自动加载plugin目录
- API模式：提供`/agents/reload`接口实现热插拔
- 重载会保留所有内置Agent和MCP Agent

---

## 💻 使用示例

### Python API调用

```python
from core import AgentManager
from config import get_config

# 加载配置
config = get_config()

# 初始化AgentManager
agent_manager = AgentManager(
    plugin_src="plugin",
    base_url=config.settings.LLM_BASE_URL,
    api_key=config.settings.LLM_API_KEY,
    model_name=config.settings.LLM_MODEL_NAME
)

# 同步调用
response = agent_manager("查询图书信息")
for msg in response:
    print(f"{msg['role']}: {msg.get('message', '')}")

# 流式调用
for event in agent_manager("查询图书信息", stream=True):
    if event["type"] == "delta":
        print(event["data"]["content"], end="", flush=True)
```

### HTTP API调用

```bash
# 同步模式
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "查询图书信息",
    "stream": false
  }'

# 流式模式 (SSE)
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "查询图书信息",
    "stream": true
  }'
```

### JavaScript客户端

```javascript
// 使用fetch API
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: '查询图书信息',
    stream: false
  })
});

const result = await response.json();
console.log(result.response);
```

---

## 🔌 内置Agent

### 1. Entrance Agent（入口Agent）
- **功能**: 解析用户请求，生成任务列表
- **特点**: 不对外直接使用，作为所有请求的入口点

### 2. General Agent（通用Agent）
- **功能**: 处理一般性问答，整合多个Agent的结果
- **特点**: 默认后备Agent，负责格式化输出

### 3. Demand Agent（需求处理Agent）
- **功能**: 处理复杂需求，任务拆分
- **特点**: 支持多步骤任务处理

### 4. MCP Agent（MCP协议Agent）
- **功能**: 与MCP服务器通信，调用外部工具
- **特点**: 支持SSE传输，自动工具调用

---

## 📡 API接口

### 主要端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/agents` | 获取Agent列表 |
| POST | `/agents/reload` | 热重载插件Agent |
| GET | `/agents/{name}` | 获取Agent详情 |
| POST | `/chat` | 同步聊天接口 |
| POST | `/chat/stream` | 流式聊天接口(SSE) |
| GET | `/conversations` | 获取会话列表 |
| POST | `/conversations` | 创建新会话 |
| GET | `/conversations/{id}` | 获取会话详情 |
| DELETE | `/conversations/{id}` | 删除会话 |
| POST | `/conversations/{id}/export` | 导出会话 |

### API文档

启动服务后访问:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🛠️ 技术栈

### 后端
- **Python 3.8+** - 核心开发语言
- **FastAPI** - 高性能Web框架
- **Pydantic 2.0+** - 数据验证和设置管理
- **OpenAI SDK** - LLM接口
- **Uvicorn** - ASGI服务器
- **SQLite** - 数据库（会话持久化）

### 前端
- **React 19** - UI框架
- **Vite** - 构建工具
- **Axios** - HTTP客户端
- **React Router** - 路由管理
- **Lucide React** - 图标库
- **React Markdown** - Markdown渲染

### 集成
- **MCP Protocol** - Model Context Protocol
- **SSE** - Server-Sent Events流式传输

---

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `LLM_BASE_URL` | LLM服务地址 | `http://127.0.0.1:9999/v1` | 是 |
| `LLM_API_KEY` | API密钥 | - | 是 |
| `LLM_MODEL_NAME` | 模型名称 | `openai/gpt-oss-20b` | 是 |
| `PLUGIN_DIR` | 插件目录 | `plugin` | 否 |
| `MCP_ENABLED` | 启用MCP | `false` | 否 |
| `LOG_LEVEL` | 日志级别 | `INFO` | 否 |

### 🚀 创建自定义Agent

easyAgent的强大之处在于**极简的扩展方式**。只需3步即可创建并部署自定义Agent：

#### 快速开始（3步）

```bash
# 1️⃣ 复制示例文件到plugin目录
cp example/demo_agent.py plugin/my_agent.py

# 2️⃣ 触发重载
# CLI模式：直接运行（自动加载）
python main.py "测试消息"

# API模式：调用重载接口
curl -X POST http://localhost:8000/agents/reload

# 3️⃣ 立即使用
python main.py "计算 123 加 456"
```

#### 热插拔使用（API模式）

```bash
# 场景1：添加新Agent
cp example/demo_agent.py plugin/new_agent.py
curl -X POST http://localhost:8000/agents/reload
# 新Agent立即可用，无需重启服务

# 场景2：删除Agent
rm plugin/old_agent.py
curl -X POST http://localhost:8000/agents/reload
# Agent已移除

# 场景3：更新Agent
vim plugin/existing_agent.py
curl -X POST http://localhost:8000/agents/reload
# 修改立即生效
```

#### 完整示例

查看 `example/demo_agent.py` 获取完整注释的示例代码：

```python
# plugin/my_agent.py
from core.agent import Agent
from core.base_model import Message
from core.prompt.template_model import PromptTemplate

class MyAgent(Agent):
    """自定义Agent示例"""

    def __init__(self):
        # 1. 配置Agent基本信息
        super().__init__(
            name="my_agent",                    # 唯一标识
            description="Agent功能描述",         # 帮助LLM理解何时调用
            handles=["关键词1", "关键词2"],      # 触发关键词
            parameters={                        # 参数说明
                "input": "输入参数说明"
            }
        )

        # 2. 创建提示词模板
        self.prompt_template = PromptTemplate(
            system_instructions="你是一位专业助手",
            available_agents=None,
            core_instructions="具体任务执行指南",
            data_fields="返回数据的结构说明"
        )

    def run(self, message: Message) -> Message:
        """
        3. 实现核心处理逻辑

        输入: message（包含LLM解析后的数据）
        输出: Message 或 Dict 或 任意类型
        """
        # 提取数据
        data = message.data or {}

        # 处理逻辑
        result = process_data(data)

        # 返回结果（3种方式）
        # 方式1: 返回Message（完全控制）
        return Message(
            status="success",
            task_list=["任务1", "任务2"],
            data={"key": "value"},
            next_agent="none",              # "none"结束，或指定下一个Agent
            agent_selection_reason="原因说明",
            message="处理完成"
        )

        # 方式2: 返回字典（系统自动封装）
        # return {"result": result}

        # 方式3: 返回简单值（系统包装）
        # return result
```

#### 返回值说明

`run()` 方法支持3种返回类型，系统会自动标准化：

| 返回类型 | 说明 | 适用场景 |
|---------|------|---------|
| `Message` | 完整控制所有字段 | 需要精确控制任务流、错误处理 |
| `Dict` | 系统自动封装到data | 返回结构化数据，继续处理 |
| `其他类型` | 系统包装到data.result | 简单计算、查询结果 |

#### Agent协作

通过设置 `next_agent` 字段实现Agent间任务传递：

```python
# 结束流程
next_agent = "none"

# 继续让通用Agent处理
next_agent = "general_agent"

# 传递给特定Agent
next_agent = "other_agent_name"
```

#### 最佳实践

1. **命名规范**
   - 文件：`xxx_agent.py`
   - 类名：`XxxAgent`
   - Agent名：`xxx_agent`

2. **错误处理**
   ```python
   try:
       result = process()
   except Exception as e:
       return Message(
           status="error",
           data={"error": str(e)},
           next_agent="none",
           message=f"处理失败: {e}"
       )
   ```

3. **日志记录**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("处理完成")
   ```

4. **测试Agent**
   ```bash
   # CLI模式测试
   python main.py "你的问题"

   # API模式测试
   python main.py --api
   # 访问 http://localhost:8000/docs

   # Web界面测试
   cd web && npm run dev
   ```

#### 更多示例

- `example/demo_agent.py` - 数学计算Agent（带完整注释）
- `example/sql_agent.py` - SQL查询Agent
- `core/agents/demand_agent.py` - 需求处理Agent
- `core/agents/mcp_agent.py` - MCP协议Agent

---

## 🎯 应用场景

- **🤖 智能客服系统** - 路由不同类型问题到专业Agent
- **📊 数据查询助手** - 自然语言到SQL转换
- **🔄 工作流自动化** - 多步骤任务自动化处理
- **📖 知识问答系统** - 领域专家Agent协作
- **🛠️ 开发助手** - 代码生成、调试、文档生成

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🌟 致谢

- [OpenAI](https://openai.com/) - 提供强大的LLM API
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Pydantic](https://docs.pydantic.dev/) - 数据验证库
- [React](https://react.dev/) - 用户界面库
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star支持一下！**

</div>
