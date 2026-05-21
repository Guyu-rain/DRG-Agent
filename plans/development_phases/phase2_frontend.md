# Phase 2: 前端开发 + 测试验证

## 总览

**目标**: 完成 React + TypeScript 前端全部页面、组件和状态管理，使用 Mock Service Worker (MSW) 模拟后端 API，确保前端可独立开发、调试和测试。

**前置条件**: 
- Phase 1 后端 API 接口定义已明确 (`plans/03_api_interfaces.md`)
- Node.js 22 已安装 (fnm)
- pnpm 11.x 已配置 (corepack)

**完成的标志**: 
- `pnpm dev` 启动 Vite 开发服务器
- 所有 7 个页面可正常渲染和交互
- `pnpm test` 前端组件测试通过
- MSW mock 数据可覆盖所有 API 场景
- 页面在 Chrome/Safari 样式一致

---

## Step 1: 前端项目脚手架

**参照文档**: `plans/01_tech_stack.md` §2.4, `plans/02_architecture.md` §2.1

### 1.1 创建 Vite + React + TypeScript 项目

```bash
cd web
pnpm create vite . --template react-ts
```

### 1.2 安装依赖

```bash
pnpm add antd @ant-design/icons react-router-dom zustand axios
pnpm add -D @types/react @types/react-dom typescript vite
# 测试
pnpm add -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
# Mock API
pnpm add -D msw
# 代码质量
pnpm add -D eslint prettier @typescript-eslint/eslint-plugin @typescript-eslint/parser
```

### 1.3 配置文件

| 文件 | 说明 |
|------|------|
| `package.json` | 项目元信息、脚本命令 (dev/build/test/lint) |
| `tsconfig.json` | TypeScript 严格模式编译配置 |
| `vite.config.ts` | Vite 构建配置 + 路径别名 + 代理设置 |
| `.eslintrc.cjs` | ESLint 规则 |
| `.prettierrc` | 代码格式化规则 |

**验收**:
- [ ] `pnpm dev` 启动成功，浏览器打开显示 Vite 默认页面
- [ ] `pnpm build` 无错误
- [ ] TypeScript 严格模式: `tsconfig.json` 中 `"strict": true`

### 1.4 项目目录结构

```
web/src/
├── components/                  # 通用组件
│   ├── Layout/
│   │   ├── AppLayout.tsx        # 主布局 (Sider + Header + Content)
│   │   └── AppLayout.css
│   └── Common/
│       ├── Loading.tsx          # 全局加载组件
│       ├── EmptyState.tsx       # 空状态组件
│       ├── ErrorFallback.tsx    # 错误回退组件
│       └── PageHeader.tsx       # 页面标题组件
├── pages/                       # 页面 (详见 Step 3-7)
│   ├── TaskCenter/
│   ├── DRGGrouping/
│   ├── RuleManagement/
│   ├── DocumentSystem/
│   ├── TestCase/
│   ├── ExecutionLog/
│   └── Settings/
├── stores/                      # Zustand 状态管理
│   ├── groupingStore.ts
│   ├── documentStore.ts
│   ├── testcaseStore.ts
│   ├── taskStore.ts
│   └── settingsStore.ts
├── services/                    # API 请求层
│   ├── api.ts                   # Axios 实例 + 拦截器
│   ├── cases.ts                 # 病历 API
│   ├── rules.ts                 # 规则 API
│   ├── grouping.ts              # 入组 API
│   ├── documents.ts             # 文档 API
│   ├── testcases.ts             # 测试用例 API
│   ├── tasks.ts                 # 任务 API
│   └── system.ts                # 系统 API
├── mocks/                       # MSW 模拟数据
│   ├── handlers.ts              # 请求处理器
│   ├── server.ts                # Node 环境 MSW server
│   └── data/                    # Mock 数据
│       ├── cases.ts
│       ├── rules.ts
│       ├── grouping.ts
│       └── documents.ts
├── hooks/                       # 自定义 Hooks
│   ├── usePolling.ts            # 轮询 hook (任务状态)
│   └── useDebounce.ts           # 防抖 hook (搜索)
├── types/                       # TypeScript 类型定义
│   ├── api.ts                   # API 响应类型
│   ├── case.ts                  # 病历类型
│   ├── rule.ts                  # 规则类型
│   ├── grouping.ts              # 入组类型
│   ├── document.ts              # 文档类型
│   ├── testcase.ts              # 测试用例类型
│   └── task.ts                  # 任务类型
├── utils/                       # 工具函数
│   ├── format.ts                # 日期/数字格式化
│   └── constants.ts             # 常量定义
├── App.tsx                      # 根组件
├── main.tsx                     # 入口
└── index.css                    # 全局样式
```

---

## Step 2: 基础设施搭建

### 2.1 Ant Design 主题配置

文件: `src/App.tsx`

```tsx
import { ConfigProvider, App as AntApp } from 'antd';

const theme = {
  token: {
    colorPrimary: '#1F4E79',    // 主色 (与 SRS 文档一致)
    borderRadius: 6,
  },
};

<ConfigProvider theme={theme}>
  <AntApp>
    <RouterProvider router={router} />
  </AntApp>
</ConfigProvider>
```

### 2.2 路由配置

文件: `src/App.tsx`

**参照文档**: `plans/02_architecture.md` §2.1

| 路由 | 页面组件 | 说明 |
|------|---------|------|
| `/` | `TaskCenter` | 任务中心仪表盘（默认页） |
| `/drg` | `DRGGrouping` | DRG 入组工作台（核心页面） |
| `/rules` | `RuleManagement` | 规则版本管理 |
| `/docs` | `DocumentSystem` | 虚拟文档系统主页 |
| `/docs/:type` | `DocumentList` | 按类型浏览文档 |
| `/docs/:id` | `DocumentDetail` | 文档详情与预览 |
| `/tests` | `TestCase` | 测试用例管理 |
| `/logs` | `ExecutionLog` | 智能体执行日志 |
| `/settings` | `Settings` | 系统配置 |

### 2.3 主布局组件

文件: `src/components/Layout/AppLayout.tsx`

```
┌──────────────────────────────────────────┐
│  Header: DRG-Agent                    🔔  │
├──────────┬───────────────────────────────┤
│  Sider   │                               │
│  📊 任务  │                               │
│  🏥 入组  │     <Outlet />                │
│  📋 规则  │     (页面内容渲染区域)         │
│  📄 文档  │                               │
│  🧪 测试  │                               │
│  📝 日志  │                               │
│  ⚙️ 配置  │                               │
├──────────┴───────────────────────────────┤
│  Footer: DRG-Agent © 2026               │
└──────────────────────────────────────────┘
```

**要求**:
- Sider 使用 Ant Design `Menu` 组件，`mode="inline"`
- 菜单项带图标，高亮当前路由
- Sider 可折叠
- Header 显示系统名称和通知图标
- 使用 React Router `<Outlet />` 渲染子页面

**验收**:
- [ ] 点击侧边栏菜单正确切换路由
- [ ] 当前路由对应的菜单项高亮
- [ ] Sider 折叠/展开动画流畅

### 2.4 Axios API 请求层

文件: `src/services/api.ts`

```typescript
import axios, { AxiosError } from 'axios';
import { message } from 'antd';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 响应拦截器: 统一错误处理
apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiErrorResponse>) => {
    const msg = error.response?.data?.message || '网络错误';
    message.error(msg);
    return Promise.reject(error);
  }
);
```

**要求**:
- 统一的请求/响应拦截器
- HTTP 错误码自动提示 (antd message)
- 请求超时 30 秒
- 支持取消请求 (AbortController)

### 2.5 MSW Mock 服务

文件: `src/mocks/handlers.ts` + `src/mocks/server.ts`

**要求**:
- Mock 所有 Phase 1 定义的 43 个 API 接口
- Mock 数据包括: 课程示例病历、课程示例规则、课程示例入组结果、样例文档和测试用例
- 模拟异步延迟 (200-500ms)，真实模拟网络请求
- 模拟错误场景: 404、500、503

**验收**:
- [ ] 浏览器 DevTools Network 标签中可见 mock 请求
- [ ] Mock 数据与 `plans/03_api_interfaces.md` 中定义的响应 JSON 一致
- [ ] 刷新页面后 mock 数据保持一致

---

## Step 3: DRG 入组工作台页面（核心页面）

**参照文档**: `plans/02_architecture.md` §2.1 (核心页面组件关系), `plans/03_api_interfaces.md` §2, §4

文件: `src/pages/DRGGrouping/`

### 3.1 页面布局

```
┌────────────────────────────────────────────────────────────┐
│  DRG 入组工作台                                            │
├──────────────────────────┬─────────────────────────────────┤
│  左侧: 输入面板           │  右侧: 结果面板                  │
│                          │                                  │
│  规则版本: [下拉选择]     │  入组结果: BB11                 │
│                          │  神经系统复合手术，伴严重合并症   │
│  病历输入模式:            │                                  │
│  [文本模式] [结构化模式]  │  MDC: MDCB                     │
│                          │  ADRG: BB1                     │
│  ┌────────────────────┐  │  DRG: BB11                     │
│  │ 主诊断：A01.002... │  │                                  │
│  │ 次要诊断：J96.0    │  │  证据链:                        │
│  │ 主要手术：38.10... │  │  1. 主诊断 A01.002 命中 MDCB   │
│  │                     │  │  2. 手术 38.1000x002 命中 BB1  │
│  └────────────────────┘  │  3. J96.0 属于 MCC             │
│                          │  4. 未被排除表排除              │
│  [开始入组] [保存样例]   │  5. BB1→BB11 (MCC 分层)        │
│                          │                                  │
│                          │  [提交复核] [生成文档] [生成测试] │
└──────────────────────────┴─────────────────────────────────┘
```

### 3.2 子组件

| 组件 | 文件 | 功能 |
|------|------|------|
| `RuleVersionSelector` | `RuleVersionSelector.tsx` | 下拉选择活跃规则版本，调用 `GET /api/v1/rules/versions` |
| `PatientCaseInput` | `PatientCaseInput.tsx` | Tab 切换文本/结构化输入模式 |
| `TextModeInput` | `TextModeInput.tsx` | TextArea 自由文本输入 |
| `StructuredFormInput` | `StructuredFormInput.tsx` | 结构化表单 (主诊断、次要诊断、手术等字段) |
| `GroupingExecuteButton` | `GroupingExecuteButton.tsx` | 执行入组按钮，调用 `POST /api/v1/grouping/execute` |
| `GroupingResultPanel` | `GroupingResultPanel.tsx` | 入组结果展示面板 |
| `ResultSummary` | `ResultSummary.tsx` | DRG 组号/组名/MDC/ADRG 摘要卡片 |
| `EvidenceChain` | `EvidenceChain.tsx` | 证据链时间线可视化 (Ant Design Timeline) |
| `CandidateRules` | `CandidateRules.tsx` | 候选规则列表，显示命中/未命中原因 |
| `ActionButtons` | `ActionButtons.tsx` | 操作按钮组 (提交复核、生成文档、生成测试用例) |

### 3.3 Zustand Store

文件: `src/stores/groupingStore.ts`

```typescript
interface GroupingState {
  currentCaseId: string | null;
  currentCase: PatientCase | null;
  currentResult: GroupingResult | null;
  selectedRuleVersion: string | null;
  inputMode: 'text' | 'structured';
  isExecuting: boolean;
  isParsing: boolean;
  history: GroupingTaskSummary[];
  
  // Actions
  setRuleVersion: (id: string) => void;
  setInputMode: (mode: 'text' | 'structured') => void;
  submitCase: (data: CaseCreateRequest) => Promise<string>;
  parseCase: (caseId: string) => Promise<void>;
  executeGrouping: () => Promise<string>;
  fetchResult: (taskId: string) => Promise<void>;
  clearResult: () => void;
}
```

### 3.4 交互要点

- 病历输入后自动触发解析 (`POST /api/v1/cases/{caseId}/parse`)
- 解析完成后自动显示解析结果，允许用户修正
- 点击"开始入组"后，按钮显示 loading 动画
- 入组完成后自动轮询结果 (3 秒间隔，最多 30 秒)
- 证据链使用 Ant Design `Timeline` 组件，每条显示 step 编号和描述
- MCC/CC 判定部分用绿色 (命中) / 红色 (排除) 标签高亮

**验收**:
- [ ] 自由文本病历输入后，解析结果显示结构化字段
- [ ] 结构化表单可正常输入和提交
- [ ] 点击"开始入组"后 loading 状态正确显示
- [ ] 入组结果显示完整的 MDC/ADRG/DRG 和证据链
- [ ] 模拟入组失败场景时显示错误原因和建议
- [ ] 规则版本切换后提示"结果已过期，请重新入组"

---

## Step 4: 规则管理页面

**参照文档**: `plans/03_api_interfaces.md` §3

### 4.1 页面布局

```
┌────────────────────────────────────────────────┐
│  规则管理                                       │
├────────────────────────────────────────────────┤
│  [+ 导入规则]  [规则版本列表]                    │
│                                                 │
│  版本          状态      规则数量   导入时间      │
│  DRG 2.0 演示  ✅ 活跃   MDC:26   2026-05-19   │
│                [激活] [查看详情] [删除]          │
│                                                 │
│  选中版本详情:                                   │
│  ┌────────────────────────────────────────────┐ │
│  │ MDC 列表 (26)    ADRG 列表 (376)           │ │
│  │ MDCB 神经系统...  BB1 神经系统复合手术...   │ │
│  │ MDCF 循环系统...  BB2 神经系统其他手术...   │ │
│  │ ...              ...                        │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ DRG 列表 (628)    MCC/CC 列表              │ │
│  │ BB11 伴MCC        J96.0 急性呼吸衰竭 MCC   │ │
│  │ BB15 不伴CC       I10 原发性高血压 CC       │ │
│  │ ...              ...                        │ │
│  └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

### 4.2 功能列表

| 功能 | 接口 |
|------|------|
| 导入规则文件 (Excel/CSV) | `POST /api/v1/rules/import` |
| 规则版本列表 | `GET /api/v1/rules/versions` |
| 查看版本详情 (MDC/ADRG/DRG/MCC/CC 列表) | `GET /api/v1/rules/versions/{versionId}` |
| 激活规则版本 | `POST /api/v1/rules/versions/{versionId}/activate` |
| 删除规则版本 | `DELETE /api/v1/rules/versions/{versionId}` |
| 按编码搜索规则 | `GET /api/v1/rules/search?code=...&ruleType=...` |

**验收**:
- [ ] 文件上传后可看到导入进度
- [ ] 版本列表中，活跃版本显示绿色标记
- [ ] 点击"激活"后，原活跃版本变为非活跃
- [ ] 版本详情页以 Tab 展示 MDC/ADRG/DRG/MCC/CC 列表
- [ ] 删除非活跃版本前弹出确认对话框

---

## Step 5: 虚拟文档系统页面

**参照文档**: `plans/03_api_interfaces.md` §5, `plans/02_architecture.md` §2.1

### 5.1 页面布局

```
┌────────────────────────────────────────────────────────────────┐
│  虚拟文档系统                                                    │
├────────────────────────────────────────────────────────────────┤
│  筛选: [全部类型 ▾] [全部状态 ▾] [搜索...]       [+ 生成文档]   │
│                                                                 │
│  文档标题                 类型      状态      版本    操作       │
│  DRG-Agent 需求分析文档   SRS      已提交    V1.0   [查看]     │
│  DRG-Agent 概要设计文档   设计      草稿      V1.0   [编辑]     │
│  DRG-Agent 测试文档       测试      待审核    V1.0   [提交]     │
│  第一次会议纪要            管理      已归档    V1.0   [下载]     │
│                                                                 │
│  [上页] 1/1 [下页]                                              │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 页面拆分

主页面 `DocumentSystem` 提供类型卡片入口：
- 需求分析文档区 (requirements)
- 概要设计文档区 (design)
- 测试文档区 (testing)
- 会议纪要区 (management)
- 配置管理区 (configuration)

点击卡片进入 `DocumentList`，显示该类型下的文档列表。

### 5.3 文档生成对话框

```
┌─────────────────────────────────────┐
│  生成文档                            │
│                                     │
│  文档类型: [需求分析文档 ▾]          │
│  文档标题: [DRG-Agent 需求分析文档]   │
│                                     │
│  上下文配置:                         │
│  ☑ 包含功能需求                     │
│  ☑ 包含用例                         │
│  ☑ 包含分析模型                     │
│  □ 包含界面原型                     │
│  关联来源任务: [选择入组任务 ▾]      │
│  关联规则版本: [DRG 2.0 演示规则 ▾]  │
│                                     │
│  [取消] [生成]                      │
└─────────────────────────────────────┘
```

### 5.4 文档详情页

路由: `/docs/:id`

显示：
- 文档标题、类型、版本、状态
- 生成信息（生成智能体、模型、时间）
- 文档正文（Markdown 渲染）
- 章节导航
- 操作按钮：编辑、下载 PDF/Markdown、提交、归档、查看版本历史

**验收**:
- [ ] 文档列表支持类型/状态/关键词筛选
- [ ] 点击"生成文档"弹出配置对话框
- [ ] 文档内容以 Markdown 渲染显示
- [ ] 编辑文档后可以保存，版本号自动更新
- [ ] 提交文档后状态变为"已提交"
- [ ] 下载功能可导出 Markdown/PDF
- [ ] 版本历史列表显示历次修改

---

## Step 6: 测试用例管理页面

**参照文档**: `plans/03_api_interfaces.md` §6

### 6.1 页面布局

```
┌──────────────────────────────────────────────────────────────────────┐
│  测试用例管理                                                          │
├──────────────────────────────────────────────────────────────────────┤
│  生成配置:                    ┌──────────────────────────────────┐    │
│  规则版本: [DRG 2.0 ▾]       │ 筛选: [全部 ▾] [全部优先级 ▾]    │    │
│  场景类型:                    │                                   │    │
│  ☑ 正常 ☑ 边界 ☑ 异常        │ ID    标题              类型  操作 │    │
│  范围: [MDCB ▾]              │ TC-D-001 主诊断正常命中 正常 [执行] │    │
│  数量上限: [50]              │ TC-D-014 MCC被排除      边界 [执行] │    │
│  [生成用例]                   │ TC-D-025 主诊断缺失     异常 [执行] │    │
│                              │ ...                               │    │
│  [导出选中] [提交到文档系统]  │                                   │    │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 功能列表

| 功能 | 接口 |
|------|------|
| 生成测试用例 | `POST /api/v1/testcases/generate` |
| 测试用例列表 | `GET /api/v1/testcases?scenarioType=...` |
| 查看用例详情 | `GET /api/v1/testcases/{testCaseId}` |
| 导出测试用例 (Excel) | `POST /api/v1/testcases/export` |
| 提交到文档系统 | `POST /api/v1/testcases/submit-to-documents` |
| 执行测试用例 | 调用 `POST /api/v1/grouping/execute` 验证 |

**验收**:
- [ ] 生成配置表单可正常交互
- [ ] 生成后列表显示测试用例，按类型用不同颜色标签区分
- [ ] 点击某个测试用例可查看详情 (输入病历 + 预期结果)
- [ ] 可执行单个测试用例，显示实际结果 vs 预期结果的对比
- [ ] 导出 Excel 文件包含所有选中用例
- [ ] 提交到文档系统后跳转到文档页面

---

## Step 7: 任务中心 / 执行日志 / 系统配置页面

**参照文档**: `plans/03_api_interfaces.md` §7-9

### 7.1 任务中心

路由: `/`

显示仪表盘：
- 统计卡片: 总任务数 / 执行中 / 已完成 / 失败
- 最近任务列表 (支持按类型和状态筛选)
- 点击任务查看详情 (步骤列表、耗时、日志)

**验收**:
- [ ] 任务列表实时显示状态
- [ ] 可取消执行中的任务
- [ ] 任务详情显示每个步骤的耗时

### 7.2 执行日志页面

路由: `/logs`

- 日志列表 (时间、级别、智能体、消息)
- 筛选: 按任务 ID、日志级别、智能体名称
- 展开查看输入/输出详情

**验收**:
- [ ] 日志按时间倒序显示
- [ ] 级别用颜色区分 (info 蓝色、warning 橙色、error 红色)
- [ ] 可展开查看完整的 input/output JSON

### 7.3 系统配置页面

路由: `/settings`

- LLM 配置 (API Base, Model, Max Retries, Timeout)
- 存储路径配置
- 当前活跃规则版本
- 初始化演示数据按钮
- 健康检查状态面板

**验收**:
- [ ] 配置修改后保存到后端
- [ ] 初始化演示数据按钮调用后显示结果
- [ ] 健康检查面板显示各组件连接状态

---

## Step 8: Zustand 状态管理

**参照文档**: `plans/02_architecture.md` §5

文件: `src/stores/`

```typescript
// src/stores/groupingStore.ts
export const useGroupingStore = create<GroupingState>((set, get) => ({
  // state...
  // actions...
}));

// src/stores/documentStore.ts  
export const useDocumentStore = create<DocumentState>((set, get) => ({
  // state...
  // actions...
}));
```

**Store 设计原则**:
- 每个 store 独立管理一个模块的状态
- 异步操作在 action 中完成，使用 try/catch 处理错误
- 避免跨 store 直接引用，通过组件传递或事件协调

**验收**:
- [ ] 打开 React DevTools 可查看所有 store 状态
- [ ] 状态更新触发关联组件重新渲染
- [ ] 跨页面状态保持一致 (如规则版本选择影响入组页面)

---

## Step 9: TypeScript 类型定义

**参照文档**: `plans/03_api_interfaces.md`

文件: `src/types/`

要求所有 API 请求/响应类型与 `plans/03_api_interfaces.md` 完全一致：

```typescript
// src/types/api.ts
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// src/types/case.ts
export interface CaseCreateRequest {
  rawText?: string;
  structuredData?: StructuredCaseInput;
  sourceType: 'text' | 'structured';
}

export interface PatientCase {
  caseId: string;
  status: 'created' | 'parsing' | 'parsed' | 'validated' | 'error';
  // ... 所有字段与 05_data_model.md §2.1 一致
}

// src/types/grouping.ts
export interface GroupingExecuteRequest {
  caseId: string;
  ruleVersionId: string;
}

export interface GroupingResult {
  mdc: { code: string; name: string };
  adrg: { code: string; name: string };
  drg: { code: string; name: string };
  evidence: EvidenceItem[];
  explanation: string;
  candidateRules: CandidateRule[];
  warnings: string[];
}
```

**验收**:
- [ ] 所有 interface 与 `plans/03_api_interfaces.md` 中的 JSON 示例一致
- [ ] TypeScript 编译无类型错误: `pnpm typecheck`
- [ ] 枚举类型 (如 `docType`, `scenarioType`, `status`) 正确约束

---

## Step 10: 前端测试

### 10.1 组件单元测试

```bash
# 使用 vitest + @testing-library/react
pnpm test
```

测试结构:
```
web/src/
├── __tests__/
│   ├── components/
│   │   ├── AppLayout.test.tsx
│   │   └── Loading.test.tsx
│   ├── pages/
│   │   ├── DRGGrouping.test.tsx      # 核心页面必须有测试
│   │   ├── RuleManagement.test.tsx
│   │   └── DocumentSystem.test.tsx
│   └── stores/
│       ├── groupingStore.test.ts
│       └── documentStore.test.ts
```

**测试覆盖要求**:
- `DRGGrouping` 页面: 至少 5 个测试用例
  - 文本模式输入切换
  - 结构化表单提交
  - 入组执行 loading 状态
  - 入组成功结果显示
  - 入组失败错误提示
- `RuleManagement` 页面: 至少 3 个测试用例
- `DocumentSystem` 页面: 至少 3 个测试用例
- 每个 Zustand store: 至少 2 个测试用例

**验收**:
- [ ] `pnpm test` 全部通过
- [ ] 总测试用例数量 ≥ 20
- [ ] 核心页面测试覆盖关键交互路径

### 10.2 MSW 集成测试

在测试中启用 MSW，确保 API 调用被正确 mock。

```typescript
// src/__tests__/setup.ts
import { server } from '../mocks/server';
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## Step 11: 代码质量

### 11.1 ESLint + Prettier

```bash
pnpm lint        # ESLint 检查
pnpm format      # Prettier 格式化
```

### 11.2 TypeScript 类型检查

```bash
pnpm typecheck   # tsc --noEmit
```

**验收**:
- [ ] `pnpm lint` 零错误
- [ ] `pnpm typecheck` 零错误
- [ ] `pnpm build` 成功生成 `dist/` 目录

---

## Phase 2 最终验收清单

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 1 | 前端开发服务器启动 | `pnpm dev` → 浏览器打开正常 |
| 2 | 7 个页面路由可访问 | 手动点击侧边栏所有菜单项 |
| 3 | DRG 入组工作台完整交互 | 文本输入 → 解析 → 入组 → 结果显示 |
| 4 | 规则管理可导入/查看/激活 | 上传规则文件 → 版本列表更新 |
| 5 | 文档系统可筛选/生成/提交 | 生成文档 → 编辑 → 提交 |
| 6 | 测试用例可生成/导出 | 选择配置 → 生成 → 列表显示 |
| 7 | 任务中心显示任务列表 | 统计卡片 + 列表 + 详情 |
| 8 | MSW mock 覆盖所有 API | 网络面板无 404 请求 |
| 9 | 主题色正确 (#1F4E79) | 所有 Ant Design 组件使用品牌色 |
| 10 | 页面响应式布局 | Chrome/Safari 窗口缩放不溢 |
| 11 | 所有组件测试通过 | `pnpm test` 零失败 |
| 12 | 无编译/类型/lint 错误 | `pnpm build && pnpm typecheck && pnpm lint` |
| 13 | 错误状态有友好提示 | 网络断开/API 500 → antd message 错误提示 |

---

## 后续改进建议

1. **虚拟列表优化**: 文档和测试用例列表超 100 条时，使用 Ant Design `Table` 的虚拟滚动
2. **响应式适配**: 移动端和平板适配 (当前仅针对桌面端 1440px+)
3. **暗色模式**: 添加 Ant Design 暗色主题切换
4. **国际化 i18n**: 使用 `react-intl` 支持中英文切换
5. **E2E 测试**: 使用 Playwright 录制完整的用户操作流程
6. **性能优化**: React.lazy + Suspense 代码分割，减少首屏加载时间
7. **可访问性**: 添加 ARIA label，支持键盘导航
8. **前端监控**: 集成 Sentry 或自定义错误上报
