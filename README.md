# Multi-Task QA Assistant

基于 **DeepSeek LLM** + **LangChain** 的全栈智能问答助手，集成 RAG 知识库管理、实时天气、新闻搜索、A 股涨停查询，原生支持 DeepSeek R1 推理可视化。

## 界面预览

<img width="2157" height="1248" alt="image" src="https://github.com/user-attachments/assets/1b3c308d-5430-479f-869b-d6931c82ab55" />


> 左侧：RAG 知识库管理面板（文档上传、解析、切块、向量化全流程）｜右侧：智能对话面板（可折叠工具抽屉 + 示例提问）

---

## 功能概览

### 智能对话

| 模式 | 模型 | 特点 |
|------|------|------|
| 快速 | `deepseek-chat` | 即时响应，适合日常问答与工具调用 |
| 智能搜索 | `deepseek-reasoner` | SSE 实时流式输出，展示 AI 的逐步思考过程 |

- Agent 自动识别意图并调用合适的工具
- 支持对话历史持久化（SQLite）
- 流式与非流式双通道

### 工具能力

| 工具 | 数据源 | 说明 |
|------|--------|------|
| 实时天气 | Open-Meteo + IP 定位 | 支持城市名 / 自动定位，分钟级天气实况 |
| 新闻搜索 | DuckDuckGo | 内置 403 容错回退，确保可用性 |
| A 股涨停 | AkShare | 支持自然语言日期（"昨天""上周五""3天前"） |
| 文档知识库 | FAISS / 本地向量库 | 语义检索，AI 回答附带来源引用 |

### RAG 知识库管理

完整的文档处理流水线，可视化操作界面：

```
上传文档 → 解析加载 → 文本切块 → 向量化 → 写入索引 → 语义检索
```

- **文档解析**：支持 PDF（PyMuPDF）、TXT、Word，可选 OCR（EasyOCR）
- **切块策略**：递归字符切分，可配置 chunk_size / overlap
- **嵌入方式**：密集（dense）/ 稀疏（sparse）/ 混合（hybrid）
- **向量模型**：HuggingFace BGE-M3（默认）/ OpenAI Embeddings，支持自定义维度
- **向量检索**：全库搜索或按文件筛选，支持相似度阈值过滤
- **一键流水线**：单步执行或全自动批处理

### 前端界面

- 全屏工作台布局，知识库管理 + 右侧可拉伸对话面板
- 可折叠工具抽屉，点击查看工具详情与示例提问
- 深色科技感 UI，响应式设计
- 文档切块/向量化预览、全屏查看、键盘导航

---

## 技术栈

### 后端

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| LLM | LangChain + DeepSeek API（ChatOpenAI 兼容） |
| 向量数据库 | FAISS（密集索引）+ BM25（稀疏索引） |
| 嵌入模型 | HuggingFace BGE-M3 / OpenAI Embeddings |
| 会话存储 | SQLite + SQLAlchemy |
| 文档解析 | PyMuPDF + EasyOCR |
| 数据源 | Open-Meteo / DuckDuckGo / AkShare |
| 配置管理 | Pydantic Settings + dotenv |

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3（Composition API） |
| 构建 | Vite |
| HTTP | Axios + Fetch（SSE 流式） |
| 样式 | Scoped CSS，深色主题 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- DeepSeek API Key（[获取](https://platform.deepseek.com/)）

### 1. 克隆项目

```bash
git clone <repository-url>
cd multi-task-qa-assistant01
```

### 2. 后端部署

```bash
cd Backend

# 配置环境变量
cp .env.template .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

服务默认运行在 `http://0.0.0.0:5000`

### 3. 前端部署

```bash
cd Frontend

# 安装依赖
npm install

# 开发模式
npm run dev
```

开发服务器默认运行在 `http://localhost:5174`

> 前端默认连接 `http://localhost:5000` 后端，如需修改请编辑 `Frontend/src/services/api.js` 中的 `baseURL`。

---

## 环境变量

在 `Backend/.env` 中配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | （必填） | DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com` | API 地址 |
| `APP_HOST` | `0.0.0.0` | 服务监听地址 |
| `APP_PORT` | `5000` | 服务端口 |
| `DEBUG` | `True` | 调试模式（热重载 + 详细日志） |
| `SQLITE_URL` | `sqlite:///chat_history.db` | 会话历史数据库 |
| `KNOWLEDGE_BASE_DIR` | `knowledge` | 知识库根目录 |
| `VECTOR_DB_PATH` | `vector_db_index` | 向量索引存储路径 |

---

## 项目结构

```
multi-task-qa-assistant01/
├── Backend/
│   ├── app.py                    # FastAPI 入口，所有 API 路由
│   ├── requirements.txt
│   ├── .env.template
│   ├── src/
│   │   ├── agent.py              # LangChain Agent 引擎（工具调用 + 流式推理）
│   │   ├── llm.py                # LLM / Embeddings 初始化 + 模型缓存
│   │   ├── config.py             # Pydantic 统一配置
│   │   ├── memory.py             # SQLite 会话历史
│   │   ├── schemas.py            # API 请求/响应模型
│   │   ├── vector_db.py          # 向量库管理器（协调各 service）
│   │   ├── tools/
│   │   │   ├── weather.py        # 实时天气（Open-Meteo + IP 定位）
│   │   │   ├── news.py           # 新闻搜索（DuckDuckGo + 403 回退）
│   │   │   ├── stock.py          # A 股涨停（AkShare + 自然语言日期）
│   │   │   └── rag_tool.py       # 知识库语义检索工具
│   │   └── services/
│   │       ├── load_service.py   # 文档加载（PDF/TXT/OCR）
│   │       ├── chunk_service.py  # 文本切块
│   │       ├── embedding_service.py  # 向量化（dense/sparse/hybrid）
│   │       └── index_service.py  # 索引构建与检索（FAISS/BM25）
│   └── knowledge/
│       ├── upload_doc/           # 原始上传文件
│       ├── load_doc/             # 解析后的结构化数据
│       ├── chunk_doc/            # 切块结果
│       ├── embedding_doc/        # 向量化结果
│       └── vector_store/         # 向量索引文件（FAISS）
│
├── Frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.vue               # 主布局（全屏工作台 + 可拉伸对话面板）
│       ├── main.js
│       ├── style.css             # 全局深色主题
│       ├── components/
│       │   ├── ChatWindow.vue    # 对话组件（流式消息 + 工具抽屉）
│       │   └── KnowledgeManager.vue  # 知识库管理面板
│       └── services/
│           ├── api.js            # Axios 基础配置
│           ├── chatService.js    # 对话 API
│           ├── loadService.js    # 文档加载 API
│           ├── chunkService.js   # 切块 API
│           ├── embeddingService.js  # 向量化 API
│           └── indexService.js   # 索引与检索 API
│
└── README.md
```

---

## API 接口

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/tools` | 获取可用工具列表 |
| `POST` | `/api/chat` | 非流式对话 |
| `POST` | `/api/chat/stream` | 流式对话（SSE） |

### 知识库管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/knowledge/upload` | 上传文档 |
| `GET` | `/api/knowledge/files` | 文件列表（可按阶段筛选） |
| `DELETE` | `/api/knowledge/files/{filename}` | 删除文档及关联数据 |
| `POST` | `/api/knowledge/parse/{filename}` | 解析文档 |
| `POST` | `/api/knowledge/chunk/{filename}` | 文本切块 |
| `POST` | `/api/knowledge/embedding/{filename}` | 向量化 |
| `POST` | `/api/knowledge/index/{filename}` | 写入向量索引 |
| `POST` | `/api/knowledge/pipeline/{filename}` | 一键全流程处理 |
| `POST` | `/api/knowledge/search` | 向量检索 |
| `GET` | `/api/knowledge/embedding/preview/{filename}` | 向量化预览 |
| `GET` | `/api/knowledge/files/{filename}/chunks` | 查看切块内容 |

---

## 常用命令

| 操作 | 命令 |
|------|------|
| 启动后端 | `cd Backend && python app.py` |
| 启动前端 | `cd Frontend && npm run dev` |
| 安装后端依赖 | `pip install -r Backend/requirements.txt` |
| 安装前端依赖 | `cd Frontend && npm install` |
| 构建前端生产包 | `cd Frontend && npm run build` |
| 重建向量索引 | 删除 `Backend/vector_db_index/` 后重启后端 |
| 查看后端日志 | `type Backend\app.log`（Windows）/ `tail -f Backend/app.log`（Linux） |

---

## 注意事项

- **知识库更新**：通过前端管理面板上传文档并执行处理流程，无需手动操作文件目录
- **模型开销**：`deepseek-reasoner` 会消耗更多 Token（含推理过程），日常使用建议选择"快速"模式
- **嵌入模型首次加载**：HuggingFace BGE-M3 模型首次运行会自动下载（约 2GB），后续使用缓存
- **支持的文档格式**：`.pdf`、`.txt`、`.md`、`.xlsx`、`.xls`、`.png`、`.jpg`（图片需开启 OCR）
- **向量检索一致性**：检索时会自动读取索引元数据，使用与建库时相同的嵌入模型，无需手动配置
- **CPU 密集操作**：文档解析、向量化等操作已异步化，不会阻塞其他 API 请求

---

## License

MIT
