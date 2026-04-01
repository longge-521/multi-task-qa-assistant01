# Multi-Task QA Assistant (多任务智能问答助手) 🚀

这是一个基于 **DeepSeek LLM** 和 **LangChain** 打造的全栈智能助手。它集成了实时天气预报、热点新闻搜索、A 股涨停板查询等多种实用工具，并支持多模型（聊天模型与推理模型）的动态切换。

---

## 🌟 核心功能

- **多模型无缝切换**：
  - 🚀 **快速通道 (deepseek-chat)**：适用于日常流畅对话与快速工具调用。
  - 🧠 **智能搜索 (deepseek-reasoner/R1)**：启用深度思考模型，处理复杂逻辑与推理任务。
- **强大的工具扩展**：
  - ⛅ **实时天气**：支持城市搜索，若未提供位置则自动通过 IP 定位当前城市并展示天气。
  - 📰 **新闻资讯**：聚合搜索最近 24 小时热点，内置 Robust Fallback 机制（当专门新闻接口受限时自动切换全网搜索）。
  - 📈 **A 股助手**：支持自然语言日期查询（如“前天”、“上周五”），基于 AkShare 实时获取涨停股票列表，自动识别非交易日并回溯。
- **现代化 UI 体验**：
  - 基于 Vue 3 的深色科技感界面。
  - 动态能力卡片：支持点击触发预设查询，交互丝滑。
  - 工具调用回显：清晰展示 AI 在回答过程中使用了哪些后端工具。
- **会话持久化**：使用 SQLite 自动保存与每个用户的对话历史，支持断开重连。

---

## 🛠️ 技术栈

### 后端 (Backend)
- **核心框架**: Python 3.10+, Flask, LangChain
- **大模型**: DeepSeek API (Chat & Reasoner)
- **数据源**: 
  - 天气: Open-Meteo & IP-API
  - 新闻: DuckDuckGo (via `ddgs`)
  - 股票: AkShare (东方财富数据)
- **数据库**: SQLite (会话管理)

### 前端 (Frontend)
- **框架**: Vue 3 + Vite 4
- **样式**: Vanilla CSS (极简科技风)
- **通信**: Axios

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd multi-task-qa-assistant01
```

### 2. 后端配置 (Backend)
1. 进入后端目录：`cd Backend`
2. 创建并配置环境变量：
   在 `Backend` 目录下新建 `.env` 文件：
   ```env
   DEEPSEEK_API_KEY=你的DeepSeek_API_Key
   DEEPSEEK_API_BASE=https://api.deepseek.com
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 运行后端：
   ```bash
   python app.py
   ```
   默认运行在 `http://localhost:5000`

### 3. 前端配置 (Frontend)
1. 进入前端目录：`cd ../Frontend`
2. 安装依赖：
   ```bash
   npm install
   ```
3. 启动开发服务器：
   ```bash
   npm run dev
   ```
   默认访问地址：`http://localhost:5174`

---

## 📁 项目结构

```text
multi-task-qa-assistant01/
├── Backend/               # Flask 后端代码
│   ├── src/
│   │   ├── tools/         # 插件化工具集合 (天气、新闻、股票)
│   │   ├── agent.py       # LangChain Agent 逻辑
│   │   └── llm.py         # LLM 选型与初始化
│   ├── app.py             # 接口入口
│   └── .env               # 环境变量配置
├── Frontend/              # Vue 3 前端代码
│   ├── src/
│   │   ├── components/    # UI 组件 (ChatWindow)
│   │   └── services/      # API 通信层
│   └── package.json
└── README.md              # 本文档
```

---

## 📝 注意事项

- **API Key**: 请确保您的 DeepSeek 账户有足够余额以调用 `reasoner` 模型。
- **Network**: 新闻搜索功能依赖 DuckDuckGo，在部分网络环境下可能需要加速。
- **Stock Data**: 股票查询由 `akshare` 提供，依赖东方财富的实时接口，请在交易时间内或交易后合理查询。

---

## 🤝 贡献与反馈
如果有更好的想法或发现了 BUG，欢迎通过 Issue 或 Pull Request 与我交流！