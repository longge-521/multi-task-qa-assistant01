# Multi-Task QA Assistant (多任务智能问答助手) 🚀

这是一个基于 **DeepSeek LLM** 和 **LangChain** 打造的全栈智能助手。它集成了本地知识库 (RAG)、实时天气预报、热点新闻搜索、A 股涨停板查询等多种实用工具，并原生支持 **DeepSeek R1 (Reasoner)** 的思考过程可视化。

---

## 🌟 核心功能

- **DeepSeek R1 推理可视化**：
  - 🧠 **智能搜索 (deepseek-reasoner)**：不仅提供回答，更能在 UI 中实时流式展示 AI 的“思考过程”，揭示逻辑推理路径。
- **📚 本地知识库 (RAG)**：
  - **语义检索**：集成 FAISS 向量数据库，自动对 `Backend/knowledge/` 目录下的文档进行索引与检索。
  - **精准引用**：AI 回答中会标注资料来源（如 `[来源: welcome.txt]`），确保信息的可溯源性。
- **多模型无缝切换**：
  - 🚀 **快速通道 (deepseek-chat)**：极速响应，适用于日常对话与即时工具调用。
  - 🧠 **深度思考 (deepseek-reasoner)**：处理复杂逻辑、数学或长链推理任务。
- **强大的工具扩展**：
  - ⛅ **实时天气**：基于 IP 自动定位或手动输入城市，获取分钟级天气实况。
  - 📰 **稳健新闻搜索**：内置 Robust Fallback 机制，解决 DuckDuckGo 403 访问限制，确保资讯获取成功率。
  - 📈 **A 股助手**：对接 AkShare 实时数据，支持自然语言日期查询（如“前天”）及涨停股回溯。
- **配置系统升级**：
  - 支持通过 `.env` 完整配置 APP 端口、主机、调试模式及数据库路径，无需改动源码。
- **现代化 UI 体验**：
  - 基于 Vue 3 的深色科技感界面，支持工具调用回显与 Server-Sent Events (SSE) 实时流。

---

## 🛠️ 技术栈

### 后端 (Backend)
- **核心框架**: Python 3.10+, FastAPI (高性能异步处理)
- **大模型驱动**: LangChain + DeepSeek API
- **向量数据库**: FAISS (本地知识库索引)
- **数据源**: Open-Meteo (天气), DDGS (新闻), AkShare (股票)
- **数据库**: SQLite (会话持久化存储)

### 前端 (Frontend)
- **框架**: Vue 3 + Vite
- **通信**: EventSource (实现 SSE 流式消息)

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd multi-task-qa-assistant01
```

### 2. 后端部署 (Backend)
1. **进入目录**：`cd Backend`
2. **准备资料**：将您的本地文档（如 .txt, .pdf 等）放入 `Backend/knowledge/` 文件夹。
3. **配置环境**：
   在 `Backend` 目录下新建或编辑 `.env` 文件：
   ```bash
   # DeepSeek 核心配置
   DEEPSEEK_API_KEY=你的DeepSeek_API_Key
   DEEPSEEK_API_BASE=https://api.deepseek.com

   # 应用配置
   APP_HOST=0.0.0.0
   APP_PORT=5000
   DEBUG=True

   # 数据库与知识库
   SQLITE_URL=sqlite:///chat_history.db
   KNOWLEDGE_BASE_DIR=knowledge
   VECTOR_DB_PATH=vector_db_index
   ```
4. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
5. **启动服务**：
   ```bash
   python app.py
   ```

### 3. 前端部署 (Frontend)
1. **进入目录**：`cd Frontend`
2. **安装依赖**：
   ```bash
   npm install
   ```
3. **启动开发服务器**：
   ```bash
   npm run dev
   ```
   默认启动地址：`http://localhost:5174`

---

## 📁 项目结构

```text
multi-task-qa-assistant01/
├── Backend/               # Python 后端
│   ├── src/
│   │   ├── tools/         # 插件化工具 (天气、新闻、股票、RAG)
│   │   ├── agent.py       # LangChain Agent 解析引擎
│   │   ├── config.py      # Pydantic 统一配置中心
│   │   ├── vector_db.py   # FAISS 向量库封装逻辑
│   │   ├── memory.py      # SQLite 会话持久化
│   │   └── llm.py         # LLM 选型初始化
│   ├── knowledge/         # 本地知识库源文档
│   ├── app.py             # FastAPI 入口
│   └── requirements.txt   # 依赖清单
├── Frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── components/    # UI 组件 (ChatWindow)
│   │   └── services/      # API 通信
│   └── package.json
└── README.md              # 项目文档
```

---

## 📝 注意事项

- **知识库更新**: 若新增了 `knowledge/` 目录下的资料，重启后端服务即可自动重新触发全量索引。
- **API 负载**: DeepSeek R1 会消耗更多 Token，请合理选择模型。

---

## 🤝 贡献与反馈
欢迎通过 Issue 提出宝贵的优化意见！