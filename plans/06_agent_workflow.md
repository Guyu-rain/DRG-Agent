# 智能体工作流设计

## 1. 设计原则

### 1.1 核心原则

- **规则优先**: DRG 入组必须是确定性规则匹配，LLM 不参与分组决策
- **LLM 辅助**: LLM 用于非确定性任务：病历解析（NLP 提取）、解释润色、文档生成、测试用例构造
- **状态驱动**: 所有工作流基于 LangGraph StateGraph，通过显式 State 对象传递信息
- **失败降级**: 每个智能体节点有失败处理策略，保证工作流不会因单点失败而崩溃

### 1.2 智能体职责边界

| 智能体 | 类型 | 核心职责 |
|--------|------|----------|
| 病历解析智能体 | LLM | 从自由文本提取结构化编码字段 |
| 编码校验器 | 规则 | ICD/ICD-CM-3 格式校验（确定性） |
| 规则解析器 | 规则 | 解析 DRG 规则文件为索引结构 |
| 规则检索智能体 | 规则+LLM | 根据病历查找候选规则 |
| DRG 入组智能体 | 规则 | 执行 MDC→ADRG→DRG 匹配（确定性） |
| 解释生成智能体 | LLM | 将证据链转换为自然语言解释 |
| 文档生成智能体 | LLM+模板 | 生成工程文档 |
| 测试用例生成智能体 | LLM+规则 | 构造测试场景和用例 |
| 文档提交智能体 | 规则 | 将文档存入虚拟文档系统 |

---

## 2. 入组工作流 (GroupingWorkflow)

### 2.1 State 定义

```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class GroupingState(TypedDict):
    # 输入
    case_id: str
    rule_version_id: str

    # 阶段1: 病历解析
    raw_text: Optional[str]           # 原始病历文本
    structured_data: Optional[dict]   # 结构化输入数据
    parsed_case: Optional[dict]       # 解析后的标准化病历

    # 阶段2: 编码校验
    validation_passed: Optional[bool]
    validation_errors: list[str]
    validation_warnings: list[str]

    # 阶段3: 规则检索
    mdc_candidates: Optional[list]
    adrg_candidates: Optional[list]
    mcc_entries: Optional[list]
    cc_entries: Optional[list]
    exclusion_table: Optional[list]

    # 阶段4: DRG 入组 (规则引擎)
    grouping_result: Optional[dict]   # 完整入组结果

    # 阶段5: 解释生成
    explanation: Optional[str]        # 自然语言解释

    # 任务元数据
    task_id: Optional[str]
    status: str                       # "executing" | "completed" | "failed"
    error: Optional[dict]             # 错误信息
```

### 2.2 工作流结构

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ case_parse  │  病历解析智能体
                    │  (LLM)      │  LLM 从文本提取编码
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  validate   │  编码校验器
                    │  (Rule)     │  ICD 格式校验
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
              ┌─────┤  is_valid?  │  条件分支
              │ No  └──────┬──────┘
              │            │ Yes
              │            │
    ┌─────────▼──┐  ┌─────▼──────────┐
    │mark_as_error│  │ rule_retrieve  │  规则检索智能体
    │  (异常处理) │  │ (Rule + LLM)   │  加载规则索引
    └──────┬──────┘  └─────┬──────────┘
           │               │
           │        ┌──────▼──────┐
           │        │ drg_group   │  DRG 入组智能体
           │        │  (Rule)     │  三重匹配引擎
           │        └──────┬──────┘
           │               │
           │        ┌──────▼──────┐
           │  ┌─────┤ is_grouped? │  条件分支
           │  │ No  └──────┬──────┘
           │  │            │ Yes
           │  │            │
           │ ┌▼────────┐┌──▼──────────┐
           │ │explain_ ││  explain_    │  解释生成智能体
           │ │failure  ││  success     │  LLM 生成自然语言
           │ │(LLM)    ││  (LLM)       │
           │ └────┬────┘└──────┬───────┘
           │      │            │
           │      └─────┬──────┘
           │            │
           ▼            ▼
        ┌──────────────────┐
        │   save_result    │  保存结果到数据库
        └────────┬─────────┘
                 │
           ┌─────▼─────┐
           │    END    │
           └───────────┘
```

### 2.3 各节点详细设计

#### 2.3.1 case_parse (病历解析智能体)

```python
def case_parse_agent(state: GroupingState) -> dict:
    """
    将病历文本或结构化数据解析为标准化的 PatientCase 对象。
    
    输入: state.raw_text 或 state.structured_data
    输出: state.parsed_case
    """

    # 如果是结构化输入，直接映射
    if state.get("structured_data"):
        return {"parsed_case": map_structured_to_parsed(state["structured_data"])}

    # 如果是自由文本，调用 LLM 提取
    prompt = f"""
    你是一位专业的 ICD 编码专家。请从以下病历文本中提取关键信息。

    要求：
    1. 识别主诊断（主要疾病）及其 ICD 编码 —— 若文本仅有疾病名称无编码，尝试根据医学知识推断编码；若无法确定，code 字段留空
    2. 识别所有次要诊断（并发症/合并症）及其 ICD 编码
    3. 识别主要手术/操作及其 ICD-CM-3 编码 —— 若仅有手术名称，尝试推断编码
    4. 识别其他手术/操作
    5. 提取患者基本信息（年龄、性别等）
    6. 提取出院方式（如有）

    输出 JSON 格式：
    {{
      "primaryDiagnosis": {{"code": "...(可为空)", "name": "...", "sourceText": "..."}},
      "secondaryDiagnoses": [{{"code": "...(可为空)", "name": "...", "sourceText": "..."}}],
      "primaryProcedure": {{"code": "...(可为空)", "name": "...", "sourceText": "..."}},
      "otherProcedures": [{{"code": "...(可为空)", "name": "..."}}],
      "patientInfo": {{"age": ..., "gender": "..."}},
      "dischargeType": "...",
      "warnings": ["未能识别的字段列表"]
    }}

    注意：若某些诊断/手术仅有名称而无编码，请在 warnings 中注明，但不要丢失名称信息。

    病历文本：
    {state["raw_text"]}
    """

    # 调用 LLM
    result = call_llm_with_retry(prompt)

    # 解析 JSON 输出
    parsed = parse_llm_json_output(result)

    return {
        "parsed_case": parsed,
        "status": "parsing"
    }
```

**失败处理：**
- LLM 返回非 JSON → 3次重试，仍失败则标记状态为 `error`
- 返回空结果 → 标记 `parsed_case` 为 null，提示用户使用结构化输入

**字段映射层 (Chinese → English):**

`map_structured_to_parsed()` 函数在 `CaseService._normalize_case_input()` 中实现，负责将输入数据的中文键名转换为内部英文键名：

```python
def _normalize_case_input(data: dict) -> dict:
    """将中文字段名映射为内部英文键名，同时去重重复的手术/诊断记录。"""
    normalized = {}

    if "性别" in data:
        normalized["gender"] = data["性别"]
    if "年龄" in data:
        normalized["age"] = data["年龄"]

    # 主要诊断
    if "主要诊断" in data:
        diag = data["主要诊断"]
        normalized["primaryDiagnosis"] = {
            "code": diag.get("疾病编码"),
            "name": diag.get("疾病名称"),
        }

    # 次要诊断 (去重)
    if "次要诊断列表" in data:
        seen = set()
        diags = []
        for d in data["次要诊断列表"]:
            code = d.get("疾病编码")
            if code and code not in seen:
                seen.add(code)
                diags.append({"code": code, "name": d.get("疾病名称")})
            elif not code:
                diags.append({"code": None, "name": d.get("疾病名称")})
        normalized["secondaryDiagnoses"] = diags

    # 主要手术
    if "主要手术" in data:
        proc = data["主要手术"]
        normalized["primaryProcedure"] = {
            "code": proc.get("手术编码"),
            "name": proc.get("手术名称"),
            "level": proc.get("手术级别"),
        }

    # 其他手术 (去重)
    if "其他手术列表" in data:
        seen = set()
        procs = []
        for p in data["其他手术列表"]:
            code = p.get("手术编码")
            if code and code not in seen:
                seen.add(code)
                procs.append({"code": code, "name": p.get("手术名称"), "level": p.get("手术级别")})
            elif not code:
                procs.append({"code": None, "name": p.get("手术名称"), "level": p.get("手术级别")})
        normalized["otherProcedures"] = procs

    return normalized
```

> **支持的文件格式**: `example/drg_example.json` (含编码) 和 `example/drg_example_nocode.json` (仅名称，无编码) 均可通过此映射层导入。无编码场景下 `code` 为 `None`，后续由病历解析智能体或用户手动补充。

#### 2.3.2 validate (编码校验器)

```python
def validate_codes(state: GroupingState) -> dict:
    """
    对解析出的编码进行格式校验。

    校验规则：
    - ICD 编码格式: 大写字母+数字+可选符号(./+*)
    - ICD-CM-3 编码格式: 数字+可选字母+可选x+数字
    - 主诊断名称必须存在
    - 编码为空时 (nocode 场景): 记录 warning 但不阻止流程
    """

    case = state["parsed_case"]
    errors = []
    warnings = []

    # 校验主诊断
    if not case.get("primaryDiagnosis") or not case["primaryDiagnosis"].get("name"):
        errors.append("主诊断缺失")
    elif not case["primaryDiagnosis"].get("code"):
        warnings.append("主诊断编码缺失，仅有名称: " + case["primaryDiagnosis"]["name"])
    elif not validate_icd_format(case["primaryDiagnosis"]["code"]):
        errors.append(f"主诊断编码格式错误: {case['primaryDiagnosis']['code']}")

    # 校验次要诊断
    for diag in case.get("secondaryDiagnoses", []):
        code = diag.get("code")
        if code and not validate_icd_format(code):
            errors.append(f"次要诊断编码格式错误: {code}")
        elif not code and diag.get("name"):
            warnings.append(f"次要诊断仅名称无编码: {diag['name']}")

    # 校验手术编码
    if case.get("primaryProcedure"):
        proc = case["primaryProcedure"]
        if proc.get("code") and not validate_icd_cm3_format(proc["code"]):
            errors.append(f"主要手术编码格式错误: {proc['code']}")
        elif not proc.get("code") and proc.get("name"):
            warnings.append(f"主要手术仅名称无编码: {proc['name']}")

    return {
        "validation_passed": len(errors) == 0,  # 仅 error 阻止流程; warning 不阻止
        "validation_errors": errors,
        "validation_warnings": warnings
    }
```

#### 2.3.3 is_valid 条件路由

```python
def is_valid_route(state: GroupingState) -> Literal["rule_retrieve", "mark_as_error"]:
    """判断编码校验是否通过"""
    if state["validation_passed"]:
        return "rule_retrieve"
    else:
        return "mark_as_error"
```

#### 2.3.4 rule_retrieve (规则检索智能体)

```python
def rule_retrieve_agent(state: GroupingState) -> dict:
    """
    根据病历编码，从规则库中检索候选规则。
    这是一个确定性操作 + LLM 辅助优化。
    """

    case = state["parsed_case"]
    primary_diag_code = case["primaryDiagnosis"]["code"]
    secondary_codes = [d["code"] for d in case.get("secondaryDiagnoses", []) if d.get("code")]
    primary_proc_code = case.get("primaryProcedure", {}).get("code")

    # 确定性: 根据 ICD 前缀匹配 MDC
    mdc_candidates = mdc_matcher.find_mdc(primary_diag_code)

    if not mdc_candidates:
        # LLM 辅助: 尝试猜测可能的 MDC
        prompt = f"""
        以下诊断编码无法直接匹配 MDC:
        - 主诊断: {primary_diag_code}
        
        请根据你的医学知识，建议这个诊断可能属于哪个 MDC 大类。
        如果无法确定，请明确指出。
        """
        llm_suggestion = call_llm_with_retry(prompt)
        return {
            "mdc_candidates": [],
            "mdc_llm_suggestion": llm_suggestion
        }

    # ADRG 候选：根据 MDC + 手术
    adrg_candidates = adrg_matcher.find_adrg(mdc_candidates, primary_proc_code)

    # MCC/CC 查找
    mcc_entries = cc_mcc_service.find_mcc_cc(secondary_codes)

    return {
        "mdc_candidates": mdc_candidates,
        "adrg_candidates": adrg_candidates,
        "mcc_entries": mcc_entries
    }
```

#### 2.3.5 drg_group (DRG 入组智能体 - 规则引擎)

```python
def drg_group_agent(state: GroupingState) -> dict:
    """
    执行确定性 DRG 入组，不调用 LLM。
    这是系统的核心逻辑。
    """

    case = state["parsed_case"]

    # Step 1: MDC 匹配
    mdc_result = mdc_matcher.match(case["primaryDiagnosis"]["code"])
    if not mdc_result:
        return {
            "grouping_result": {
                "is_grouped": False,
                "stage": "mdc_matching",
                "reason": f"主诊断 {case['primaryDiagnosis']['code']} 无法匹配 MDC",
                "mdc_code": None,
                "adrg_code": None,
                "drg_code": None,
                "evidence": []
            }
        }

    # Step 2: ADRG 匹配
    primary_proc = case.get("primaryProcedure", {}).get("code")
    adrg_result = adrg_matcher.match(mdc_result.code, case["primaryDiagnosis"]["code"], primary_proc)
    if not adrg_result:
        return {
            "grouping_result": {
                "is_grouped": False,
                "stage": "adrg_matching",
                "reason": f"MDC={mdc_result.code} 下无法匹配 ADRG",
                "mdc_code": mdc_result.code,
                "mdc_name": mdc_result.name,
                "adrg_code": None,
                "drg_code": None,
                "evidence": [mdc_result.evidence]
            }
        }

    # Step 3: MCC/CC 判定
    secondary_codes = [d["code"] for d in case.get("secondaryDiagnoses", []) if d.get("code")]
    cc_result = cc_mcc_service.evaluate(secondary_codes, case["primaryDiagnosis"]["code"])

    # Step 4: DRG 分组
    drg_result = drg_matcher.match(adrg_result.code, cc_result.level)

    # Step 5: 构建证据链
    evidence = build_evidence_chain(mdc_result, adrg_result, cc_result, drg_result)

    return {
        "grouping_result": {
            "is_grouped": True,
            "mdc_code": mdc_result.code,
            "mdc_name": mdc_result.name,
            "adrg_code": adrg_result.code,
            "adrg_name": adrg_result.name,
            "drg_code": drg_result.code,
            "drg_name": drg_result.name,
            "evidence": evidence,
            "candidate_rules": drg_result.candidates,
            "warnings": cc_result.warnings
        }
    }
```

#### 2.3.6 explain (解释生成智能体)

```python
def explain_agent(state: GroupingState) -> dict:
    """
    将结构化的证据链转换为面向用户的自然语言解释。
    这是 LLM 发挥作用的环节。
    """

    result = state["grouping_result"]

    if result["is_grouped"]:
        prompt = f"""
        你是 DRG 入组解释专家。请将以下证据链转换为一段清晰的中文解释。

        DRG 入组结果：
        - MDC: {result['mdc_code']} ({result['mdc_name']})
        - ADRG: {result['adrg_code']} ({result['adrg_name']})
        - DRG: {result['drg_code']} ({result['drg_name']})

        证据链：
        {json.dumps(result['evidence'], ensure_ascii=False, indent=2)}

        要求：
        1. 用连贯的文字说明推理过程
        2. 明确每一层判断的依据
        3. 如果涉及 MCC/CC 判定和排除表，需要特别说明
        4. 解释字数控制在 200-500 字
        5. 语气专业但不生硬
        """
    else:
        prompt = f"""
        你是 DRG 入组解释专家。以下病例未能成功入组，请生成友好的说明。

        失败信息：
        - 失败阶段: {result['stage']}
        - 原因: {result['reason']}
        - 已匹配信息: {result.get('mdc_code', '无')}

        要求：
        1. 说明为什么无法入组
        2. 给出可能的修正建议
        3. 字数控制在 100-300 字
        """

    explanation = call_llm_with_retry(prompt)
    return {"explanation": explanation}
```

---

## 3. 文档生成工作流 (DocumentGenWorkflow)

### 3.1 State 定义

```python
class DocumentGenState(TypedDict):
    doc_type: str                      # requirements|design|testing|management|configuration
    title: str
    context: dict                      # 生成上下文配置
    template_name: str

    # 中间状态
    collected_context: Optional[dict]  # 收集到的上下文
    generated_content: Optional[str]   # LLM 生成的原始内容

    # 输出
    doc_id: Optional[str]
    status: str                         # pending|running|completed|failed
    error: Optional[str]
```

### 3.2 工作流结构

```
START
  │
  ▼
context_collect    ── 收集生成上下文（读取需求、代码目录、规则等）
  │
  ▼
document_generate  ── LLM 根据模板生成文档内容
  │
  ▼
format_output      ── 格式化为 Markdown/PDF
  │
  ▼
save_document      ── 写入文件和数据库
  │
  ▼
 END
```

### 3.3 上下文收集节点

```python
def context_collect_agent(state: DocumentGenState) -> dict:
    """根据文档类型收集生成所需的上下文"""

    context = {}

    if state["doc_type"] == "requirements":
        # 收集功能需求、用例、分析模型等
        context = {
            "system_description": "DRG-Agent 医保入组智能体系统",
            "modules": ["DRG入组", "文档自动生成", "测试用例生成", "虚拟文档系统"],
            "user_roles": ["医生/编码员", "业务专家", "项目经理", "测试人员"],
            "grouping_results": fetch_recent_grouping_results(limit=5),
            "rule_versions": fetch_rule_versions(),
        }

    elif state["doc_type"] == "design":
        # 收集代码结构、接口定义、数据库模型等
        context = {
            "api_endpoints": collect_api_endpoints(),
            "data_models": collect_data_models(),
            "agent_list": collect_agent_definitions(),
            "technology_stack": fetch_tech_stack(),
        }

    elif state["doc_type"] == "testing":
        # 收集测试用例、规则、病历样本等
        context = {
            "test_cases": fetch_test_cases(),
            "rule_versions": fetch_rule_versions(),
            "sample_cases": fetch_sample_cases(limit=10),
        }

    return {"collected_context": context}
```

### 3.4 文档生成智能体

```python
def document_generate_agent(state: DocumentGenState) -> dict:
    """
    根据模板和上下文，调用 LLM 生成文档内容。
    不同文档类型使用不同的 prompt 模板。
    """

    template = load_template(state["doc_type"], state["template_name"])

    prompt = template.format(
        title=state["title"],
        context=json.dumps(state["collected_context"], ensure_ascii=False, indent=2)
    )

    # 如果内容过长，分段生成
    sections = split_prompt_into_sections(prompt, max_tokens=6000)
    full_content = []

    for section in sections:
        content = call_llm_with_retry(section)
        full_content.append(content)

    return {
        "generated_content": "\n\n".join(full_content),
        "status": "running"
    }
```

**Prompt 模板设计原则:**
- 每个模板包含：封面信息、版本记录、目录框架、正文大纲
- LLM 负责填充正文内容
- 模板中包含占位符 `{{placeholder}}`，LLM 填空
- 如果 LLM 生成失败，使用纯模板输出（不含智能生成内容）

---

## 4. 测试用例生成工作流 (TestGenWorkflow)

### 4.1 State 定义

```python
class TestGenState(TypedDict):
    # 输入
    rule_version_id: str
    scenario_types: list[str]          # ["normal", "boundary", "abnormal"]
    scope: dict                        # {mdc_list, adrg_list, include_all}
    sample_case_ids: list[str]
    max_count: int

    # 中间状态
    rule_analysis: Optional[dict]      # 规则分析结果
    scenarios: Optional[list]          # 构建的测试场景

    # 输出
    test_cases: Optional[list]
    status: str
```

### 4.2 工作流结构

```
START
  │
  ▼
rule_analyze       ── 分析规则，提取可测条件组合
  │
  ▼
scenario_construct ── 构造正常/边界/异常场景
  │
  ▼
testcase_generate  ── LLM 批量生成测试用例
  │
  ▼
save_testcases     ── 存入测试用例库
  │
  ▼
 END
```

### 4.3 场景构造逻辑（确定性）

```python
def scenario_construct_agent(state: TestGenState) -> dict:
    """
    根据规则分析结果，确定性地构造测试场景。
    LLM 不参与场景构造，确保覆盖完整。
    """

    rules = state["rule_analysis"]
    scenarios = []

    # 正常场景：合法的诊断+手术组合
    if "normal" in state["scenario_types"]:
        for adrg in rules.get("adrg_list", []):
            for diag in adrg["valid_diagnoses"][:3]:
                scenarios.append({
                    "type": "normal",
                    "description": f"正常场景: ADRG={adrg['code']}, 诊断={diag}",
                    "input": {"primaryDiagnosis": diag, "primaryProcedure": adrg["sample_procedure"]},
                    "expected": {"adrg": adrg["code"]}
                })

    # 边界场景：MCC 命中/未命中/被排除
    if "boundary" in state["scenario_types"]:
        for adrg in rules.get("adrg_with_cc", []):
            # 场景1: MCC 命中
            scenarios.append({
                "type": "boundary",
                "description": f"边界场景: ADRG={adrg['code']}, 有 MCC 命中",
                "input": {"primaryDiagnosis": adrg["primary_diag"], "secondaryDiagnoses": [adrg["sample_mcc"]]},
                "expected": {"has_mcc": True, "drg_contains_mcc": True}
            })
            # 场景2: MCC 被排除
            if adrg.get("excluded_mcc"):
                scenarios.append({
                    "type": "boundary",
                    "description": f"边界场景: ADRG={adrg['code']}, MCC 被排除",
                    "input": {"primaryDiagnosis": adrg["primary_diag"], "secondaryDiagnoses": [adrg["excluded_mcc"]]},
                    "expected": {"has_mcc": False, "drg_contains_mcc": False}
                })
            # 场景3: 无 MCC
            scenarios.append({
                "type": "boundary",
                "description": f"边界场景: ADRG={adrg['code']}, 无 MCC",
                "input": {"primaryDiagnosis": adrg["primary_diag"], "secondaryDiagnoses": []},
                "expected": {"has_mcc": False}
            })

    # 异常场景
    if "abnormal" in state["scenario_types"]:
        scenarios.extend([
            {"type": "abnormal", "description": "编码格式错误", "input": {"primaryDiagnosis": "ZZZ999"}},
            {"type": "abnormal", "description": "主诊断缺失", "input": {"primaryDiagnosis": ""}},
            {"type": "abnormal", "description": "手术编码非法", "input": {"primaryDiagnosis": "A01.002", "primaryProcedure": "INVALID"}},
            {"type": "abnormal", "description": "编码无法匹配 MDC", "input": {"primaryDiagnosis": "Z99.9"}},
            {"type": "abnormal", "description": "规则文件格式错误", "input": {"primaryDiagnosis": "A01.002", "primaryProcedure": "38.1000x002"}},
        ])

    return {"scenarios": scenarios[:state.get("max_count", 50)]}
```

### 4.4 测试用例生成智能体

```python
def testcase_generate_agent(state: TestGenState) -> dict:
    """
    根据场景，调用 LLM 生成完整的测试用例。
    包括用例编号、标题、优先级、输入病历、预期结果。
    """

    prompt = f"""
    你是测试用例设计专家。请根据以下测试场景，生成完整的测试用例。

    规则版本信息：
    {json.dumps(state['rule_analysis'], ensure_ascii=False, indent=2)}

    测试场景：
    {json.dumps(state['scenarios'], ensure_ascii=False, indent=2)}

    要求：
    1. 每个场景生成一个测试用例
    2. 用例包含：编号(TC-X-XXX)、标题、类型、优先级、需求引用
    3. 输入病历要包含完整字段（主诊断、次要诊断、主要手术）
    4. 预期结果包含预期的 MDC、ADRG、DRG 和关键解释点
    5. 正常场景优先级为 "high"，边界为 "medium"，异常为 "medium"

    输出 JSON 数组：
    [{{
      "testCaseId": "TC-D-001",
      "title": "...",
      "scenarioType": "normal|boundary|abnormal",
      "priority": "high|medium|low",
      "inputCase": {{"primaryDiagnosis": {{...}}, ...}},
      "expectedResult": {{"mdc": "...", "adrg": "...", "drg": "..."}},
      "expectedExplanation": "..."
    }}]
    """

    result = call_llm_with_retry(prompt)
    test_cases = parse_llm_json_output(result)
    return {"test_cases": test_cases}
```

---

## 5. 多智能体协作模式

### 5.1 串行协作（入组工作流）

```
病历解析 → 编码校验 → 规则检索 → DRG入组 → 解释生成
```

每个节点的输出是下一个节点的输入。

### 5.2 条件分支协作

```
编码校验 → [通过] → 继续入组
         → [失败] → 标记异常，停止入组
```

```
DRG入组 → [成功] → 生成成功解释
        → [失败] → 生成失败解释
```

### 5.3 并行协作（文档生成 + 测试用例生成）

入组完成后，可以触发并行任务：
```
入组完成
  ├──→ 文档生成智能体 (异步)
  ├──→ 测试用例生成智能体 (异步)
  └──→ 文档提交智能体 (异步)
```

### 5.4 事件驱动协作

```
领域事件: "入组任务已完成"
  ├──→ 触发: 文档生成建议
  ├──→ 触发: 测试用例生成建议
  └──→ 触发: 结果通知
```

---

## 6. AgentOrchestrator 实现

```python
# server/app/agents/orchestration.py

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

class AgentOrchestrator:
    """智能体编排器，管理所有工作流的构建和执行"""

    def __init__(self, llm_client, rule_engine):
        self.llm_client = llm_client
        self.rule_engine = rule_engine
        self.memory = MemorySaver()

    def build_grouping_workflow(self) -> StateGraph:
        """构建 DRG 入组工作流"""

        workflow = StateGraph(GroupingState)

        # 注册节点
        workflow.add_node("case_parse", case_parse_agent)
        workflow.add_node("validate", validate_codes)
        workflow.add_node("rule_retrieve", rule_retrieve_agent)
        workflow.add_node("drg_group", drg_group_agent)
        workflow.add_node("explain", explain_agent)
        workflow.add_node("save_result", save_grouping_result)

        # 注册边
        workflow.add_edge(START, "case_parse")
        workflow.add_edge("case_parse", "validate")

        # 条件边: 校验通过?
        workflow.add_conditional_edges(
            "validate",
            is_valid_route,
            {
                "rule_retrieve": "rule_retrieve",
                "mark_as_error": "save_result"
            }
        )

        workflow.add_edge("rule_retrieve", "drg_group")
        workflow.add_edge("drg_group", "explain")
        workflow.add_edge("explain", "save_result")
        workflow.add_edge("save_result", END)

        return workflow.compile(checkpointer=self.memory)

    def execute_grouping(self, case_id: str, rule_version_id: str) -> dict:
        """执行入组工作流"""

        graph = self.build_grouping_workflow()

        initial_state = {
            "case_id": case_id,
            "rule_version_id": rule_version_id,
            "raw_text": get_case_raw_text(case_id),
            "status": "executing"
        }

        results = []
        for step in graph.stream(initial_state):
            results.append(step)

        return results

    def build_document_gen_workflow(self) -> StateGraph:
        """构建文档生成工作流"""
        workflow = StateGraph(DocumentGenState)

        workflow.add_node("context_collect", context_collect_agent)
        workflow.add_node("document_generate", document_generate_agent)
        workflow.add_node("format_output", format_output_agent)
        workflow.add_node("save_document", save_document_agent)

        workflow.add_edge(START, "context_collect")
        workflow.add_edge("context_collect", "document_generate")
        workflow.add_edge("document_generate", "format_output")
        workflow.add_edge("format_output", "save_document")
        workflow.add_edge("save_document", END)

        return workflow.compile()

    def build_test_gen_workflow(self) -> StateGraph:
        """构建测试用例生成工作流"""
        workflow = StateGraph(TestGenState)

        workflow.add_node("rule_analyze", rule_analyze_agent)
        workflow.add_node("scenario_construct", scenario_construct_agent)
        workflow.add_node("testcase_generate", testcase_generate_agent)
        workflow.add_node("save_testcases", save_testcases_agent)

        workflow.add_edge(START, "rule_analyze")
        workflow.add_edge("rule_analyze", "scenario_construct")
        workflow.add_edge("scenario_construct", "testcase_generate")
        workflow.add_edge("testcase_generate", "save_testcases")
        workflow.add_edge("save_testcases", END)

        return workflow.compile()
```

---

## 7. LLM 调用封装

```python
# server/app/llm/client.py

import openai
from app.core.config import settings
from app.core.logging import logger

class LLMClient:
    def __init__(self):
        openai.api_key = settings.LLM_API_KEY
        openai.api_base = settings.LLM_API_BASE

    def call(self, prompt: str, model: str = None, max_retries: int = 3) -> str:
        """调用 LLM，支持重试"""

        model = model or settings.LLM_MODEL

        for attempt in range(max_retries):
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,          # 较低温度保证一致性
                    max_tokens=4096,
                    timeout=settings.LLM_TIMEOUT
                )
                content = response.choices[0].message.content
                logger.info(f"LLM call success, tokens: {response.usage}")
                return content

            except openai.error.Timeout:
                logger.warning(f"LLM timeout, attempt {attempt + 1}/{max_retries}")
                time.sleep(2 ** attempt)      # 指数退避

            except openai.error.APIError as e:
                logger.error(f"LLM API error: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"LLM unexpected error: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

        raise Exception(f"LLM call failed after {max_retries} retries")

    def call_with_fallback(self, prompt: str, fallback_value: str = None) -> str:
        """调用 LLM，失败时返回降级值"""
        try:
            return self.call(prompt)
        except Exception as e:
            logger.error(f"LLM call failed with fallback: {e}")
            if fallback_value:
                return fallback_value
            raise
```

---

## 8. Prompt 管理策略

所有 Prompt 模板集中管理在 `server/app/llm/prompts/`：

```
prompts/
├── case_parse.txt           # 病历解析 prompt
├── rule_retrieve.txt        # 规则检索 prompt
├── explain_success.txt      # 成功解释 prompt
├── explain_failure.txt      # 失败解释 prompt
├── document_srs.txt         # 需求分析文档生成 prompt
├── document_design.txt       # 概要设计文档生成 prompt
├── document_test.txt         # 测试文档生成 prompt
└── testcase_generate.txt    # 测试用例生成 prompt
```

每个 prompt 文件包含：
1. 角色定义（你是什么专家）
2. 输入格式说明
3. 输出格式要求
4. 约束条件
5. 示例（可选）
