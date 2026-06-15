# DRG-Agent 后端说明

`server/` 是 DRG-Agent 的后端工程，基于 **FastAPI + LangGraph** 实现医保 DRG 入组、文档自动生成、测试用例生成与虚拟文档系统的 REST API。

---

## 1. 架构

后端采用自上而下的分层架构，上层依赖下层，下层不反向依赖上层。

```
HTTP 请求
  │
  ▼
API 路由层      app/api/v1/        56 个 REST 接口，JSON 统一响应 + Q&A NDJSON 流
  │
  ▼
服务层          app/services/      事务管理、输入校验、编排调用
  │
  ├─────────────▼
  │   智能体编排层  app/agents/    LangGraph StateGraph 工作流（入组/文档/测试）
  │                                ├ case_parser  病历解析智能体 (LLM)
  │                                ├ rule_retriever 规则检索
  │                                ├ grouping     DRG 入组智能体 (规则)
  │                                ├ explain      解释生成智能体 (LLM)
  │                                ├ document_gen 文档生成智能体 (LLM)
  │                                └ testcase_gen 测试用例生成智能体
  ▼
领域引擎层      app/engine/        DRG 规则引擎（纯 Python 确定性算法，不调用 LLM）
                                   code_validator / rule_parser / mdc_matcher /
                                   adrg_matcher / cc_mcc / drg_matcher / grouping_engine
  │
  ▼
基础设施层      app/core/          配置、数据库、日志、中间件、异常
                app/models/        SQLAlchemy ORM 模型（14 张表）
                app/llm/           LLM 客户端封装 + Prompt 模板
                app/tasks/         Celery 异步任务
```

**关键设计原则**

- **规则与 LLM 分离**：DRG 入组（MDC→ADRG→DRG）是 `app/engine/` 中的确定性算法，结果可复现、可审计；LLM 仅用于病历解析、解释润色、文档/测试用例生成等非关键路径。
- **统一响应**：普通 JSON 接口返回 `{ "code", "data", "message" }`，异常由全局处理器转换为同一结构；Q&A 流式接口按行返回 NDJSON 事件。
- **失败降级**：LLM 不可用时，解释生成与文档生成回退到模板化输出，核心入组不受影响。
- **问答流兼容**：Q&A 使用 NDJSON 流式返回结构化思考摘要和最终回答；旧非流式接口保留为连接启动失败时的兼容路径。系统不保存或展示模型原始思维链。

### 目录结构

```text
server/
├── app/
│   ├── api/v1/        # REST 路由：cases / rules / grouping / documents / testcases / tasks / system / logs
│   ├── agents/        # LangGraph 智能体与编排器 (orchestration.py)
│   ├── core/          # config / database / logging / middleware / exceptions
│   ├── engine/        # DRG 规则引擎（确定性算法）
│   ├── llm/           # LLM 客户端 + prompts/*.txt
│   ├── models/        # SQLAlchemy ORM 模型
│   ├── schemas/       # Pydantic 请求/响应模型（camelCase）
│   ├── services/      # 业务服务层
│   └── tasks/         # Celery 任务定义
├── data/rules/        # 内置演示规则文件 demo_rules.json（输入数据，保留原位）
├── migrations/        # Alembic 数据库迁移
├── tests/             # pytest 测试（test_engine / test_services / test_api / test_integration）
└── main.py            # FastAPI 应用入口

# 运行时产物统一存放于仓库根目录 ../documents/（generated / exports / reports）
```

---

## 2. 依赖与环境

| 项目 | 版本 / 说明 |
|------|------|
| Python | 3.12（由仓库根目录 `.mise.toml` 锁定） |
| 包管理 | [uv](https://docs.astral.sh/uv/)，依赖声明于根目录 `pyproject.toml` |
| 数据库 | PostgreSQL 16（Docker，`docker-compose.yml`） |
| 缓存/队列 | Redis 7（Docker） |
| 核心库 | FastAPI、SQLAlchemy 2（async）、Alembic、Pydantic 2、LangGraph、LangChain、OpenAI SDK、Celery、Loguru |

依赖安装（在**仓库根目录**执行）：

```bash
uv sync          # 创建 .venv 并安装全部依赖
```

### 环境变量

后端从仓库根目录的 `.env` 读取配置（`.env` 已被 gitignore）。复制模板并填写：

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | 大模型 API Key（DeepSeek，OpenAI 兼容） |
| `LLM_API_BASE` | `https://api.deepseek.com` |
| `LLM_MODEL` | `deepseek-chat` |
| `DATABASE_URL` | `postgresql+asyncpg://drgagent:drgagent_dev@localhost:5432/drg_agent` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `DOCUMENT_STORAGE_PATH` | 本地产物存储根目录（默认仓库根 `./documents`，含 generated/exports/reports） |

---

## 3. 启动

> 推荐使用仓库根目录的 `./start.sh` 一键启动（含 Docker + 后端 + 前端）。以下为后端单独启动步骤。

```bash
# 1. 启动 Docker 服务（仓库根目录）
docker compose up -d

# 2. 应用数据库迁移
cd server
../.venv/bin/alembic upgrade head

# 3. 启动 FastAPI 服务
../.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后：

- API 根路径：<http://localhost:8000>
- Swagger 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/system/health>

首次使用可初始化演示数据（导入规则 + 4 个样例病历）：

```bash
curl -X POST http://localhost:8000/api/v1/system/demo/init
```

### Celery 异步任务（可选）

文档与测试用例生成默认在请求内同步完成；如需通过 Celery 异步执行，另开终端：

```bash
cd server
../.venv/bin/celery -A app.tasks worker --loglevel=info
```

---

## 4. 关闭

- 单独启动的进程：在对应终端按 `Ctrl + C`。
- 通过 `./start.sh` 启动的：在仓库根目录执行 `./stop.sh`。
- 停止 Docker 服务（保留数据）：`docker compose stop`
- 彻底清理（删除容器与数据卷）：`docker compose down -v`

---

## 5. 测试

```bash
cd server

# 全部测试
../.venv/bin/python -m pytest tests/ -v

# 带覆盖率
../.venv/bin/python -m pytest tests/ --cov=app --cov-report=term-missing

# 仅规则引擎
../.venv/bin/python -m pytest tests/test_engine/ -v

# 代码风格检查
../.venv/bin/ruff check app/
```

测试使用独立的临时 SQLite 数据库与 Mock LLM 客户端，**不依赖**真实 PostgreSQL 或 DeepSeek API。当前共 126 个用例，规则引擎覆盖率约 89%。

---

## 6. 常见注意事项

- **`.env` 位置**：必须放在**仓库根目录**（不是 `server/`）。后端通过绝对路径定位它。
- **数据库未启动**：若 PostgreSQL 容器未运行，应用仍可启动，但 `/system/health` 会返回 `database: disconnected`。先执行 `docker compose up -d`。
- **迁移**：模型变更后需 `alembic revision --autogenerate -m "..."` 再 `alembic upgrade head`。应用启动时也会 `create_all` 作为兜底，但正式变更应走迁移。
- **LLM 不可达**：解释生成、文档生成会自动降级为模板化输出；DRG 入组为确定性规则匹配，不受影响。
- **文档/测试用例生成较慢**：真实 LLM 可能执行多轮源码工具调用。当前版本不限制工具调用轮次，也不设置固定请求超时；模型完成后才返回结果。
- **文档输出保护**：DeepSeek 偶尔返回的 DSML/工具协议会继续作为工具调用处理，无法解析的协议文本不会覆盖当前文档。
- **重复启动保护**：`start.sh` 会复用本项目已有进程；若 8000/5173 被其他程序占用则直接停止，不会启动重复 worker 或漂移到其他端口。
- **入组结果可复现**：`app/engine/` 为纯算法，相同输入必得相同 DRG；修改规则请改 `data/rules/demo_rules.json` 或重新导入规则版本。
- **端口占用**：后端默认 8000。若被占用，可改 `uvicorn ... --port <其它端口>`，并相应调整前端 Vite 代理 `web/vite.config.ts`。
- **CORS**：已允许 `http://localhost:5173`；前端开发走 Vite 代理时为同源，不触发 CORS。

---

## 7. 接口一览

56 个 REST 接口，前缀 `/api/v1`，分组：`cases`(7) / `rules`(7) / `grouping`(4) / `documents`(21) / `testcases`(8) / `tasks`(4) / `system`(4) / `logs`(1)。其中 Q&A 流式接口为 `POST /documents/qa/conversations/{conv_id}/messages/stream`，响应媒体类型为 `application/x-ndjson`。完整定义以运行时 Swagger 文档 `/docs` 为准；初始接口设计见 [plans/03_api_interfaces.md](../plans/03_api_interfaces.md)。
