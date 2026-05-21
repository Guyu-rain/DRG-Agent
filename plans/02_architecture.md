# 系统架构设计

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (React + TypeScript)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │DRG 入组  │ │规则管理  │ │文档系统  │ │测试用例  │ │ 系统配置  │ │
│  │ 工作台   │ │          │ │          │ │          │ │           │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ │
│       └─────────────┴────────────┴────────────┴─────────────┘       │
│                              │ HTTP/REST                              │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────┐
│                      后端 (FastAPI + Python)                          │
│  ┌──────────────────────────┼─────────────────────────────────────┐ │
│  │                   API 路由层 (v1/)                              │ │
│  │  /cases  │ /rules │ /grouping │ /docs │ /testcases │ /system   │ │
│  └──────────┴────────┴───────────┴───────┴────────────┴──────────┘ │
│                               │                                       │
│  ┌────────────────────────────┼───────────────────────────────────┐ │
│  │                    服务层 (Services)                             │ │
│  │  CaseService│RuleService│GroupingService│DocService│TestService │ │
│  └─────────────┴───────────┴───────────────┴──────────┴───────────┘ │
│                               │                                       │
│  ┌────────────────────────────┼───────────────────────────────────┐ │
│  │                 智能体编排层 (Agent Orchestration)               │ │
│  │   ┌─────────────────────────────────────────────────────────┐  │ │
│  │   │               AgentOrchestrator                          │  │ │
│  │   │  StateGraph → Nodes → Edges → Conditional Edges         │  │ │
│  │   │                                                          │  │ │
│  │   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │ │
│  │   │  │病历解析  │ │规则检索  │ │DRG 入组  │ │解释生成    │  │  │ │
│  │   │  │Agent     │ │Agent     │ │Agent     │ │Agent       │  │  │ │
│  │   │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │  │ │
│  │   │  ┌──────────┐ ┌──────────┐ ┌────────────┐               │  │ │
│  │   │  │文档生成  │ │测试生成  │ │文档提交    │               │  │ │
│  │   │  │Agent     │ │Agent     │ │Agent       │               │  │ │
│  │   │  └──────────┘ └──────────┘ └────────────┘               │  │ │
│  │   └─────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                       │
│  ┌────────────────────────────┼───────────────────────────────────┐ │
│  │                    领域服务层 (Domain/Engine)                    │ │
│  │  ┌──────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │ │
│  │  │RuleParser        │ │GroupingEngine   │ │CodeValidator    │  │ │
│  │  │(规则解析)        │ │(MDC→ADRG→DRG)   │ │(编码校验)      │  │ │
│  │  └──────────────────┘ └─────────────────┘ └─────────────────┘  │ │
│  │  ┌──────────────────┐ ┌─────────────────┐                      │ │
│  │  │CCMCCService      │ │VersionTracker   │                      │ │
│  │  │(MCC/CC判定)      │ │(版本追踪)       │                      │ │
│  │  └──────────────────┘ └─────────────────┘                      │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                       │
│  ┌────────────────────────────┼───────────────────────────────────┐ │
│  │                     基础设施层 (Infrastructure)                  │ │
│  │  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │ │
│  │  │Database│ │Document  │ │LLM       │ │Celery    │ │Logging│ │ │
│  │  │(PostgreSQL)│Storage   │ │Client    │ │Tasks     │ │       │ │ │
│  │  └────────┘ └──────────┘ └──────────┘ └──────────┘ └───────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 分层架构设计

### 2.1 表现层 (Presentation Layer)

**职责**: 用户交互、数据展示、表单输入、结果可视化

**前端路由结构:**

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | TaskCenter | 任务中心仪表盘 |
| `/drg` | DRGGrouping | DRG 入组工作台（核心页面） |
| `/rules` | RuleManagement | 规则版本管理 |
| `/docs` | DocumentSystem | 虚拟文档系统 |
| `/docs/:type` | DocumentList | 按类型浏览文档 |
| `/docs/:id` | DocumentDetail | 文档详情与预览 |
| `/tests` | TestCaseManager | 测试用例管理 |
| `/logs` | ExecutionLog | 智能体执行日志 |
| `/settings` | SystemSettings | 系统配置 |

**核心页面组件关系:**

```
DRGGrouping Page
├── RuleVersionSelector (规则版本选择器)
├── PatientCaseInput (病历输入面板 - 文本/结构化两种模式)
│   ├── TextModeInput (自由文本输入)
│   └── StructuredFormInput (结构化表单)
├── GroupingExecuteButton (执行入组按钮)
├── GroupingResultPanel (入组结果面板)
│   ├── ResultSummary (DRG 组号/组名/MDC/ADRG)
│   ├── EvidenceChain (证据链可视化)
│   └── CandidateRules (候选规则列表)
└── ActionButtons (提交复核 / 生成文档 / 生成测试用例)
```

### 2.2 应用层 (Application Layer)

**职责**: 编排服务调用、事务管理、权限校验

**核心服务:**

```python
# server/app/services/

CaseService
├── create_case(case_input) → case_id
├── validate_case(case_id) → validation_result
├── parse_case(case_id) → structured_case
└── get_cases(filter) → list[case_summary]

RuleService
├── import_rules(file, metadata) → rule_version
├── list_versions() → list[version_summary]
├── get_version(version_id) → rule_version_detail
├── activate_version(version_id)
└── parse_rule_file(file) → parsed_rules

GroupingService
├── execute_grouping(case_id, rule_version_id) → task_id
├── get_grouping_result(task_id) → grouping_result
├── batch_grouping(case_ids, rule_version_id) → batch_task_id
└── create_review(task_id, comment) → review_task

DocumentService
├── generate_document(doc_type, context) → doc_task_id
├── preview_document(doc_id) → document_content
├── edit_document(doc_id, content)
├── submit_document(doc_id) → submission_record
├── list_documents(filter) → list[doc_summary]
├── get_document(doc_id) → document_detail
└── export_document(doc_id, format) → file

TestCaseService
├── generate_testcases(config) → test_task_id
├── list_testcases(filter) → list[testcase_summary]
├── export_testcases(testcase_ids) → file
└── submit_to_document_system(testcase_ids) → doc_task_id
```

### 2.3 智能体编排层（核心）

**AgentOrchestrator** 是系统的调度核心，管理所有智能体的生命周期和工作流编排。

```
AgentOrchestrator
├── 入组工作流 (GroupingWorkflow)
│   ├── 节点: case_parse → rule_retrieve → drg_group → explain
│   └── 条件分支: 编码有效? / 命中MDC? / 有MCC?
│
├── 文档生成工作流 (DocumentGenWorkflow)
│   ├── 节点: context_collect → document_generate → preview → edit → submit
│   └── 异步执行，不阻塞主流程
│
└── 测试用例生成工作流 (TestGenWorkflow)
    ├── 节点: rule_analyze → scenario_construct → testcase_generate → submit
    └── 异步执行
```

### 2.4 领域服务层

**职责**: 纯业务逻辑，不依赖 LLM，可独立测试

- **RuleParser**: 解析 DRG 规则文件（Excel/CSV），输出结构化规则对象
- **GroupingEngine**: 三重匹配引擎（MDC→ADRG→DRG），确定性算法
- **CodeValidator**: ICD/ICD-CM-3 编码格式校验
- **CCMCCService**: MCC/CC 列表匹配 + 排除表检查
- **VersionTracker**: 规则版本管理，支持多版本共存

### 2.5 基础设施层

**职责**: 提供底层技术支持

- **数据库**: SQLAlchemy ORM → SQLite/PostgreSQL
- **文件存储**: 本地文件系统 + JSON 索引元数据
- **LLM Client**: OpenAI SDK 封装，统一的重试/超时/降级策略
- **Celery Tasks**: 异步任务队列
- **Logging**: Loguru 统一日志

---

## 3. DRG 规则引擎架构（核心确定性逻辑）

```
┌─────────────────────────────────────────────────────────┐
│                    DRG 规则引擎                           │
│                                                          │
│  ┌────────────────┐         ┌────────────────┐          │
│  │  RuleParser    │────────▶│  Structured    │          │
│  │  (文件解析)    │         │  Rule Database │          │
│  └────────────────┘         └───────┬────────┘          │
│                                     │                    │
│  ┌────────────────┐                  │                    │
│  │  PatientCase   │                  │                    │
│  │  (结构化病历)  │                  │                    │
│  └───────┬────────┘                  │                    │
│          │                           │                    │
│          ▼                           ▼                    │
│  ┌─────────────────────────────────────────┐            │
│  │           GroupingEngine                 │            │
│  │                                          │            │
│  │  Step 1: Code Validation                 │            │
│  │  Step 2: MDC Matching (主诊断→MDC)       │            │
│  │  Step 3: ADRG Matching (MDC+手术→ADRG)   │            │
│  │  Step 4: CCMCC Evaluation (次要诊断→CC)  │            │
│  │  Step 5: DRG Finalization (ADRG+CC→DRG)  │            │
│  │  Step 6: Evidence Building               │            │
│  └──────────────┬──────────────────────────┘            │
│                 │                                        │
│                 ▼                                        │
│  ┌─────────────────────────────────────────┐            │
│  │          GroupingResult                  │            │
│  │  {                                       │            │
│  │    mdc: "MDCB",                          │            │
│  │    adrg: "BB1",                          │            │
│  │    drg: "BB11",                          │            │
│  │    evidence: [...],                      │            │
│  │    warnings: [...]                       │            │
│  │  }                                       │            │
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

**关键设计原则**:
- 规则引擎内部逻辑全部使用 Python 字典/集合查找，O(1) 复杂度
- 规则数据在导入时预处理为索引结构 (如 `{icd_code → mdc}` 映射表)
- 不使用 LLM 参与规则匹配，保证结果可复现
- LLM 仅在"解释生成"环节介入，将证据链转换为自然语言

---

## 4. 数据流设计

### 4.1 DRG 入组主流程

```
用户输入病历 
  → CaseService.create_case() 
  → CaseService.parse_case() (调用病历解析智能体)
  → CaseService.validate_case() (调用编码校验器)
  → [病历已保存]
  → 用户点击"开始入组"
  → GroupingService.execute_grouping(case_id, rule_version_id)
  → AgentOrchestrator.run_grouping_workflow()
    → 节点1: 病历解析智能体 (结构化提取)
    → 节点2: 规则检索智能体 (加载规则索引)
    → 节点3: DRG 入组智能体 (调用 GroupingEngine)
      → 分支: 编码有效? → 是 → MDC匹配 → 命中MDC? → 是 → ADRG匹配 → CC判定 → DRG确定
      → 分支: 编码有效? → 否 → 异常处理 → 标记未入组
    → 节点4: 解释生成智能体 (证据链转自然语言)
  → 保存 GroupingTask + GroupingResult
  → 返回结果给前端
```

### 4.2 文档生成流程（异步）

```
用户选择文档类型 + 上下文
  → DocumentService.generate_document(doc_type, context)
  → 创建 DocumentTask (状态: pending)
  → Celery 异步执行:
    → AgentOrchestrator.run_document_gen_workflow()
      → 节点1: 上下文收集 (读取需求/代码/规则)
      → 节点2: 文档生成智能体 (LLM + 模板)
      → 节点3: 文档格式化和存储
    → 更新 DocumentTask (状态: completed)
  → 前端轮询状态 / SSE 通知
  → 用户预览 → 编辑 → 提交
```

### 4.3 测试用例生成流程（异步）

```
用户选择规则范围 + 场景类型
  → TestCaseService.generate_testcases(config)
  → 创建 TestTask (状态: pending)
  → Celery 异步执行:
    → AgentOrchestrator.run_test_gen_workflow()
      → 节点1: 规则分析 (提取规则条件组合)
      → 节点2: 场景构建 (正常/边界/异常)
      → 节点3: 测试用例生成智能体 (LLM)
      → 节点4: 存入测试用例库
    → 更新 TestTask (状态: completed)
```

---

## 5. 前端状态管理架构

```
Store 模块划分 (Zustand):

groupingStore
├── currentCase: PatientCase | null
├── currentResult: GroupingResult | null
├── isExecuting: boolean
├── history: GroupingTask[]
├── actions: submitCase, executeGrouping, clearResult

documentStore
├── documents: DocumentSummary[]
├── currentDocument: DocumentDetail | null
├── filter: DocFilter
├── actions: fetchDocuments, filterDocuments, viewDocument

testcaseStore
├── testcases: TestCase[]
├── isGenerating: boolean
├── filter: TestCaseFilter
├── actions: generateTestCases, fetchTestCases, exportTestCases

taskStore
├── tasks: TaskSummary[]
├── actions: fetchTasks, pollTaskStatus

settingsStore
├── apiConfig: ApiConfig
├── llmConfig: LLMConfig
├── actions: updateConfig, resetConfig
```

---

## 6. 部署架构

```
课程演示环境 (单机部署):

┌────────────────────────────────────────────┐
│  开发机 / 笔记本                            │
│                                             │
│  Terminal 1:                                │
│    cd server && uvicorn main:app --reload   │
│    (FastAPI 开发服务器 :8000)               │
│                                             │
│  Terminal 2:                                │
│    celery -A app.tasks worker --loglevel=info│
│    (Celery Worker 队列处理)                 │
│                                             │
│  Terminal 3:                                │
│    cd web && pnpm dev                       │
│    (Vite 开发服务器 :5173)                  │
│                                             │
│  Browser: http://localhost:5173             │
└────────────────────────────────────────────┘

可选生产部署:
  - 后端: Gunicorn + Uvicorn workers
  - 前端: Nginx 静态文件服务
  - 数据库: 外部 PostgreSQL
  - 任务队列: Redis + Celery
```

---

## 7. 模块间依赖关系

```
web/ (前端)
  └── depends on: server/app/api/ (REST API)

server/app/api/ (API 路由)
  └── depends on: server/app/services/

server/app/services/ (服务层)
  ├── depends on: server/app/models/ (数据模型)
  ├── depends on: server/app/agents/ (智能体编排)
  └── depends on: server/app/engine/ (规则引擎)

server/app/agents/ (智能体)
  ├── depends on: server/app/engine/ (规则引擎)
  └── depends on: server/app/llm/ (LLM 客户端)

server/app/engine/ (规则引擎)
  └── depends on: 无外部依赖 (纯 Python 算法)

server/app/llm/ (LLM 客户端)
  └── depends on: openai SDK

server/app/core/ (核心配置)
  └── depends on: pydantic-settings
```

依赖方向严格遵守从上到下原则：上层依赖下层，下层不依赖上层。
