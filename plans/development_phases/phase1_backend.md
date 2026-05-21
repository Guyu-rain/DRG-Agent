# Phase 1: 后端开发 + 测试验证

## 总览

**目标**: 完成所有后端基础设施、DRG 规则引擎、智能体编排、REST API 和单元测试，确保后端可独立运行和验证。

**前置条件**: 
- Docker PostgreSQL + Redis 已启动 (`docker compose up -d`)
- Python 3.12 虚拟环境已激活 (`.venv/`)
- 所有 Python 依赖已安装 (`uv sync`)

**完成的标志**: 
- `uv run pytest server/tests/ -v` 全部通过
- `curl http://localhost:8000/api/v1/system/health` 返回 healthy
- 课程示例病历 `A01.002+G01* + J96.0 + 38.1000x002` 返回 `MDCB → BB1 → BB11`
- 所有 API 接口的 Swagger 文档 (`/docs`) 可访问和交互

---

## Step 1: 数据库模型与迁移 (ORM Layer)

**参照文档**: `plans/05_data_model.md`

### 1.1 实现 SQLAlchemy ORM 模型

创建 `server/app/models/` 下的所有模型文件：

| 文件 | 模型类 | 参照 |
|------|--------|------|
| `case.py` | `PatientCase` | 05_data_model.md §2.1 |
| `rule.py` | `RuleVersion` | 05_data_model.md §2.4 |
| `grouping.py` | `GroupingTask`, `GroupingResult`, `TaskStep` | 05_data_model.md §2.5-2.7 |
| `document.py` | `Document`, `DocumentVersion`, `DocumentTask` | 05_data_model.md §2.8-2.10 |
| `testcase.py` | `TestCase`, `TestTask` | 05_data_model.md §2.11-2.12 |
| `log.py` | `ExecutionLog` | 05_data_model.md §2.13 |
| `config.py` | `SystemConfig` | 05_data_model.md §2.14 |

**要求**:
- 所有模型继承 `server/app/core/database.py` 中的 `Base`
- 使用 `generate_id(prefix)` 函数生成带日期和随机后缀的唯一 ID (如 `CASE-20260521-A1B2C3`)
- JSON 字段使用 `sqlalchemy.JSON` 类型
- 枚举字段使用 Python `enum.Enum` + `sqlalchemy.Enum`
- 日期时间字段使用 `datetime.now(timezone.utc)` 作为默认值
- 关系字段使用 `relationship()` 和 `back_populates`

**验收**:
- [ ] 所有 14 个核心数据实体模型已定义
- [ ] `python -c "from app.models import *"` 无报错
- [ ] 每个模型可通过 `Base.metadata.create_all()` 在 PostgreSQL 中建表
- [ ] Procedure 模型包含 `level: int?` 字段 (手术级别)

### 1.2 配置 Alembic 并生成初始迁移

```bash
cd server
alembic init migrations
# 修改 alembic.ini 中的 sqlalchemy.url
# 修改 migrations/env.py 导入 Base 和所有模型
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**验收**:
- [ ] `alembic upgrade head` 成功在 PostgreSQL 中创建所有表
- [ ] `docker exec drg-agent-postgres psql -U drgagent -d drg_agent -c "\dt"` 列出所有表

---

## Step 2: DRG 规则引擎 (Core Domain Logic)

**参照文档**: `plans/02_architecture.md` §3, `plans/06_agent_workflow.md` §2.3.5

**核心原则**: 此模块为纯 Python 确定性算法，不调用 LLM，不依赖数据库 ORM 之外的任何外部服务。所有逻辑必须可单元测试。

### 2.1 CodeValidator — 编码格式校验

文件: `server/app/engine/code_validator.py`

```python
def validate_icd_format(code: str) -> bool:
    """验证 ICD 诊断编码格式。字母+数字+可选符号(. / + *)"""
    
def validate_icd_cm3_format(code: str) -> bool:
    """验证 ICD-CM-3 手术编码格式。数字+可选字母+可选x+数字"""
    
def validate_case_codes(parsed_case: dict) -> dict:
    """对结构化病历所有编码进行批量校验，返回 errors 和 warnings 列表"""
```

**要求**:
- 正则表达式校验，不能假阳性/假阴性
- 支持课程示例格式: `A01.002+G01*`, `J96.0`, `38.1000x002`
- 空值返回明确错误信息

**验收**:
- [ ] `validate_icd_format("A01.002+G01*")` → `True`
- [ ] `validate_icd_format("ZZZ999")` → `True` (仅格式校验，不查词表)
- [ ] `validate_icd_format("")` → `False`，错误信息 "编码为空"
- [ ] `validate_icd_cm3_format("38.1000x002")` → `True`
- [ ] `validate_icd_cm3_format("INVALID")` → `False`

### 2.2 RuleParser — 规则文件解析

文件: `server/app/engine/rule_parser.py`

```python
def parse_rule_file(file_path: str) -> dict:
    """解析 DRG 规则文件（Excel/CSV），返回结构化规则字典。
    
    Returns:
        {
            "mdc_list": [{code, name, icd_prefixes}],
            "adrg_list": [{code, name, mdc, surgery_list, diagnosis_list}],
            "drg_list": [{code, name, adrg, cc_level}],
            "mcc_list": [{code, name, level}],
            "cc_list": [{code, name, level}],
            "exclusion_table": [{diag_code, excluded_by}]
        }
    """

def build_rule_index(parsed_rules: dict) -> dict:
    """将解析后的规则构建为内存索引结构（哈希表），加速匹配。
    
    Returns:
        {
            "icd_to_mdc": {icd_prefix: mdc_code},   # 如 "A01": "MDCB"
            "mdc_surgeries": {mdc_code: [procedure_codes]},
            "mcc_set": {diag_code},                  # 快速查找
            "cc_set": {diag_code},
            "exclusion_map": {diag_code: [excluded_by_codes]},
            "adrg_drg_map": {adrg_code: [{cc_level, drg_code, name}]}
        }
    """
```

**要求**:
- 支持 Excel (.xlsx/.xls) 和 CSV 格式
- 解析失败时不崩溃，返回 `parse_errors` 列表
- `build_rule_index` 的输出必须是 O(1) 查找的数据结构
- 规则文件首次启动时导入，可存在数据库的 `RuleVersion` JSON 字段中

**验收**:
- [ ] 解析 DRG 2.0 课程示例规则文件成功
- [ ] `rule_counts.mdc >= 1` (至少包含 MDCB)
- [ ] `parse_rule_file("nonexistent.xlsx")` 返回 `parse_errors` 而非抛异常
- [ ] 生成的索引中 `icd_to_mdc["A01"] == "MDCB"`

### 2.3 MDC Matcher — MDC 匹配

文件: `server/app/engine/mdc_matcher.py`

```python
def match_mdc(primary_diag_code: str, rule_index: dict) -> dict:
    """根据主诊断 ICD 编码匹配 MDC。
    
    Returns:
        成功: {"code": "MDCB", "name": "神经系统疾病及功能障碍", "evidence": {...}}
        失败: {"code": None, "reason": "主诊断 Z99.9 无法匹配任何 MDC"}
    """
```

**要求**:
- 使用 `rule_index.icd_to_mdc` 进行前缀匹配
- 匹配失败时返回候选 MDC 列表（供人工复核或 LLM 辅助建议）
- 证据链记录命中的 ICD 前缀和规则条目

**验收**:
- [ ] `match_mdc("A01.002+G01*")` → `MDCB`
- [ ] `match_mdc("Z99.9")` → `None`，reason 非空
- [ ] 前缀匹配逻辑正确: ICD `A01.0` 应能匹配前缀 `A01`

### 2.4 ADRG Matcher — ADRG 匹配

文件: `server/app/engine/adrg_matcher.py`

```python
def match_adrg(mdc_code: str, primary_diag_code: str, primary_proc_code: str | None, rule_index: dict) -> dict:
    """在指定 MDC 下匹配 ADRG。
    
    Returns:
        成功: {"code": "BB1", "name": "神经系统复合手术", "evidence": {...}}
        失败: {"code": None, "reason": "..."}
    """
```

**要求**:
- 支持手术类 ADRG 和非手术类 ADRG 的区分
- 支持规则优先级（当一个病例可能命中多个 ADRG 时）
- 无手术编码时尝试匹配内科类 ADRG

**验收**:
- [ ] `match_adrg("MDCB", "A01.002+G01*", "38.1000x002")` → `BB1`
- [ ] 无手术编码时返回内科 ADRG 候选

### 2.5 CCMCC Service — MCC/CC 判定与排除表

文件: `server/app/engine/cc_mcc.py`

```python
def evaluate_cc_mcc(secondary_diag_codes: list[str], primary_diag_code: str, rule_index: dict) -> dict:
    """评估并发症等级。
    
    Returns:
        {
            "level": "MCC" | "CC" | "NONE",
            "matched_codes": [{code, level}],
            "excluded_codes": [{code, reason}],
            "warnings": [...]
        }
    """

def check_exclusion(diag_code: str, primary_diag_code: str, rule_index: dict) -> bool:
    """检查次要诊断是否被主诊断的排除表排除。"""
```

**要求**:
- 先查 MCC 列表，再查 CC 列表，取最高级别
- 排除表检查必须在 MCC/CC 匹配之后，对命中的编码逐一检查
- 如果所有 MCC/CC 都被排除，level 应返回 `NONE`
- 警告信息应区分 "不在列表" 和 "被排除"

**验收**:
- [ ] `evaluate_cc_mcc(["J96.0"], "A01.002+G01*")` → `level="MCC"`, excluded_codes 为空
- [ ] 当 MCC 被主诊断排除时 → `level="NONE"`, matched_codes 为空, excluded_codes 包含排除原因
- [ ] `evaluate_cc_mcc([], "...")` → `level="NONE"`

### 2.6 GroupingEngine — 入组引擎集成

文件: `server/app/engine/grouping_engine.py`

```python
class GroupingEngine:
    """DRG 入组引擎，整合所有匹配步骤。"""
    
    def __init__(self, rule_index: dict):
        self.rule_index = rule_index
        self.mdc_matcher = MDCModule(rule_index)
        self.adrg_matcher = ADRGModule(rule_index)
        self.cc_mcc_service = CCMCCModule(rule_index)
        self.drg_matcher = DRGModule(rule_index)
    
    def group(self, parsed_case: dict) -> GroupingResult:
        """执行完整的 MDC→ADRG→DRG 入组。
        
        步骤:
        1. 编码格式校验 (CodeValidator)
        2. MDC 匹配 (mdc_matcher)
        3. ADRG 匹配 (adrg_matcher)
        4. MCC/CC 判断 (cc_mcc_service)
        5. DRG 分组 (drg_matcher)
        6. 证据链构建
        """
```

**要求**:
- 集成上述所有组件，按顺序执行
- 任何一步失败，后续步骤应优雅处理并记录原因
- 输出 GroupingResult 包含完整证据链
- 候选 DRG 列表包含命中/未命中的原因

**验收**:
- [ ] **课程示例回归测试**: 主诊断 `A01.002+G01*`, 次要诊断 `J96.0`, 主要手术 `38.1000x002`，输出 `MDCB → BB1 → BB11`，证据链 5 步完整
- [ ] 缺少主诊断 → 返回 `is_grouped=False`, `stage="mdc_matching"`
- [ ] MCC 被排除 → 正确降级到不伴合并症的 DRG

### 2.7 规则引擎单元测试

文件: `server/tests/test_code_validator.py`, `test_rule_parser.py`, `test_mdc_matcher.py`, `test_adrg_matcher.py`, `test_cc_mcc.py`, `test_grouping_engine.py`

**要求**:
- 每个模块至少 5 个测试用例
- 包含正常、边界、异常场景
- 课程示例作为核心回归用例
- 使用 pytest fixtures 加载预定义规则索引

**验收**:
- [ ] `uv run pytest server/tests/test_engine/ -v` 全部通过
- [ ] 覆盖率 ≥ 80% (规则引擎模块)

---

## Step 3: LLM 客户端封装

**参照文档**: `plans/06_agent_workflow.md` §7

文件: `server/app/llm/client.py`

```python
class LLMClient:
    def __init__(self):
        openai.api_key = settings.LLM_API_KEY
        openai.api_base = settings.LLM_API_BASE
    
    def call(self, prompt: str, model: str = None, temperature: float = 0.3,
             max_tokens: int = 4096, max_retries: int = 3) -> str:
        """调用 LLM，支持重试和指数退避。"""
    
    def call_with_fallback(self, prompt: str, fallback_value: str = None) -> str:
        """调用 LLM，失败时返回降级值。"""
```

**要求**:
- 重试策略: 3 次，指数退避 (1s, 2s, 4s)
- 超时时间: 从 `settings.LLM_TIMEOUT` 读取 (默认 60s)
- 错误日志: 使用 Loguru 记录每次调用和错误
- 测试模式: 提供 `MockLLMClient` 用于测试，返回预定义响应

**验收**:
- [ ] `LLMClient.call("Hello")` 返回非空字符串
- [ ] 模拟 API 不可达时，3 次重试后抛出异常
- [ ] `call_with_fallback("...", fallback="备用文本")` 在失败时返回 `"备用文本"`
- [ ] Loguru 日志中有完整的调用记录

### 3.1 Prompt 模板管理

文件: `server/app/llm/prompts/` 目录下的 `.txt` 文件

| 文件 | 用途 | 参照 |
|------|------|------|
| `case_parse.txt` | 从自由文本提取结构化编码 | 06_agent_workflow.md §2.3.1 |
| `explain_success.txt` | 入组成功时的自然语言解释 | 06_agent_workflow.md §2.3.6 |
| `explain_failure.txt` | 入组失败时的原因说明 | 06_agent_workflow.md §2.3.6 |
| `document_srs.txt` | 需求分析文档生成 | 06_agent_workflow.md §3.4 |
| `document_design.txt` | 概要设计文档生成 | 06_agent_workflow.md §3.4 |
| `document_test.txt` | 测试文档生成 | 06_agent_workflow.md §3.4 |
| `testcase_generate.txt` | 测试用例生成 | 06_agent_workflow.md §4.4 |

**要求**:
- 每个 prompt 使用 Python `string.Template` 或 `str.format()` 替换变量
- 在 prompt 中明确输出 JSON 格式要求
- 在 prompt 中限制字数/Token 消耗

---

## Step 4: Pydantic Schemas

**参照文档**: `plans/03_api_interfaces.md`, `plans/05_data_model.md`

文件: `server/app/schemas/` 目录下

| 文件 | 包含的 Schema 类 |
|------|-----------------|
| `case.py` | `CaseCreate`, `CaseParseResult`, `CaseValidateResult`, `CaseSummary`, `CaseDetail`, `DiagnosisSchema`, `ProcedureSchema` |
| `rule.py` | `RuleImportRequest`, `RuleVersionSummary`, `RuleVersionDetail`, `MDCSchema`, `ADRGSchema`, `DRGSchema`, `CCMCCEntrySchema` |
| `grouping.py` | `GroupingExecuteRequest`, `GroupingTaskResponse`, `GroupingResultResponse`, `GroupingResultDetail`, `EvidenceItem`, `CandidateRule`, `BatchGroupingRequest` |
| `document.py` | `DocumentGenerateRequest`, `DocumentTaskResponse`, `DocumentPreviewResponse`, `DocumentEditRequest`, `DocumentSummary`, `DocumentDetail`, `DocumentStatusUpdate`, `DocumentSection` |
| `testcase.py` | `TestGenRequest`, `TestTaskResponse`, `TestCaseSummary`, `TestCaseDetail`, `TestExportRequest`, `TestSubmitRequest` |
| `task.py` | `TaskSummary`, `TaskDetail`, `TaskStepDetail` |
| `system.py` | `SystemConfigResponse`, `LLMConfigSchema`, `StorageConfigSchema`, `DemoInitResponse`, `HealthCheckResponse` |
| `common.py` | `APIResponse[T]`, `PaginationResponse[T]`, `PaginationParams` |

**要求**:
- 所有 schema 继承 `pydantic.BaseModel`
- 使用 `pydantic.Field()` 添加描述和校验
- 枚举类型使用 `str, Enum` 组合
- 分页响应统一使用 `PaginationResponse[T]` 泛型

**验收**:
- [ ] 每个请求 body 对应的 schema 可以正确反序列化 API 文档中的示例 JSON
- [ ] 必填字段缺失时 pydantic 自动报错
- [ ] `python -c "from app.schemas import *"` 无报错

---

## Step 5: 智能体 (Agent) 实现

**参照文档**: `plans/06_agent_workflow.md` §2-4

### 5.1 智能体列表

| 智能体 | 文件 | 类型 | 核心函数 |
|--------|------|------|----------|
| 病历解析智能体 | `agents/case_parser.py` | LLM | `case_parse_agent(state) → parsed_case` |
| 规则检索智能体 | `agents/rule_retriever.py` | Rule+LLM | `rule_retrieve_agent(state) → candidates` |
| DRG 入组智能体 | `agents/grouping.py` | Rule | `drg_group_agent(state) → grouping_result` |
| 解释生成智能体 | `agents/explain.py` | LLM | `explain_agent(state) → explanation` |
| 文档生成智能体 | `agents/document_gen.py` | LLM+Template | 生成各类工程文档 |
| 测试用例生成智能体 | `agents/testcase_gen.py` | LLM+Rule | 构造测试场景和用例 |
| 文档提交智能体 | `agents/submit.py` | Rule | 存入虚拟文档系统 |

### 5.2 AgentOrchestrator (核心编排器)

文件: `server/app/agents/orchestration.py`

```python
class AgentOrchestrator:
    """管理所有 LangGraph 工作流的构建、编译和执行。
    
    三个主要工作流:
    1. build_grouping_workflow() → 入组工作流
    2. build_document_gen_workflow() → 文档生成工作流  
    3. build_test_gen_workflow() → 测试用例生成工作流
    """
```

**要求**:
- 每个工作流使用 LangGraph `StateGraph` 构建
- 条件分支在入组工作流中: `is_valid_route()` 和 `is_grouped_route()`
- 异步工作流 (文档/测试) 通过 Celery 任务调用而不是 API 同步执行
- 所有 agent 节点返回 partial state 更新

**验收**:
- [ ] 入组工作流可从 raw_text 到最终 explanation 完整执行
- [ ] 编码无效时工作流正确走向异常分支
- [ ] 文档生成工作流和测试生成工作流可独立调用
- [ ] 每个 agent 调用失败时，工作流不崩溃，记录 error 到 state

---

## Step 6: 服务层 (Services)

**参照文档**: `plans/02_architecture.md` §2.2, `plans/03_api_interfaces.md`

文件: `server/app/services/`

| 文件 | 服务类 | 核心方法 |
|------|--------|----------|
| `case_service.py` | `CaseService` | `create_case`, `parse_case`, `validate_case`, `get_case`, `get_cases`, `update_case`, `delete_case`, `_normalize_case_input` (中文字段映射 + 去重) , `import_from_example` (导入 example/*.json 格式) |
| `rule_service.py` | `RuleService` | `import_rules`, `get_versions`, `get_version_detail`, `activate_version`, `delete_version`, `search_rules` |
| `grouping_service.py` | `GroupingService` | `execute_grouping`, `get_grouping_result`, `get_tasks`, `batch_grouping` |
| `document_service.py` | `DocumentService` | `generate_document`, `get_document`, `preview_document`, `edit_document`, `submit_document`, `get_documents`, `export_document`, `update_status` |
| `testcase_service.py` | `TestCaseService` | `generate_testcases`, `get_testcases`, `get_testcase`, `export_testcases`, `submit_to_documents` |
| `task_service.py` | `TaskService` | `get_tasks`, `get_task_detail`, `cancel_task` |
| `system_service.py` | `SystemService` | `get_config`, `update_config`, `init_demo_data`, `health_check` |

**要求**:
- 服务层负责事务管理、输入校验、权限检查（如有）
- 服务方法调用 AgentOrchestrator 或规则引擎
- 数据库操作通过 SQLAlchemy async session 执行
- 所有异步方法必须使用 `async/await`
- `CaseService` 内置 `_normalize_case_input()` 处理中文字段名映射 (如 `疾病编码` → `code`, `手术级别` → `level`)，支持 `example/drg_example.json` 格式导入
- 导入时自动去重完全相同的诊断和手术记录 (基于 `code` 字段)

**验收**:
- [ ] 每个 service 方法有对应的单元测试
- [ ] 数据库操作使用测试数据库 (test fixture)
- [ ] 异常情况有明确的错误处理
- [ ] `example/drg_example.json` 中的 3 个病例可成功导入

---

## Step 7: REST API 路由

**参照文档**: `plans/03_api_interfaces.md`, `plans/02_architecture.md` §2.1

文件: `server/app/api/v1/` 目录下

| 文件 | 路由前缀 | 接口数量 | 参照 API 文档 |
|------|---------|----------|--------------|
| `cases.py` | `/api/v1/cases` | 7 个 | §2.1-2.7 |
| `rules.py` | `/api/v1/rules` | 6 个 | §3.1-3.6 |
| `grouping.py` | `/api/v1/grouping` | 5 个 | §4.1-4.5 |
| `documents.py` | `/api/v1/documents` | 11 个 | §5.1-5.11 |
| `testcases.py` | `/api/v1/testcases` | 6 个 | §6.1-6.6 |
| `tasks.py` | `/api/v1/tasks` | 3 个 | §7.1-7.3 |
| `system.py` | `/api/v1/system` | 4 个 | §8.1-8.4 |
| `logs.py` | `/api/v1/logs` | 1 个 | §9.1 |

**要求**:
- 所有接口的请求体、响应体必须与 `plans/03_api_interfaces.md` 完全一致
- 统一使用 `APIResponse[T]` 包装响应: `{"code": 200, "data": ..., "message": "success"}`
- 路由参数使用 FastAPI path parameters (如 `{caseId}`)
- 查询参数使用 FastAPI query parameters (如 `?page=1&pageSize=20`)
- 表单上传使用 `fastapi.UploadFile`
- 异常处理使用 FastAPI exception handlers
- 在 APIRouter 上使用 `dependencies=[Depends(get_db)]` 注入数据库会话

**验收**:
- [ ] 所有 43 个接口已注册到 FastAPI app
- [ ] `curl http://localhost:8000/docs` 显示完整的 Swagger/OpenAPI 文档
- [ ] 每个接口可以用 Swagger UI 的 "Try it out" 测试
- [ ] 接口响应格式与 API 文档一致 (code + data + message)

---

## Step 8: Celery 异步任务

**参照文档**: `plans/02_architecture.md` §4.2

文件: `server/app/tasks/`

| 文件 | 任务函数 | 调用方 |
|------|---------|--------|
| `document_tasks.py` | `generate_document_task(doc_task_id)`, `submit_document_task(doc_id)` | DocumentService |
| `testcase_tasks.py` | `generate_testcases_task(test_task_id)` | TestCaseService |
| `__init__.py` | Celery app 实例配置 | app 启动 |

**要求**:
- Celery broker 使用 Redis (配置从 `settings.REDIS_URL` 读取)
- 任务执行完成后更新数据库中的 task 状态
- 任务失败时记录错误和重试计数
- 支持 `revoke()` 取消正在执行的任务

**验收**:
- [ ] Celery worker 启动成功: `celery -A app.tasks worker --loglevel=info`
- [ ] 发送异步任务后，worker 接收并执行
- [ ] 任务状态从 `pending` → `running` → `completed` 正确流转
- [ ] 模拟任务失败时状态为 `failed`，错误信息被记录

---

## Step 9: 数据库依赖注入与中间件

文件: `server/app/api/deps.py`

```python
from app.core.database import get_db
# FastAPI 依赖注入: Depends(get_db)
```

文件: `server/app/core/middleware.py` (或在 `server/main.py` 中注册)

**要求**:
- CORS 中间件: 允许 `http://localhost:5173` (Vite 默认端口)
- 请求日志中间件: 记录每个 HTTP 请求的方法、路径、状态码、耗时
- 全局异常处理: `500` → `{"code": 500, "message": "服务器内部错误"}`
- 自定义异常类: `AppException(code=40401, message="病历不存在")`

**验收**:
- [ ] 前端 localhost:5173 可跨域调用 API
- [ ] 日志文件/控制台有完整的请求记录
- [ ] 访问不存在的接口返回 404 JSON 格式

---

## Step 10: Demo 数据初始化

**参照文档**: `plans/03_api_interfaces.md` §8.3

文件: `server/app/services/system_service.py` → `init_demo_data()`

**要求**:
- 自动导入课程示例 DRG 规则文件 (从 `server/data/rules/` 读取)
- 自动创建 3-5 个样例病历 (包括课程示例 `A01.002+G01*` 和其他场景)
- 自动激活规则版本
- 幂等性: 重复调用不会创建重复数据

**验收**:
- [ ] `POST /api/v1/system/demo/init` 返回成功
- [ ] `GET /api/v1/rules/versions` 返回至少 1 个规则版本
- [ ] `GET /api/v1/cases` 返回至少 3 个样例病历
- [ ] 对课程示例病历执行入组，返回 `BB11`

---

## Step 11: 后端集成测试

**参照文档**: `plans/04_execution_plan.md` §5 (检查点)

### 11.1 测试结构

```
server/tests/
├── conftest.py                    # pytest fixtures (test DB, client, demo data)
├── test_engine/                   # 规则引擎单元测试
│   ├── test_code_validator.py
│   ├── test_rule_parser.py
│   ├── test_mdc_matcher.py
│   ├── test_adrg_matcher.py
│   ├── test_cc_mcc.py
│   └── test_grouping_engine.py
├── test_services/                 # 服务层测试
│   ├── test_case_service.py
│   ├── test_rule_service.py
│   ├── test_grouping_service.py
│   └── test_document_service.py
├── test_api/                      # API 路由测试 (httpx AsyncClient)
│   ├── test_cases_api.py
│   ├── test_rules_api.py
│   ├── test_grouping_api.py
│   ├── test_documents_api.py
│   ├── test_testcases_api.py
│   ├── test_tasks_api.py
│   └── test_system_api.py
└── test_integration/              # 集成测试 (端到端工作流)
    ├── test_grouping_workflow.py
    └── test_demo_scenarios.py
```

### 11.2 核心测试场景

**示例回归测试** (最高优先级，来自 `example/drg_example.json`):

| # | 测试来源 | 主诊断 | 次要诊断 | 主要手术 | 预期 MDC | 预期 ADRG | 预期 DRG | 并发症 |
|---|---------|--------|---------|---------|----------|----------|----------|--------|
| 1 | 课程示例 | A01.002+G01* | J96.0 | 38.1000x002 | MDCB | BB1 | BB11 | MCC |
| 2 | example Case 1 | C16.301 | K66.002, Z98.800x108, I63.801, K76.807 | 43.7x03 | MDCG | GB2 | GB29 | CC |
| 3 | example Case 2 | J86.000x013 | K66.002, C22.100, Z98.800x115 | 34.8200x002 | MDCE | EC2 | EC29 | CC |
| 4 | example Case 3 | K83.105 | K83.109, K83.807, K66.007, Z43.402 | 51.6303 | MDCH | HC1 | HC15 | NONE |

**异常场景**:
- 主诊断缺失 → `is_grouped=False`
- 编码格式错误 → `validation_errors` 非空
- 无法匹配 MDC → `stage="mdc_matching"`
- 规则版本未激活 → 409 错误
- 无编码场景 (nocode): 仅有诊断名称无编码 → validation_warnings 记录，不阻止流程

**边界场景**:
- MCC 被排除表排除 → `complication="NONE"`
- 无次要诊断 → `complication="NONE"`
- 多个次要诊断命中 MCC → 取最高级别
- 无手术编码 → 匹配内科 ADRG
- 重复手术记录自动去重 (如 example Case 1 中 34.9103 重复两次)

**要求**:
- 使用 pytest-asyncio 运行异步测试
- 每个 API 端点至少 2 个测试 (成功 + 失败)
- 使用 httpx.AsyncClient 模拟 HTTP 请求
- 测试数据库使用独立的 PostgreSQL 数据库或 test fixture
- `example/drg_example.json` 和 `example/drg_example_nocode.json` 均需作为测试 fixture 加载

**验收**:
- [ ] `uv run pytest server/tests/ -v --cov=server/app --cov-report=term-missing` 全部通过
- [ ] 4 个示例回归测试用例全部通过 (A01.002+ C16.301 + J86.000x013 + K83.105)
- [ ] 总测试用例数量 ≥ 50
- [ ] 规则引擎模块覆盖率 ≥ 80%
- [ ] API 路由覆盖率 ≥ 70%
- [ ] 课程示例回归测试通过

---

## Phase 1 最终验收清单

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 1 | 数据库所有表已创建 | `docker exec drg-agent-postgres psql -U drgagent -d drg_agent -c "\dt"` |
| 2 | Alembic 迁移可用 | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` |
| 3 | 规则引擎课程示例通过 | `curl -X POST /api/v1/grouping/execute` 返回 BB11 |
| 4 | FastAPI 健康检查通过 | `curl /api/v1/system/health` 返回 healthy |
| 5 | Swagger 文档可访问 | 浏览器打开 `http://localhost:8000/docs` |
| 6 | 所有 API 接口实现 | 43 个接口在 Swagger 中可见 |
| 7 | Celery worker 可启动 | `celery -A app.tasks worker --loglevel=info` |
| 8 | 后端测试全部通过 | `pytest server/tests/ -v` 零失败 |
| 9 | 演示数据可初始化 | `POST /api/v1/system/demo/init` |
| 10 | 无 linter 错误 | `ruff check server/` 零错误 |

---

## 后续改进建议

1. **异步数据库查询优化**: 所有数据库操作已使用 `async/await`，后续可添加连接池调优
2. **缓存规则索引**: 可在 Redis 中缓存 `build_rule_index()` 的输出，避免每次启动重建
3. **Prompt A/B 测试**: 为关键 prompt (如病历解析、解释生成) 建立多套模板，通过测试对比效果
4. **API 限流**: 添加 FastAPI rate limiter 中间件，防止 LLM API 过度调用
5. **结构化日志采集**: 将 Loguru 日志整合到 ELK 或类似的日志系统
6. **规则热加载**: 支持在运行时加载新规则版本而不重启服务
7. **Token 预算管理**: 跟踪每次 LLM 调用的 token 消耗，设置日预算告警
