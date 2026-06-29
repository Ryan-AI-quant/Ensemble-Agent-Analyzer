# Ensemble-Agent-Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

**多Agent框架集成的新闻舆情分析系统，支持短中长期影响评估与产业链的可视化**

[English Documentation](README.md)

</div>

---

### 项目概述

**Ensemble-Agent-Analyzer（集成Agent分析器）** 是一个多 Agent框架 集成系统，专注于智能新闻舆情分析。系统允许使用者根据自身偏好，从后台调用本地已部署好的 **OpenClaw** 或 **Hermes** 等 AI Agent，对新闻舆情进行深度分析。分析结果将输出该信息对未来 **短期、中期、长期** 的影响评估，以及涉及到的完整 **产业链** 结构。

#### 核心功能

- **多 Agent框架 后端支持**：根据用户偏好无缝切换 OpenClaw、Hermes或本地分析后端
- **AI 智能对话**：与选定的 AI Agent 进行自然语言交互，支持 WebSocket 流式响应和会话历史保存
- **智能新闻聚合**：多源 RSS 抓取，基于 AI 的重要性排序，支持分类过滤和搜索
- **产业链深度分析**：深度分析新闻事件对上游、中游、下游产业的影响，并以交互式图表展示
- **短中长期影响评估**：全面分析新闻事件的短期冲击、中期调整和长期结构性影响
- **交互式思维导图生成**：基于 ReactFlow 可视化产业链结构和新闻关联关系
- **AI 智能评分**：基于产业影响程度的智能评分（1-100分制）
- **响应式设计**：移动端友好界面，触摸优化导航，支持思维导图移动端查看

### 效果展示

![主界面](./docs/screenshots/main.png)
![产业链可视化](./docs/screenshots/mindmap.png)

### 系统架构

```
+---------------------------------------------------------------+
|                      用户浏览器                                |
|  +--------------+  +----------------------------------------+  |
|  |   侧边栏     |  |           主内容区域                     |  |
|  |  +-- 对话    |  |  +-------------+--------------------+   |  |
|  |  +-- 新闻    |  |  |   新闻列表   |     分析输出        |   |  |
|  |  +-- 设置    |  |  | (按重要性)   | (文本 + 思维导图)   |   |  |
|  +--------------+  +----------------------------------------+  |
+---------------------------------------------------------------+
                               |
                               v
+---------------------------------------------------------------+
|                   Python FastAPI 后端                         |
|  +----------+  +----------+  +------------+  +---------+     |
|  | Chat API |  | News API |  | MindMap API|  |WebSocket|     |
|  +----------+  +----------+  +------------+  +---------+     |
+---------------------------------------------------------------+
                               |
                               v
+---------------------------------------------------------------+
|                 多 Agent 框架引擎层                            |
|              OpenClaw / Hermes / 本地分析                     |
+---------------------------------------------------------------+
```

### 技术栈

#### 后端
- **框架**：Python FastAPI
- **多 Agent框架 引擎**：OpenClaw / Hermes / 本地分析（运行时可配置切换）
- **新闻处理**：RSS 解析
- **思维导图与产业链**：NetworkX 图算法
- **数据验证**：Pydantic

#### 前端
- **框架**：React 18 + TypeScript
- **构建工具**：Vite
- **样式**：Tailwind CSS
- **状态管理**：Zustand
- **数据获取**：TanStack Query (React Query)
- **可视化**：ReactFlow
- **HTTP 客户端**：Axios

### 快速开始

#### 前置要求

- Python 3.9+
- Node.js 16+
- npm 或 yarn
- 本地部署的 Agent框架（OpenClaw 或 Hermes）以启用完整的 AI 分析能力

> **重要提示**：启动后端之前，请确保你要调用的 AI Agent 的 Gateway 已经开启并可以访问。例如，若使用 OpenClaw，请确认 OpenClaw Gateway 已在配置的 URL 上运行（默认：`http://localhost:18789`）；若使用 Hermes，请确认 Hermes/Ollama 服务已在配置的 URL 上运行（默认：`http://localhost:8642`）。后端在收到分析请求时会尝试连接这些服务。

#### 1. 后端配置

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 文件配置您的 Agent框架

# 启动服务
python run.py
```

后端服务将运行在 http://localhost:8000

#### 2. 前端配置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将运行在 http://localhost:3000

#### 3. 访问应用

打开浏览器访问 http://localhost:3000

### API 文档

启动后端后，访问交互式 API 文档：http://localhost:8000/docs

#### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat/message` | POST | 发送聊天消息 |
| `/api/chat/ws/{session_id}` | WebSocket | WebSocket 聊天连接 |
| `/api/news/` | GET | 获取分页新闻列表 |
| `/api/news/{news_id}` | GET | 获取新闻详情 |
| `/api/mindmap/from-news/{news_id}` | GET | 从新闻生成思维导图 |
| `/api/mindmap/analyze-and-generate` | POST | 分析新闻并生成包含产业链的思维导图 |
| `/api/news/rate-with-agent` | POST | 使用 AI Agent 评分新闻重要性 |
| `/health` | GET | 健康检查 |

### 配置说明

#### 后端环境变量

```env
# 服务器配置
HOST=0.0.0.0
PORT=8000
BACKEND_TYPE=LOCAL  # HERMES, OPENCLAW, LOCAL

# OpenClaw 配置
OPENCLAW_API_URL=http://localhost:18789
OPENCLAW_API_KEY=your_api_key_here
OPENCLAW_MODEL=gpt-4

# Hermes 配置
HERMES_API_URL=http://localhost:8642
HERMES_API_KEY=your_api_key_here
HERMES_MODEL=llama3
HERMES_API_FORMAT=openai  

# 日志
LOG_LEVEL=info
```

#### 新闻源配置

新闻源在 `backend/news_sources.json` 中配置。用户需要在该文件中添加自定义的 RSS 地址：

```json
{
  "rss_sources": [
    {
      "name": "News name",
      "url": "news_url",
      "category": "news_category"
    }
  ]
}
```

> **说明**：用户需在 `backend/news_sources.json` 中手动添加所需的 RSS 订阅地址。其中 `category` 字段用于前端新闻分类过滤。

### 功能使用说明

#### 1. 多 Agent 选择与切换
- 点击侧边栏的"设置"
- 选择偏好的 AI Agent 类型：**OpenClaw**、**Hermes** 或 **本地分析**
- 自定义 LLM 模型名称（如 gpt-4、claude-3、llama3 等）
- 更改立即生效，无需重启服务

#### 2. AI 智能对话
- 点击侧边栏的"对话"开始聊天
- 对话使用选定的 Agent 后端进行智能响应
- 支持 REST API 和 WebSocket 实时流式传输
- 页面刷新后会话历史保留

#### 3. 智能新闻阅读与分析
- 浏览按 AI 计算的重要性排序的新闻列表
- 按分类过滤或搜索特定主题
- 悬停在新闻条目上查看详细预览
- **点击任意新闻条目**触发通过选定 Agent 的自动深度分析

#### 4. 短中长期影响评估
- 选择新闻后，系统从三个时间维度分析其影响：
  - **短期影响**：即时市场反应和直接效应
  - **中期影响**：过渡性调整和次级效应
  - **长期影响**：结构性和战略性变化
- 在右上方面板查看文字版分析结果

#### 5. 产业链可视化
- 在右下面板探索交互式思维导图，展示完整的产业链结构
- 可视化 **上游**（供应商/原材料）、**中游**（制造/加工）、**下游**（终端用户/市场）各环节产业
- 每个节点代表受新闻事件影响的特定行业或实体
- 支持缩放、平移和节点检视等交互操作

#### 6. AI 智能评分
- 点击新闻面板中的紫色"AI评分"按钮
- 等待 30-60 秒使用选定的 Agent 进行批量评分
- 新闻将按 AI 评估的重要性重新排序（1-100分制）
- 评分综合考虑产业影响，不仅限于关键词匹配

#### 7. 手动输入新闻
- 点击"输入新闻"按钮粘贴自定义内容
- 系统将自动分析并生成包含产业链的思维导图

### 移动端支持

本应用采用响应式设计，针对移动设备优化：
- 横向滚动侧边栏便于导航
- 小屏幕上的垂直堆叠布局
- 触摸优化的交互体验
- 分析文本和思维导图均支持滚动浏览

### 项目结构

```
ensemble-agent-analyzer/
|-- backend/                       # Python FastAPI 后端
|   |-- app/
|   |   |-- main.py               # 应用入口
|   |   |-- config.py             # 配置管理
|   |   |-- models/
|   |   |   |-- schemas.py        # Pydantic 数据模型
|   |   |-- routes/
|   |   |   |-- chat.py           # 聊天端点
|   |   |   |-- news.py           # 新闻端点
|   |   |   |-- mindmap.py        # 思维导图端点
|   |   |-- services/
|   |       |-- news_service.py            # 新闻聚合
|   |       |-- news_analysis_service.py   # AI 分析
|   |       |-- mindmap_service.py         # 思维导图生成
|   |       |-- hermes_service.py          # Hermes Agent 集成
|   |       |-- openclaw_service.py        # OpenClaw Agent 集成
|   |-- requirements.txt
|   |-- run.py                        # 启动脚本
|-- frontend/                     # React 前端
|   |-- src/
|   |   |-- components/
|   |   |   |-- Chat/              # 聊天组件
|   |   |   |-- Layout/            # 布局组件
|   |   |   |-- MindMap/           # 思维导图组件
|   |   |   |-- News/              # 新闻组件
|   |   |-- services/              # API 服务
|   |   |-- stores/                # Zustand 状态管理
|   |   |-- types/                 # TypeScript 类型
|   |   |-- App.tsx                # 主应用
|   |   |-- main.tsx               # 入口文件
|   |-- public/
|   |   |-- icon.png               # 浏览器图标
|   |   |-- icon2.jpg              # UI 图标
|   |-- package.json
|   |-- vite.config.ts
|-- README.md                     # 英文文档
|-- README_CN.md                  # 中文文档
|-- LICENSE                       # Apache License 2.0
```

### 开发指南

#### 后端开发

```bash
cd backend

# 自动重载运行
python run.py

# 或直接使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
cd frontend

# 开发模式，支持热重载
npm run dev

# 生产环境构建
npm run build

# 预览生产构建
npm run preview
```

### 测试

```bash
# 后端测试（如有）
cd backend
pytest

# 前端测试（如有）
cd frontend
npm test
```

### 许可证

本项目采用 Apache License 2.0 开源许可证 - 详见 [LICENSE](LICENSE) 文件。

```
Copyright 2024 Ensemble-Agent-Analyzer Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### 贡献指南

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 支持与反馈

如果您遇到问题或有疑问：
- 在 GitHub 上开启 Issue
- 查阅现有文档
- 查看 API 文档 http://localhost:8000/docs

### 致谢

- FastAPI 提供的优秀后端框架
- React 和活跃的前端生态系统
- OpenClaw 和 Hermes 社区的 AI Agent 技术
- ReactFlow 强大的图可视化库
- 所有为本项目做出贡献的用户

---

<div align="center">

**Ensemble-Agent-Analyzer**

**Made with love by the Ensemble-Agent-Analyzer Team**

</div>
