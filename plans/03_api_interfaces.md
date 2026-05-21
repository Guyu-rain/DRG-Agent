# API 接口定义

## 1. 接口规范

### 1.1 基础URL

```
开发环境: http://localhost:8000/api/v1
```

### 1.2 通用规范

- **协议**: HTTP/1.1, RESTful
- **数据格式**: JSON (Content-Type: application/json)
- **字符编码**: UTF-8
- **命名风格**: camelCase (请求/响应), snake_case (内部)
- **分页**: `?page=1&pageSize=20`，返回 `{ items, total, page, pageSize }`

### 1.3 统一响应格式

```typescript
// 成功
{
  "code": 200,
  "data": { ... },
  "message": "success"
}

// 失败
{
  "code": 400,       // HTTP 状态码
  "data": null,
  "message": "详细错误描述",
  "detail": { ... }  // 可选，错误详情（字段校验等）
}

// 分页
{
  "code": 200,
  "data": {
    "items": [...],
    "total": 150,
    "page": 1,
    "pageSize": 20,
    "totalPages": 8
  },
  "message": "success"
}
```

### 1.4 HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如重复提交） |
| 422 | 请求数据校验失败 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用（LLM API 不可达等） |

---

## 2. 病历管理接口 (PatientCase)

### 2.1 创建病历

```
POST /api/v1/cases
```

**Request Body:**
```json
{
  "rawText": "主诊断：A01.002+G01* 伤寒性脑膜炎\n次要诊断：J96.0 急性呼吸衰竭\n主要手术：38.1000x002 动脉内膜剥脱术",
  "sourceType": "text"  
}
```
或结构化输入：
```json
{
  "structuredData": {
    "patientId": "P001",
    "age": 45,
    "gender": "男",
    "primaryDiagnosis": { "code": "A01.002+G01*", "name": "伤寒性脑膜炎" },
    "secondaryDiagnoses": [
      { "code": "J96.0", "name": "急性呼吸衰竭" }
    ],
    "primaryProcedure": { "code": "38.1000x002", "name": "动脉内膜剥脱术", "surgeryLevel": 3 },
    "otherProcedures": [],
    "dischargeType": "医嘱离院"
  },
  "sourceType": "structured"
}
```

**Response (201):**
```json
{
  "code": 201,
  "data": {
    "caseId": "CASE-20260519-001",
    "status": "created",
    "createdAt": "2026-05-19T10:30:00Z"
  },
  "message": "病历创建成功"
}
```

### 2.2 解析病历（提取结构化字段）

```
POST /api/v1/cases/{caseId}/parse
```

触发病历解析智能体工作流。LLM 从自由文本提取结构化字段。

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "caseId": "CASE-20260519-001",
    "parsedData": {
      "patientId": null,
      "age": null,
      "gender": null,
      "primaryDiagnosis": { "code": "A01.002+G01*", "name": "伤寒性脑膜炎", "sourceText": "主诊断：A01.002+G01* 伤寒性脑膜炎" },
      "secondaryDiagnoses": [
        { "code": "J96.0", "name": "急性呼吸衰竭", "sourceText": "次要诊断：J96.0 急性呼吸衰竭" }
      ],
      "primaryProcedure": { "code": "38.1000x002", "name": "动脉内膜剥脱术", "surgeryLevel": 3, "sourceText": "主要手术：38.1000x002 动脉内膜剥脱术" },
      "otherProcedures": [],
      "dischargeType": null,
      "rawText": "..."
    },
    "warnings": ["未检测到年龄信息", "未检测到出院方式"],
    "parseStatus": "completed"
  },
  "message": "解析完成"
}
```

### 2.3 校验病历编码

```
POST /api/v1/cases/{caseId}/validate
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "caseId": "CASE-20260519-001",
    "isValid": true,
    "validationResults": [
      { "field": "primaryDiagnosis.code", "isValid": true, "code": "A01.002+G01*" },
      { "field": "secondaryDiagnoses[0].code", "isValid": true, "code": "J96.0" },
      { "field": "primaryProcedure.code", "isValid": true, "code": "38.1000x002" }
    ],
    "errors": [],
    "warnings": ["次要诊断 J96.0 未在规则库中验证（规则库未加载）"]
  },
  "message": "校验完成"
}
```

### 2.4 获取病列表

```
GET /api/v1/cases?page=1&pageSize=20&status=parsed&keyword=A01
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "caseId": "CASE-20260519-001",
        "summary": "主诊断：A01.002+G01*",
        "status": "parsed",
        "createdAt": "2026-05-19T10:30:00Z",
        "groupingCount": 1
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20,
    "totalPages": 1
  }
}
```

### 2.5 获取病历详情

```
GET /api/v1/cases/{caseId}
```

### 2.6 删除病历

```
DELETE /api/v1/cases/{caseId}
```

### 2.7 更新病历（人工修正解析结果）

```
PUT /api/v1/cases/{caseId}
```

**Request Body:**
```json
{
  "primaryDiagnosis": { "code": "A01.002+G01*", "name": "伤寒性脑膜炎" },
  "secondaryDiagnoses": [
    { "code": "J96.0", "name": "急性呼吸衰竭" }
  ]
}
```

---

## 3. 规则管理接口 (Rule)

### 3.1 导入规则文件

```
POST /api/v1/rules/import
Content-Type: multipart/form-data
```

**Form Fields:**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | DRG 规则文件（Excel/CSV） |
| versionName | string | 是 | 版本名称，如 "DRG 2.0 演示规则" |
| description | string | 否 | 版本说明 |

**Response (201):**
```json
{
  "code": 201,
  "data": {
    "versionId": "RV-20260519-001",
    "versionName": "DRG 2.0 演示规则",
    "status": "parsing",
    "ruleCount": null,
    "parseErrors": []
  },
  "message": "规则文件已上传，正在解析"
}
```

### 3.2 获取规则版本列表

```
GET /api/v1/rules/versions
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "versionId": "RV-20260519-001",
        "versionName": "DRG 2.0 演示规则",
        "description": "课程演示用规则",
        "status": "active",
        "ruleCount": { "mdc": 26, "adrg": 376, "drg": 628 },
        "importedAt": "2026-05-19T10:00:00Z",
        "isActive": true
      }
    ],
    "total": 1
  }
}
```

### 3.3 获取规则版本详情

```
GET /api/v1/rules/versions/{versionId}
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "versionId": "RV-20260519-001",
    "versionName": "DRG 2.0 演示规则",
    "status": "active",
    "mdcList": [
      { "code": "MDCB", "name": "神经系统疾病及功能障碍", "icdPrefix": ["G00-G99", "A01"] }
    ],
    "adrgList": [
      { "code": "BB1", "name": "神经系统复合手术", "mdc": "MDCB", "conditions": {...} }
    ],
    "drgList": [
      { "code": "BB11", "name": "神经系统复合手术，伴严重合并症或并发症", "adrg": "BB1", "ccLevel": "MCC" }
    ],
    "mccList": [
      { "code": "J96.0", "name": "急性呼吸衰竭", "level": "MCC", "exclusionDiags": [] }
    ],
    "ccList": [
      { "code": "I10", "name": "原发性高血压", "level": "CC", "exclusionDiags": ["I10"] }
    ],
    "exclusionTable": [
      { "diagCode": "J96.0", "excludedBy": [] }
    ],
    "ruleCount": { "mdc": 26, "adrg": 376, "drg": 628, "mcc": 2457, "cc": 4553 }
  }
}
```

### 3.4 激活规则版本

```
POST /api/v1/rules/versions/{versionId}/activate
```

将指定版本设为活跃版本（同一时刻仅允许一个活跃版本）。

### 3.5 删除规则版本

```
DELETE /api/v1/rules/versions/{versionId}
```

### 3.6 查询规则（按编码搜索）

```
GET /api/v1/rules/search?code=A01.002&ruleType=mdc
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "matches": [
      {
        "ruleType": "mdc",
        "code": "MDCB",
        "name": "神经系统疾病及功能障碍",
        "matchedBy": "诊断编码 A01.002 命中前缀 A01"
      }
    ]
  }
}
```

---

## 4. DRG 入组接口 (Grouping)

### 4.1 执行入组

```
POST /api/v1/grouping/execute
```

**Request Body:**
```json
{
  "caseId": "CASE-20260519-001",
  "ruleVersionId": "RV-20260519-001"
}
```

**Response (202):**
```json
{
  "code": 202,
  "data": {
    "taskId": "TASK-GROUP-20260519-001",
    "status": "executing",
    "startedAt": "2026-05-19T10:35:00Z"
  },
  "message": "入组任务已创建，正在执行"
}
```

### 4.2 查询入组结果

```
GET /api/v1/grouping/results/{taskId}
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "taskId": "TASK-GROUP-20260519-001",
    "status": "completed",
    "caseId": "CASE-20260519-001",
    "ruleVersion": "DRG 2.0 演示规则",
    "startedAt": "2026-05-19T10:35:00Z",
    "finishedAt": "2026-05-19T10:35:02Z",
    "durationMs": 1534,
    "result": {
      "mdc": {
        "code": "MDCB",
        "name": "神经系统疾病及功能障碍"
      },
      "adrg": {
        "code": "BB1",
        "name": "神经系统复合手术"
      },
      "drg": {
        "code": "BB11",
        "name": "神经系统复合手术，伴严重合并症或并发症"
      },
      "complication": "MCC",
      "evidence": [
        {
          "step": 1,
          "type": "mdc_match",
          "description": "主诊断 A01.002+G01*（伤寒性脑膜炎）命中 ICD 前缀 A01，进入 MDCB 神经系统疾病及功能障碍",
          "matchedCode": "A01.002+G01*",
          "matchedRule": "MDCB ICD前缀：A01"
        },
        {
          "step": 2,
          "type": "adrg_match",
          "description": "主要手术 38.1000x002（动脉内膜剥脱术）在 MDCB 下命中 BB1 神经系统复合手术",
          "matchedCode": "38.1000x002",
          "matchedRule": "BB1 手术列表：38.1000x002"
        },
        {
          "step": 3,
          "type": "cc_mcc_evaluation",
          "description": "次要诊断 J96.0（急性呼吸衰竭）属于 MCC 列表",
          "matchedCode": "J96.0",
          "ccLevel": "MCC"
        },
        {
          "step": 4,
          "type": "exclusion_check",
          "description": "J96.0 未被主诊断 A01.002+G01* 的排除表排除",
          "excludedBy": [],
          "excluded": false
        },
        {
          "step": 5,
          "type": "drg_final",
          "description": "BB1 支持 MCC 分层，最终进入 BB11",
          "matchedRule": "BB1→BB11：MCC=是"
        }
      ],
      "explanation": "根据主诊断 A01.002+G01*（伤寒性脑膜炎），病例进入 MDCB（神经系统疾病及功能障碍）。主要手术 38.1000x002（动脉内膜剥脱术）命中 BB1（神经系统复合手术）。次要诊断 J96.0（急性呼吸衰竭）属于 MCC（严重合并症或并发症），且未被排除表排除，因此 BB1 支持 MCC 分层，最终进入 BB11（神经系统复合手术，伴严重合并症或并发症）。",
      "candidateRules": [
        {
          "adrg": "BB1",
          "drg": "BB11",
          "name": "伴严重合并症或并发症",
          "reason": "命中（MCC：J96.0）"
        },
        {
          "adrg": "BB1",
          "drg": "BB15",
          "name": "不伴合并症或并发症",
          "reason": "未命中（存在 MCC）"
        }
      ],
      "warnings": []
    },
    "inputSnapshot": {
      "primaryDiagnosis": "A01.002+G01*",
      "secondaryDiagnoses": ["J96.0"],
      "primaryProcedure": "38.1000x002"
    }
  }
}
```

### 4.3 查询未入组原因（异常场景）

当入组失败时：
```json
{
  "code": 200,
  "data": {
    "taskId": "TASK-GROUP-20260519-003",
    "status": "failed",
    "result": null,
    "error": {
      "type": "NO_RULE_MATCH",
      "stage": "mdc_matching",
      "message": "主诊断 Z99.9 无法映射到任何 MDC",
      "suggestions": ["检查诊断编码是否正确", "尝试使用结构化输入"],
      "candidateMatches": []
    }
  }
}
```

### 4.4 查询入组任务列表

```
GET /api/v1/grouping/tasks?page=1&pageSize=20&status=completed&caseId=CASE-20260519-001
```

### 4.5 批量入组

```
POST /api/v1/grouping/batch
```

**Request Body:**
```json
{
  "caseIds": ["CASE-001", "CASE-002", "CASE-003"],
  "ruleVersionId": "RV-20260519-001"
}
```

**Response (202):**
```json
{
  "code": 202,
  "data": {
    "batchTaskId": "BATCH-20260519-001",
    "totalCases": 3,
    "status": "executing"
  }
}
```

---

## 5. 文档系统接口 (Document)

### 5.1 生成文档

```
POST /api/v1/documents/generate
```

**Request Body:**
```json
{
  "docType": "requirements",
  "title": "DRG-Agent 需求分析文档",
  "context": {
    "includeRequirements": true,
    "includeUseCases": true,
    "includeAnalysisModel": true,
    "sourceTaskIds": ["TASK-GROUP-20260519-001"],
    "codeDirectories": [],
    "ruleVersionId": "RV-20260519-001"
  },
  "template": "srs_template_v1"
}
```

**docType 枚举值:** `requirements` | `design` | `testing` | `meeting_minutes` | `configuration`

**Response (202):**
```json
{
  "code": 202,
  "data": {
    "docTaskId": "DOC-TASK-20260519-001",
    "status": "pending",
    "createdAt": "2026-05-19T11:00:00Z"
  }
}
```

### 5.2 查询文档生成状态

```
GET /api/v1/documents/tasks/{docTaskId}
```

### 5.3 获取文档预览

```
GET /api/v1/documents/{docId}/preview
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "docId": "DOC-20260519-001",
    "title": "DRG-Agent 需求分析文档",
    "type": "requirements",
    "version": "V1.0",
    "status": "draft",
    "content": "# DRG-Agent 需求分析文档\n\n## 1. 引言\n...",
    "metadata": {
      "createdAt": "2026-05-19T11:05:00Z",
      "generatedBy": "文档生成智能体",
      "sourceTasks": ["TASK-GROUP-20260519-001"],
      "modelUsed": "deepseek-v3"
    },
    "sections": [
      { "id": "sec-1", "title": "引言", "status": "generated" },
      { "id": "sec-2", "title": "总体描述", "status": "generated" },
      { "id": "sec-3", "title": "功能需求", "status": "pending" }
    ]
  }
}
```

### 5.4 编辑文档

```
PUT /api/v1/documents/{docId}
```

**Request Body:**
```json
{
  "content": "# 修改后的内容...",
  "title": "更新后的标题"
}
```

### 5.5 提交文档到虚拟文档系统

```
POST /api/v1/documents/{docId}/submit
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "docId": "DOC-20260519-001",
    "status": "submitted",
    "submittedAt": "2026-05-19T11:30:00Z",
    "submissionRecord": {
      "submitter": "用户/文档提交智能体",
      "version": "V1.0",
      "filePath": "/documents/requirements/DOC-20260519-001_v1.0.pdf",
      "checksum": "sha256:abc123..."
    }
  }
}
```

### 5.6 获取文档列表

```
GET /api/v1/documents?type=requirements&status=submitted&keyword=DRG&page=1&pageSize=20
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "docId": "DOC-20260519-001",
        "title": "DRG-Agent 需求分析文档",
        "type": "requirements",
        "status": "submitted",
        "version": "V1.0",
        "createdAt": "2026-05-19T11:05:00Z",
        "submittedAt": "2026-05-19T11:30:00Z",
        "generatedBy": "文档生成智能体",
        "fileSize": 245760
      }
    ],
    "total": 5,
    "page": 1,
    "pageSize": 20,
    "totalPages": 1
  }
}
```

### 5.7 获取文档详情

```
GET /api/v1/documents/{docId}
```

### 5.8 下载文档

```
GET /api/v1/documents/{docId}/download?format=pdf
```

**format 可选值:** `pdf` | `markdown` | `html`

### 5.9 获取文档版本历史

```
GET /api/v1/documents/{docId}/versions
```

### 5.10 删除文档

```
DELETE /api/v1/documents/{docId}
```

### 5.11 更新文档状态

```
PATCH /api/v1/documents/{docId}/status
```

**Request Body:**
```json
{
  "status": "archived"
}
```

**状态流转:** `draft` → `review` → `submitted` → `archived`

---

## 6. 测试用例接口 (TestCase)

### 6.1 生成测试用例

```
POST /api/v1/testcases/generate
```

**Request Body:**
```json
{
  "ruleVersionId": "RV-20260519-001",
  "scenarioTypes": ["normal", "boundary", "abnormal"],
  "scope": {
    "mdcList": ["MDCB"],
    "adrgList": ["BB1"],
    "includeAllRules": false
  },
  "sampleCaseIds": ["CASE-20260519-001"],
  "maxCount": 50
}
```

**Response (202):**
```json
{
  "code": 202,
  "data": {
    "testTaskId": "TEST-TASK-20260519-001",
    "status": "pending",
    "createdAt": "2026-05-19T12:00:00Z"
  }
}
```

### 6.2 查询测试用例生成状态

```
GET /api/v1/testcases/tasks/{testTaskId}
```

### 6.3 获取测试用例列表

```
GET /api/v1/testcases?scenarioType=normal&ruleVersionId=RV-20260519-001&page=1&pageSize=20
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "testCaseId": "TC-D-001",
        "title": "主诊断与手术正常命中 - 伤寒性脑膜炎+动脉内膜剥脱",
        "scenarioType": "normal",
        "priority": "high",
        "requirementRef": "FR-D-05",
        "ruleVersion": "DRG 2.0 演示规则",
        "inputCase": {
          "primaryDiagnosis": { "code": "A01.002+G01*", "name": "伤寒性脑膜炎" },
          "secondaryDiagnoses": [{ "code": "J96.0", "name": "急性呼吸衰竭" }],
          "primaryProcedure": { "code": "38.1000x002", "name": "动脉内膜剥脱术" }
        },
        "expectedResult": {
          "mdc": "MDCB",
          "adrg": "BB1",
          "drg": "BB11"
        },
        "expectedExplanation": "因 MCC 命中且未被排除...",
        "createdAt": "2026-05-19T12:05:00Z"
      },
      {
        "testCaseId": "TC-D-014",
        "title": "MCC 被排除表排除 - 边界测试",
        "scenarioType": "boundary",
        "priority": "medium",
        "requirementRef": "FR-D-07",
        "inputCase": {
          "primaryDiagnosis": { "code": "I10", "name": "原发性高血压" },
          "secondaryDiagnoses": [{ "code": "I10", "name": "原发性高血压" }]
        },
        "expectedResult": {
          "mdc": "MDCF",
          "adrg": "FV1",
          "drg": "FV15"
        },
        "expectedExplanation": "MCC I10 被主诊断排除...",
        "createdAt": "2026-05-19T12:05:01Z"
      }
    ],
    "total": 35,
    "page": 1,
    "pageSize": 20,
    "totalPages": 2
  }
}
```

### 6.4 获取单个测试用例

```
GET /api/v1/testcases/{testCaseId}
```

### 6.5 导出测试用例

```
POST /api/v1/testcases/export
```

**Request Body:**
```json
{
  "testCaseIds": ["TC-D-001", "TC-D-014"],
  "format": "excel"
}
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "downloadUrl": "/api/v1/testcases/export/TEST-EXPORT-20260519-001.xlsx"
  }
}
```

### 6.6 提交测试用例到文档系统

```
POST /api/v1/testcases/submit-to-documents
```

**Request Body:**
```json
{
  "testCaseIds": ["TC-D-001", "TC-D-014"],
  "docTitle": "DRG-Agent 测试文档 V1.0",
  "docType": "testing"
}
```

---

## 7. 任务中心接口 (Task)

### 7.1 获取任务列表

```
GET /api/v1/tasks?type=grouping&status=completed&page=1&pageSize=20
```

**type 可选值:** `grouping` | `document_gen` | `test_gen` | `all`

### 7.2 获取任务详情

```
GET /api/v1/tasks/{taskId}
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "taskId": "TASK-GROUP-20260519-001",
    "type": "grouping",
    "status": "completed",
    "startedAt": "2026-05-19T10:35:00Z",
    "finishedAt": "2026-05-19T10:35:02Z",
    "durationMs": 1534,
    "steps": [
      { "step": "case_parse", "status": "completed", "durationMs": 320 },
      { "step": "code_validate", "status": "completed", "durationMs": 45 },
      { "step": "rule_retrieve", "status": "completed", "durationMs": 180 },
      { "step": "drg_grouping", "status": "completed", "durationMs": 120 },
      { "step": "explain_generate", "status": "completed", "durationMs": 869 }
    ],
    "error": null
  }
}
```

### 7.3 取消任务

```
POST /api/v1/tasks/{taskId}/cancel
```

---

## 8. 系统配置接口 (System)

### 8.1 获取系统配置

```
GET /api/v1/system/config
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "llm": {
      "apiBase": "https://openkey.cloud/v1",
      "model": "deepseek-v3",
      "maxRetries": 3,
      "timeoutSeconds": 60
    },
    "storage": {
      "documentPath": "./documents",
      "ruleDataPath": "./data/rules"
    },
    "rules": {
      "activeRuleVersionId": "RV-20260519-001"
    }
  }
}
```

### 8.2 更新系统配置

```
PUT /api/v1/system/config
```

### 8.3 初始化演示数据

```
POST /api/v1/system/demo/init
```

一键导入样例规则和病历数据，用于课堂演示。

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "ruleVersionId": "RV-DEMO-001",
    "sampleCaseIds": ["CASE-DEMO-001", "CASE-DEMO-002", "CASE-DEMO-003"],
    "message": "演示数据初始化成功"
  }
}
```

### 8.4 健康检查

```
GET /api/v1/system/health
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "status": "healthy",
    "components": {
      "database": "connected",
      "llm_api": "reachable",
      "document_storage": "available",
      "celery": "running"
    },
    "uptime": "2h 15m"
  }
}
```

---

## 9. 智能体执行日志接口

### 9.1 获取执行日志

```
GET /api/v1/logs?taskId=TASK-GROUP-20260519-001&level=error&page=1&pageSize=50
```

**Response (200):**
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "LOG-001",
        "timestamp": "2026-05-19T10:35:01.234Z",
        "level": "info",
        "agent": "case_parser",
        "taskId": "TASK-GROUP-20260519-001",
        "message": "病历解析完成，提取到 3 个编码",
        "input": "主诊断：A01.002+G01*...",
        "output": "{ primaryDiagnosis: A01.002+G01* }"
      }
    ],
    "total": 25
  }
}
```

---

## 10. WebSocket 事件（可选扩展）

用于前端实时接收任务进度和状态变更：

```
ws://localhost:8000/ws/tasks/{taskId}
```

**服务端推送消息格式:**
```json
{
  "type": "task_progress",
  "taskId": "TASK-GROUP-20260519-001",
  "data": {
    "currentStep": "drg_grouping",
    "progress": 60,
    "status": "executing"
  }
}
```

---

## 11. 错误码定义

| 错误码 | 含义 | 场景 |
|--------|------|------|
| 40001 | 编码格式错误 | 主诊断 ICD 编码格式不合法 |
| 40002 | 必填字段缺失 | 主诊断未填写 |
| 40003 | 规则版本未激活 | 选择的规则版本状态不是 active |
| 40401 | 病历不存在 | caseId 不存在 |
| 40402 | 规则版本不存在 | ruleVersionId 不存在 |
| 40403 | 任务不存在 | taskId 不存在 |
| 40404 | 文档不存在 | docId 不存在 |
| 40901 | 重复提交 | 同一任务已在执行中 |
| 50001 | 规则引擎异常 | MDC/ADRG 匹配逻辑异常 |
| 50002 | LLM 调用失败 | 3次重试后仍失败 |
| 50003 | 文档生成失败 | 模板或上下文不足 |
| 50301 | LLM API 不可达 | API Base URL 连接失败 |
