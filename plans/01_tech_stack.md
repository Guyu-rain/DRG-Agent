# 技术栈选型

## 1. 总览

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| 前端框架 | React + TypeScript | 18.x / 5.x | 生态成熟，类型安全，组件化开发效率高 |
| UI 组件库 | Ant Design | 5.x | 中后台场景最佳选择，中文文档完善，可定制主题 |
| 前端构建 | Vite | 5.x | 开发启动快，HMR 即时生效 |
| 前端状态管理 | Zustand | 4.x | 轻量无模板，API 简洁，TS 支持好 |
| 前端路由 | React Router | 6.x | 标准方案 |
| 前端请求 | Axios | 1.x | 拦截器、超时、请求取消完善 |
| 后端框架 | FastAPI | 0.115+ | Python AI 生态原生支持，异步高性能，自动 OpenAPI 文档 |
| 后端验证 | Pydantic | 2.x | 与 FastAPI 深度集成，类型安全 |
| 后端 ORM | SQLAlchemy | 2.x | Python 生态标准 ORM，异步支持 |
| 数据库 | Docker PostgreSQL 16 | 16.x | Docker 容器化，零残留，工业级标准 |
| 数据库迁移 | Alembic | 1.x | SQLAlchemy 官方迁移工具 |
| 智能体框架 | LangGraph + LangChain | 0.2+ / 0.3+ | 示例 notebook 使用方案，支持有状态多智能体编排 |
| LLM SDK | OpenAI Python SDK | 1.x | 兼容 OpenAI API，可配置代理和多模型 |
| 异步任务 | Celery + Redis | 5.x / 7.x | 文档生成/测试生成等耗时任务异步化 |
| 文件存储 | 本地文件系统 + JSON 索引 | - | 课程演示场景无需外部存储服务 |
| 日志 | Loguru | 0.7+ | Python 日志库，简洁易用 |
| 测试 | Pytest + Vitest + Testing Library | 8.x / 3.x / 16.x | 后端单元/集成测试 + 前端组件与状态测试 |
| 代码质量 | Ruff + Mypy | 0.5+ / 1.x | 快速 lint + 类型检查 |

---

## 2. 前端技术栈详解

### 2.1 React + TypeScript

- **选择原因**: React 生态最完善，组件化开发天然适合 DRG-Agent 的多页面/多面板架构需求
- **TypeScript**: 严格模式，保证类型安全，减少运行时错误
- **组件规范**: 函数式组件 + Hooks，禁止 class 组件

### 2.2 Ant Design 5.x

- **选择原因**: 
  - 中后台场景（表单、表格、步骤条、抽屉）组件丰富
  - 中文文档友好，国内使用广泛
  - 5.x 支持 CSS-in-JS，主题定制灵活
  - 内置 ProTable/ProForm 等高级组件，加速开发
- **主题**: 使用 Ant Design 5.x 的 ConfigProvider 统一定制品牌色（#1F4E79 主色，与 SRS 文档一致）

### 2.3 状态管理：Zustand

- **选择原因**:
  - 比 Redux 更轻量，API 更直观
  - 不需要 Provider 包裹，直接使用 hook
  - 支持 slice 模式，适合按模块拆分状态（入组 / 文档 / 测试 / 配置）

### 2.4 前端项目结构

```
web/
├── src/
│   ├── components/          # 通用组件
│   │   ├── Layout/          # 布局组件
│   │   ├── Common/          # 公共组件（Loading、Empty、ErrorBoundary）
│   │   └── Business/        # 业务组件
│   ├── pages/               # 页面
│   │   ├── TaskCenter/      # 任务中心
│   │   ├── DRGGrouping/     # DRG 入组工作台
│   │   ├── RuleManagement/  # 规则管理
│   │   ├── DocumentSystem/  # 文档系统
│   │   ├── TestCase/        # 测试用例
│   │   ├── ExecutionLog/    # 执行日志
│   │   └── Settings/        # 系统配置
│   ├── stores/              # Zustand stores
│   ├── services/            # API 请求层
│   ├── hooks/               # 自定义 hooks
│   ├── types/               # TypeScript 类型定义
│   ├── utils/               # 工具函数
│   └── App.tsx
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 3. 后端技术栈详解

### 3.1 FastAPI

- **选择原因**:
  - Python 是 AI/LLM 生态的第一语言，LangGraph/LangChain 均为 Python 原生
  - 异步支持 (`async/await`) 天然适配 LLM API 调用（高延迟 IO）
  - 自动生成 OpenAPI 文档，前端可直接生成类型定义
  - Pydantic 深度集成，请求/响应自动校验
- **中间件**: CORS、请求日志、异常处理、认证

### 3.2 数据库：Docker PostgreSQL 16

- **方案**: Docker Compose 管理 PostgreSQL 16 容器，`docker compose up -d` 一键启动
- **优点**: 环境隔离，卸载无残留 (`docker compose down -v`)，工业级并发支持
- **连接**: SQLAlchemy 2.x 异步 + `asyncpg` 驱动
- **迁移**: Alembic 管理数据库版本，与 PostgreSQL 无缝配合

### 3.3 后端项目结构

```
server/
├── app/
│   ├── api/                 # API 路由
│   │   ├── v1/
│   │   │   ├── cases.py     # 病例子路由
│   │   │   ├── rules.py     # 规则子路由
│   │   │   ├── grouping.py  # 入组子路由
│   │   │   ├── documents.py # 文档子路由
│   │   │   ├── testcases.py # 测试用例子路由
│   │   │   ├── tasks.py     # 任务子路由
│   │   │   └── system.py    # 系统配置子路由
│   │   └── deps.py          # 依赖注入
│   ├── core/                # 核心配置
│   │   ├── config.py        # 应用配置（pydantic Settings）
│   │   ├── security.py      # 认证与权限
│   │   └── database.py      # 数据库引擎与会话
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 业务逻辑层
│   │   ├── case_service.py
│   │   ├── rule_service.py
│   │   ├── grouping_service.py
│   │   ├── document_service.py
│   │   └── testcase_service.py
│   ├── agents/              # 智能体定义
│   │   ├── orchestration.py # AgentOrchestrator 编排器
│   │   ├── case_parser.py   # 病历解析智能体
│   │   ├── rule_retriever.py# 规则检索智能体
│   │   ├── grouping.py      # DRG 入组智能体
│   │   ├── explain.py       # 解释生成智能体
│   │   ├── document_gen.py  # 文档生成智能体
│   │   ├── testcase_gen.py  # 测试用例生成智能体
│   │   └── submit.py        # 文档提交智能体
│   ├── engine/              # DRG 规则引擎（确定性逻辑，不用 LLM）
│   │   ├── rule_parser.py   # 规则文件解析
│   │   ├── mdc_matcher.py   # MDC 匹配
│   │   ├── adrg_matcher.py  # ADRG 匹配
│   │   ├── cc_mcc.py        # MCC/CC 判定与排除表
│   │   └── code_validator.py# 编码格式校验
│   ├── llm/                 # LLM 调用封装
│   │   ├── client.py        # LLM 客户端（重试、超时、降级）
│   │   └── prompts/         # Prompt 模板
│   └── tasks/               # Celery 异步任务
├── migrations/              # Alembic 迁移文件
├── data/                    # 数据文件
│   ├── rules/               # DRG 规则文件
│   ├── samples/             # 样例病历
│   └── demo/                # 演示数据初始化脚本
├── documents/               # 生成的文档存储
│   ├── requirements/
│   ├── design/
│   ├── testing/
│   ├── management/
│   └── configuration/
├── requirements.txt
├── alembic.ini
└── main.py                  # FastAPI 入口
```

---

## 4. 智能体框架详解

### 4.1 LangGraph 核心概念

```
StateGraph → State (TypedDict) → Nodes (智能体) → Edges (流转) → Conditional Edges (分支)
```

- **State**: 贯穿工作流的共享状态对象
- **Node**: 一个智能体或处理函数，接收 State 返回部分 State
- **Edge**: 节点间的顺序流转
- **Conditional Edge**: 根据条件分支到不同节点
- **Send**: 并行分发到多个节点（如多科室并行会诊）

### 4.2 LangGraph vs 纯 LangChain

- LangGraph 更适合本项目的理由:
  - 入组流程有明确的条件分支（编码有效？命中 MDC？有无 MCC？）
  - 文档生成/测试生成可以与入组流程解耦，通过事件触发
  - 支持并行执行（病历解析 + 规则检索可并行）

### 4.3 LLM 调用策略

- **API 代理**: 支持配置 `api_base`，适配国内环境
- **多模型**: 主模型用 deepseek-v3（性价比高），复杂任务可切换到 gpt-4
- **重试机制**: 3 次重试，指数退避 (1s, 2s, 4s)
- **降级策略**: 生成类任务失败时使用模板化输出
- **Token 限制**: 控制 prompt 长度，超长病历分段处理

---

## 5. 关键设计决策

### 5.1 DRG 入组必须规则驱动，不能 LLM 自由生成

- `server/app/engine/` 目录实现纯 Python 规则匹配引擎
- LLM 仅用于: 病历解析（NLP 提取编码）、解释文本润色、文档生成
- 核心论断：规则匹配结果必须可复现、可审计

### 5.2 前后端分离 + RESTful API

- 前端独立开发，通过 API 与后端通信
- 后端不返回 HTML，仅返回 JSON
- 便于团队分工（前端/后端/算法）

### 5.3 异步任务处理

- 入组推理同步返回（<5 秒，需求 NFR-05）
- 文档生成、测试用例生成通过 Celery 异步执行
- 前端通过轮询或 SSE 获取任务进度

### 5.4 安全与配置

- API Key 通过 `.env` 文件管理，不提交代码仓库
- 演示数据使用脱敏样例
- `.env.example` 提供配置模板

---

## 6. 开发环境要求

| 工具 | 版本 | 版本管理 |
|------|------|----------|
| Python | 3.12 | mise (`.mise.toml`) |
| Node.js | 22 LTS | fnm (`.node-version`) |
| pnpm | 11.x | corepack (`package.json`) |
| uv | 0.11+ | Homebrew |
| Docker | 27+ | Docker Desktop |
| Git | ≥ 2.x | 系统自带 |

### 环境变量 (.env.example)

```bash
# LLM 配置
LLM_API_KEY=sk-xxxxxxxx
LLM_API_BASE=https://openkey.cloud/v1
LLM_MODEL=deepseek-v3

# 数据库 (Docker PostgreSQL)
DATABASE_URL=postgresql+asyncpg://drgagent:drgagent_dev@localhost:5432/drg_agent

# Redis (Docker Redis)
REDIS_URL=redis://localhost:6379/0

# 文件存储
DOCUMENT_STORAGE_PATH=./server/documents

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 7. 技术栈风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LangGraph 版本 API 不稳定 | 智能体代码需要适配 | 锁定版本，避免自动升级 |
| LLM API 不可用 | 系统核心功能无法运行 | 规则引擎独立于 LLM；文档生成有模板降级 |
| 前端状态管理复杂 | 开发效率降低 | 仅使用 Zustand，避免过度状态拆分 |
| PostgreSQL 容器未启动 | 数据库不可用 | docker-compose.yml 内置健康检查 + 自动重启策略 |
