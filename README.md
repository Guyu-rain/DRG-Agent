# DRG-Agent

医保 DRG 入组智能体系统 —— 基于大模型/智能体框架的多智能体协作平台。

## 项目简介

DRG-Agent 是一个面向医保 DRG（疾病诊断相关分组）入组场景的多智能体系统。系统接收电子病历和 DRG 入组规则，自动完成 ICD 编码解析、MDC/ADRG/DRG 三层分组推理、入组解释生成，并支持需求分析文档、概要设计文档、测试文档的自动生成与提交。

### 核心模块

| 模块 | 说明 |
|------|------|
| **DRG 入组智能体** | 根据电子病历和入组规则自动匹配输出 DRG 分组结果 |
| **文档自动生成智能体** | 基于系统需求/代码/设计信息自动生成工程文档 |
| **测试用例生成智能体** | 根据 DRG 规则自动构造正常/边界/异常测试用例 |
| **虚拟文档系统** | 文档存储、版本管理、检索和提交记录 |

### 项目结构

```
DRG-Agent/
├── plans/                  # 项目规划文档（技术栈、架构、接口、执行计划、分阶段开发）
├── server/                 # 后端 (FastAPI + LangGraph)，详见 server/README.md
│   ├── app/
│   │   ├── api/v1/         # REST API 路由
│   │   ├── core/           # 核心配置、数据库、中间件、异常
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务逻辑层
│   │   ├── agents/         # LangGraph 智能体定义
│   │   ├── engine/         # DRG 规则引擎（确定性算法）
│   │   ├── llm/            # LLM 调用封装与 Prompt 模板
│   │   └── tasks/          # Celery 异步任务
│   ├── migrations/         # Alembic 数据库迁移
│   └── tests/              # 后端测试
├── web/                    # 前端 (React + TypeScript + Ant Design)，详见 web/READMD.md
├── docker-compose.yml      # Docker 服务编排 (PostgreSQL + Redis)
├── start.sh / stop.sh      # 一键启动 / 停止脚本
└── README.md
```

---

## 开发环境搭建

### 前置依赖

以下工具需要在系统级别安装：

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| **fnm** | Node.js 版本管理 | `brew install fnm` (macOS) / `winget install Schniz.fnm` (Windows) |
| **mise** | Python/Java 版本管理 | `brew install mise` (macOS/Linux) |
| **uv** | Python 包管理 + venv | `brew install uv` (macOS) / `pip install uv` |
| **Docker Desktop** | PostgreSQL + Redis 服务 | [docker.com](https://www.docker.com/products/docker-desktop/) |

> **Windows 用户**: 推荐通过 WSL2 使用 mise，或使用 mise 的 Windows 原生支持。fnm 和 Docker Desktop 均原生支持 Windows。

### 首次准备

```bash
# 1. 克隆仓库
git clone <repo-url>
cd DRG-Agent

# 2. 安装运行时 (Node.js 22 + Python 3.12)
fnm install 22 && fnm use 22       # Node.js 22 LTS
mise install && mise trust         # Python 3.12 (读取 .mise.toml)

# 3. 启用 pnpm (通过 corepack)
corepack enable
corepack prepare pnpm@11.1.3 --activate

# 4. 安装依赖
uv sync                            # 后端：创建 .venv 并安装 Python 依赖
cd web && corepack pnpm install && cd ..   # 前端依赖

# 5. 配置环境变量 (填入 LLM API Key)
cp .env.example .env
```

### 一键启动（推荐）

完成首次准备后，在仓库根目录执行：

```bash
./start.sh      # 启动 Docker(PostgreSQL+Redis) + 后端 + 前端，并自动初始化演示数据
./stop.sh       # 停止全部服务（保留数据；./stop.sh --purge 彻底清理）
```

启动后访问：

- 前端界面：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>

### 手动分步启动

```bash
# 数据库服务
docker compose up -d

# 后端：迁移 + 启动
cd server
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

# (可选) Celery worker —— 文档/测试用例默认同步生成，不强制需要
../.venv/bin/celery -A app.tasks worker --loglevel=info

# 初始化演示数据
curl -X POST http://localhost:8000/api/v1/system/demo/init

# 前端（另开终端）—— 默认连接真实后端
cd web && corepack pnpm dev
```

> **前后端集成说明（Phase 3）**：前端默认通过 Vite 代理连接真实后端，无需 Mock。
> 若后端未就绪、仅需调试前端，可执行 `VITE_ENABLE_MSW=true corepack pnpm dev` 启用 MSW Mock。
> 详见 [server/README.md](server/README.md) 与 [web/READMD.md](web/READMD.md)。

### 版本锁定

| 文件 | 作用 |
|------|------|
| `.node-version` | 指定 Node.js 版本，fnm 自动切换 |
| `.mise.toml` | 指定 Python 版本，mise 自动切换 |
| `package.json` | `packageManager` 字段锁定 pnpm 版本 |
| `pyproject.toml` | Python 依赖声明，`uv.lock` 锁定精确版本 |
| `docker-compose.yml` | 锁定 PostgreSQL 16 + Redis 7 镜像版本 |

### 环境变量

复制 `.env.example` 为 `.env`，填写实际配置：

```bash
cp .env.example .env
```

需要填写的字段：
- `LLM_API_KEY`: 大模型 API Key
- `LLM_API_BASE`: API 地址
- `LLM_MODEL`: 模型名称

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | React 18 + TypeScript 5 |
| UI 组件库 | Ant Design 5 |
| 状态管理 | Zustand |
| 后端框架 | FastAPI (Python) |
| 智能体框架 | LangGraph + LangChain |
| ORM | SQLAlchemy 2 (async) |
| 数据库 | PostgreSQL 16 (Docker) |
| 缓存/队列 | Redis 7 (Docker) |
| 异步任务 | Celery |
| LLM SDK | OpenAI Python SDK |

详见 [plans/01_tech_stack.md](plans/01_tech_stack.md)

---

## 开发指南

### 代码规范

- **Python**: 遵循 PEP 8，使用 `ruff` lint，`mypy` 类型检查
- **TypeScript**: 严格模式，ESLint + Prettier
- **Git**: 遵循 Conventional Commits

### 常用命令

```bash
# Python 后端
uv run ruff check .               # Lint 检查
uv run mypy server/               # 类型检查
uv run pytest server/tests/       # 运行测试

# Node 前端
cd web
pnpm lint                         # Lint 检查
pnpm typecheck                    # 类型检查
pnpm test                         # 运行测试
```

### 清理环境

```bash
docker compose down -v            # 停止并删除数据库容器和数据卷
rm -rf .venv node_modules         # 删除项目依赖
mise deactivate                   # 卸载 mise shims
```

---

## 文档

**规划文档**

- [技术栈选型](plans/01_tech_stack.md)
- [系统架构设计](plans/02_architecture.md)
- [API 接口定义](plans/03_api_interfaces.md)
- [项目执行计划](plans/04_execution_plan.md)
- [数据模型设计](plans/05_data_model.md)
- [智能体工作流设计](plans/06_agent_workflow.md)

**分阶段开发文档**

- [Phase 1 · 后端开发](plans/development_phases/phase1_backend.md)
- [Phase 2 · 前端开发](plans/development_phases/phase2_frontend.md)
- [Phase 3 · 前后端集成](plans/development_phases/phase3_integration.md)

**子工程说明**

- [后端说明 server/README.md](server/README.md) —— 架构、依赖、启动、关闭、测试、注意事项
- [前端说明 web/READMD.md](web/READMD.md) —— 页面、状态管理、Mock、联调

---

## 团队

DRG-Agent 项目组 - Software Engineering 课程大作业
