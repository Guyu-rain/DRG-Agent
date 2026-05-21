# 数据模型设计

## 1. 实体关系总览

```
┌──────────┐       ┌───────────┐       ┌──────────────┐
│PatientCase│──1:N──│GroupingTask│──1:1──│GroupingResult│
└──────────┘       └───────────┘       └──────────────┘
      │                  │
      │N:1              │N:1
      ▼                  ▼
┌──────────┐       ┌───────────┐       ┌──────────────┐
│RuleVersion│──1:N──│  DRGRule  │       │  TaskStep    │
└──────────┘       └───────────┘       └──────────────┘
                         │
                         │1:N
                         ▼
                  ┌───────────┐  ┌───────────────┐
                  │ CCMCCEntry│  │ ExclusionTable │
                  └───────────┘  └───────────────┘

┌────────────┐     ┌─────────────┐
│DocumentTask│──1:1│Document     │
└────────────┘     └─────────────┘

┌────────────┐     ┌─────────────┐
│ TestTask   │──1:N│ TestCase    │
└────────────┘     └─────────────┘
```

---

## 2. 核心数据模型定义

### 2.1 病历 (PatientCase)

```
PatientCase
├── id: str (PK, "CASE-{date}-{seq}")
├── raw_text: str?                    # 原始病历文本
├── source_type: enum                 # "text" | "structured"
├── status: enum                      # "created" | "parsing" | "parsed" | "validated" | "error"
│
├── patient_id: str?                  # 患者标识
├── age: int?
├── gender: str?                      # "男" | "女" | "未知"
│
├── primary_diagnosis_code: str?      # 主诊断 ICD 编码
├── primary_diagnosis_name: str?      # 主诊断名称
│
├── secondary_diagnoses: JSON?        # [{code, name, source_text}] - 次要诊断列表
├── primary_procedure_code: str?      # 主要手术编码
├── primary_procedure_name: str?      # 主要手术名称
├── other_procedures: JSON?           # [{code, name}] - 其他操作列表
│
├── discharge_type: str?              # 出院方式
│
├── parse_result: JSON?               # 解析智能体原始输出
├── parse_warnings: JSON?             # 解析警告列表
│
├── validation_result: JSON?          # 编码校验结果
├── validation_errors: JSON?          # 校验错误列表
│
├── created_at: datetime
├── updated_at: datetime
│
├── grouping_tasks: List[GroupingTask]  # 关联的入组任务
└── metadata_json: JSON?              # 扩展元数据
```

**Python/Pydantic 定义:**
```python
from enum import Enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, JSON, DateTime, Enum as SAEnum, Text
from sqlalchemy.orm import relationship

class CaseStatus(str, Enum):
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    VALIDATED = "validated"
    ERROR = "error"

class SourceType(str, Enum):
    TEXT = "text"
    STRUCTURED = "structured"

class Diagnosis(BaseModel):
    code: str
    name: Optional[str] = None
    source_text: Optional[str] = None
    type: str  # "primary" | "secondary"

class Procedure(BaseModel):
    code: str
    name: Optional[str] = None
    level: Optional[int] = None   # 手术级别 (如 DRG 规则中的 1-4 级)
    is_primary: bool = False
    priority: int = 0
```

### 2.2 诊断编码 (Diagnosis) - 嵌入式对象

```
Diagnosis (JSON 字段，存储在 PatientCase.secondary_diagnoses 中)
├── code: str              # ICD 编码，如 "J96.0"
├── name: str?             # 诊断名称，如 "急性呼吸衰竭"
├── source_text: str?      # 来源文本
└── type: str              # "primary" | "secondary"
```

### 2.3 手术操作 (Procedure) - 嵌入式对象

```
Procedure (JSON 字段)
├── code: str              # ICD-CM-3 编码，如 "38.1000x002"
├── name: str?             # 手术名称，如 "动脉内膜剥脱术"
├── level: int?            # 手术级别 (1-4)，如 3 级手术
├── is_primary: bool       # 是否为主要手术
└── priority: int          # 优先级（用于规则排序）
```

> **注意**: 输入数据可能使用中文字段名 (`手术名称`, `手术编码`, `手术级别`) 而非英文 (`name`, `code`, `level`)。系统需在 `CaseService` 中提供字段映射层，将中文键名转换为内部英文键名。参见下文 §2.14。

---

### 2.4 规则版本 (RuleVersion)

```
RuleVersion
├── id: str (PK, "RV-{date}-{seq}")
├── version_name: str              # "DRG 2.0 演示规则"
├── description: str?              # 版本说明
├── source_filename: str           # 原始文件名
├── source_file_hash: str          # 文件哈希（去重）
├── status: enum                   # "imported" | "parsing" | "active" | "archived" | "error"
│
├── parse_errors: JSON?            # 解析错误列表
│
├── mdc_list: JSON                 # [{code, name, icd_prefixes, ...}]
├── adrg_list: JSON                # [{code, name, mdc, conditions, ...}]
├── drg_list: JSON                 # [{code, name, adrg, cc_level, ...}]
├── mcc_list: JSON                 # [{code, name, level, exclusion_diags}]
├── cc_list: JSON                  # [{code, name, level, exclusion_diags}]
├── exclusion_table: JSON          # [{diag_code, excluded_by}]
│
├── rule_counts: JSON?             # {mdc: 26, adrg: 376, drg: 628, mcc: 2457, cc: 4553}
│
├── imported_at: datetime
├── activated_at: datetime?
└── archived_at: datetime?
```

### 2.5 入组任务 (GroupingTask)

```
GroupingTask
├── id: str (PK, "TASK-GROUP-{date}-{seq}")
├── case_id: str (FK → PatientCase.id)
├── rule_version_id: str (FK → RuleVersion.id)
├── status: enum                    # "pending" | "executing" | "completed" | "failed" | "needs_review"
├── priority: int (default: 0)
│
├── input_snapshot: JSON            # 执行时的病历快照
├── started_at: datetime?
├── finished_at: datetime?
├── duration_ms: int?
│
├── error_type: str?                # 异常类型
├── error_message: str?             # 异常描述
│
├── created_at: datetime
├── created_by: str?                # 创建人
│
├── result: GroupingResult?         # 1:1 关系
├── steps: List[TaskStep]           # 执行步骤
└── case: PatientCase               # 反向引用
```

**状态机:**
```
pending → executing → completed
                    → failed
                    → needs_review → completed
```

### 2.6 入组结果 (GroupingResult)

```
GroupingResult
├── id: str (PK)
├── task_id: str (FK → GroupingTask.id, unique)
├── mdc_code: str?                  # 如 "MDCB"
├── mdc_name: str?                  # 如 "神经系统疾病及功能障碍"
├── adrg_code: str?                 # 如 "BB1"
├── adrg_name: str?                 # 如 "神经系统复合手术"
├── drg_code: str?                  # 如 "BB11"
├── drg_name: str?                  # 如 "神经系统复合手术，伴严重合并症或并发症"
│
├── is_grouped: bool                # 是否成功入组
├── ungrouped_reason: str?          # 未入组原因
│
├── complication: str?              # 并发症等级 "MCC" | "CC" | "NONE" (与 evidence_chain 互补)
├── evidence_chain: JSON            # 证据链 [{step, type, description, matchedCode, matchedRule}]
├── explanation: str?               # 自然语言解释
│
├── candidate_rules: JSON?          # 候选规则列表
├── warnings: JSON?                 # 警告列表
│
├── confirmed_at: datetime?         # 人工确认时间
├── confirmed_by: str?              # 确认人
│
├── created_at: datetime
└── task: GroupingTask              # 反向引用
```

### 2.7 任务步骤 (TaskStep)

```
TaskStep
├── id: str (PK)
├── task_id: str (FK → GroupingTask.id)
├── step_name: str                  # 步骤名: "case_parse" | "code_validate" | "rule_retrieve" | "drg_grouping" | "explain_generate"
├── step_order: int                 # 执行顺序
├── status: enum                    # "pending" | "running" | "completed" | "failed" | "skipped"
├── started_at: datetime?
├── finished_at: datetime?
├── duration_ms: int?
├── input_summary: str?             # 输入摘要
├── output_summary: str?            # 输出摘要
├── error_message: str?             # 错误信息
└── task: GroupingTask              # 反向引用
```

---

### 2.8 文档 (Document)

```
Document
├── id: str (PK, "DOC-{date}-{seq}")
├── doc_type: enum                  # "requirements" | "design" | "testing" | "management" | "configuration"
├── title: str                      # 文档标题
├── content: str                    # 文档内容（Markdown）
├── original_content: str?          # 智能体生成的原始内容（编辑前）
│
├── version: str (default: "V1.0")
├── status: enum                    # "draft" | "review" | "submitted" | "archived"
│
├── author: str?                    # 作者
├── generated_by: str?              # 生成智能体名称
│
├── metadata_json: JSON?            # {model_used, token_count, generated_at, ...}
├── source_task_id: str?            # 来源任务 ID
│
├── file_path: str?                 # 文件存储路径
├── file_format: str?               # "pdf" | "markdown" | "html"
├── file_size: int?                 # 文件大小（字节）
├── checksum: str?                  # 文件校验和
│
├── created_at: datetime
├── updated_at: datetime
├── submitted_at: datetime?
│
├── versions: List[DocumentVersion] # 版本历史
└── sections: JSON?                 # [{id, title, status}] 章节列表
```

### 2.9 文档版本 (DocumentVersion)

```
DocumentVersion
├── id: str (PK)
├── document_id: str (FK → Document.id)
├── version: str                    # "V1.0", "V1.1", ...
├── content_snapshot: str           # 版本内容快照
├── change_description: str?        # 变更说明
├── created_at: datetime
└── created_by: str?
```

---

### 2.10 文档生成任务 (DocumentTask)

```
DocumentTask
├── id: str (PK, "DOC-TASK-{date}-{seq}")
├── doc_type: enum
├── title: str
├── context: JSON                   # 生成上下文配置
├── template: str?                  # 模板名称
├── status: enum                    # "pending" | "running" | "completed" | "failed"
├── result_doc_id: str? (FK → Document.id)
├── started_at: datetime?
├── finished_at: datetime?
├── error_message: str?
├── created_at: datetime
```

---

### 2.11 测试用例 (TestCase)

```
TestCase
├── id: str (PK, "TC-{module}-{seq}")
├── title: str
├── scenario_type: enum             # "normal" | "boundary" | "abnormal"
├── priority: enum                  # "high" | "medium" | "low"
│
├── requirement_ref: str?           # 关联需求编号，如 "FR-D-05"
├── rule_version_id: str? (FK → RuleVersion.id)
│
├── input_case: JSON                # 输入病历 { primaryDiagnosis, secondaryDiagnoses, primaryProcedure, ... }
├── expected_result: JSON           # 预期结果 { mdc, adrg, drg }
├── expected_explanation: str?      # 预期解释
│
├── actual_result: JSON?            # 实际执行结果
├── is_passed: bool?                # null=未执行, true=通过, false=失败
├── executed_at: datetime?
│
├── created_at: datetime
└── created_by: str?
```

### 2.12 测试生成任务 (TestTask)

```
TestTask
├── id: str (PK, "TEST-TASK-{date}-{seq}")
├── rule_version_id: str (FK)
├── scenario_types: JSON            # ["normal", "boundary", "abnormal"]
├── scope: JSON                     # {mdc_list, adrg_list, include_all_rules}
├── max_count: int?
├── status: enum                    # "pending" | "running" | "completed" | "failed"
├── generated_count: int?
├── started_at: datetime?
├── finished_at: datetime?
├── error_message: str?
├── created_at: datetime
```

---

### 2.13 执行日志 (ExecutionLog)

```
ExecutionLog
├── id: str (PK, "LOG-{date}-{seq}")
├── timestamp: datetime
├── level: enum                     # "debug" | "info" | "warning" | "error"
├── agent: str                      # 智能体名称
├── task_id: str?                   # 关联任务
├── message: str                    # 日志消息
├── input_summary: str?             # 输入摘要
├── output_summary: str?            # 输出摘要
├── error_detail: str?              # 错误详情
├── metadata_json: JSON?            # 扩展信息（token 消耗等）
```

---

### 2.14 系统配置 (SystemConfig)

```
SystemConfig
├── id: int (PK, default=1)
├── llm_config: JSON                # {api_base, model, max_retries, timeout}
├── storage_config: JSON            # {document_path, rule_data_path}
├── active_rule_version_id: str?
├── demo_initialized: bool
├── updated_at: datetime
```

---

## 3. 数据库索引建议

```sql
-- PatientCase
CREATE INDEX idx_case_status ON patient_cases(status);
CREATE INDEX idx_case_created ON patient_cases(created_at DESC);

-- RuleVersion
CREATE INDEX idx_rule_status ON rule_versions(status);
CREATE UNIQUE INDEX idx_rule_active ON rule_versions(status) WHERE status = 'active';

-- GroupingTask
CREATE INDEX idx_task_case ON grouping_tasks(case_id);
CREATE INDEX idx_task_status ON grouping_tasks(status);
CREATE INDEX idx_task_created ON grouping_tasks(created_at DESC);

-- GroupingResult
CREATE INDEX idx_result_drg ON grouping_results(drg_code);

-- Document
CREATE INDEX idx_doc_type ON documents(doc_type);
CREATE INDEX idx_doc_status ON documents(status);
CREATE INDEX idx_doc_created ON documents(created_at DESC);

-- TestCase
CREATE INDEX idx_test_type ON test_cases(scenario_type);
CREATE INDEX idx_test_req ON test_cases(requirement_ref);

-- ExecutionLog
CREATE INDEX idx_log_task ON execution_logs(task_id);
CREATE INDEX idx_log_time ON execution_logs(timestamp DESC);
CREATE INDEX idx_log_level ON execution_logs(level);
```

---

## 4. SQLAlchemy 模型 Python 定义示例

```python
# server/app/models/case.py
from sqlalchemy import Column, String, Integer, JSON, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base

def generate_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

class PatientCase(Base):
    __tablename__ = "patient_cases"

    id = Column(String, primary_key=True, default=lambda: generate_id("CASE"))
    raw_text = Column(Text, nullable=True)
    source_type = Column(String(20), nullable=False, default="text")
    status = Column(String(20), nullable=False, default="created")

    patient_id = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)

    primary_diagnosis_code = Column(String(50), nullable=True)
    primary_diagnosis_name = Column(String(200), nullable=True)

    secondary_diagnoses = Column(JSON, nullable=True)
    primary_procedure_code = Column(String(50), nullable=True)
    primary_procedure_name = Column(String(200), nullable=True)
    other_procedures = Column(JSON, nullable=True)

    discharge_type = Column(String(50), nullable=True)

    parse_result = Column(JSON, nullable=True)
    parse_warnings = Column(JSON, nullable=True)

    validation_result = Column(JSON, nullable=True)
    validation_errors = Column(JSON, nullable=True)

    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    grouping_tasks = relationship("GroupingTask", back_populates="case")
```

---

## 5. 输入字段映射层 (Chinese → English)

DRG 样例数据 (`example/drg_example.json`) 使用中文字段名，系统在 `CaseService.create_case()` 入口处自动将其映射为内部英文键名：

| 中文键名 | 英文键名 | 说明 |
|----------|----------|------|
| `性别` | `gender` | "男"/"女"/"未知" |
| `年龄` | `age` | 数值 |
| `主要诊断.疾病名称` | `primaryDiagnosis.name` | |
| `主要诊断.疾病编码` | `primaryDiagnosis.code` | |
| `次要诊断列表[].疾病名称` | `secondaryDiagnoses[].name` | |
| `次要诊断列表[].疾病编码` | `secondaryDiagnoses[].code` | |
| `主要手术.手术名称` | `primaryProcedure.name` | |
| `主要手术.手术编码` | `primaryProcedure.code` | |
| `主要手术.手术级别` | `primaryProcedure.level` | 1-4 级 |
| `其他手术列表[].手术名称` | `otherProcedures[].name` | |
| `其他手术列表[].手术编码` | `otherProcedures[].code` | |
| `其他手术列表[].手术级别` | `otherProcedures[].level` | 1-4 级 |

**重复数据处理**: `CaseService` 在导入时自动去除完全相同的重复诊断和重复手术记录（基于 code 字段去重）。

**映射实现**: `server/app/services/case_service.py` 中的 `_normalize_case_input()` 静态方法负责此转换。`example/drg_example.json` 和 `example/drg_example_nocode.json` 中的 3 个测试用例均可通过此映射层正常导入。

### 无编码场景 (nocode)

`drg_example_nocode.json` 中的病历仅有疾病/手术名称而无编码。处理策略：
1. 字段映射层保留名称，将 `code` 设为 `None`
2. 病历解析智能体尝试通过 LLM 根据名称推断 ICD/ICD-CM-3 编码
3. 推断失败则标记 `validation_warnings`，提示用户手动补充编码
4. 入组前校验会提示 "编码缺失" 但不阻止(允许仅名称的无码入组体验)
