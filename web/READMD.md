# DRG-Agent 前端说明

## 1. 项目定位

`web/` 是 DRG-Agent 的前端工程，负责提供医保 DRG 入组智能体系统的浏览器端交互界面。前端采用前后端分离架构，通过 REST API 与后端通信。

**自 Phase 3 集成起，前端默认连接真实后端**（通过 Vite 代理转发到 `http://localhost:8000`）。MSW Mock 改为按需启用——仅当显式设置 `VITE_ENABLE_MSW=true` 时启用，用于后端未就绪时的离线前端开发。Vitest 单元测试始终使用 MSW Node 服务，与浏览器端开关无关。

当前前端覆盖以下功能页面：

- 任务中心
- DRG 入组工作台
- 规则管理
- 虚拟文档系统
- 测试用例管理
- 执行日志
- 系统配置

全局错误边界（`components/Common/ErrorBoundary.tsx`）包裹整个应用，单个页面组件渲染异常不会导致整页白屏。

## 2. 技术栈与依赖

核心框架：

- React 18
- TypeScript 5
- Vite 5
- React Router 6
- Zustand 4
- Ant Design 5
- Axios 1

开发与测试：

- Vitest
- Testing Library
- JSDOM
- MSW
- ESLint
- Prettier

包管理：

- Node.js >= 22
- pnpm 11，通过 Corepack 调用：`corepack pnpm ...`

## 3. 目录结构

```text
web/
├── public/
│   └── mockServiceWorker.js
├── src/
│   ├── components/
│   │   ├── Common/
│   │   └── Layout/
│   ├── hooks/
│   ├── mocks/
│   │   ├── data/
│   │   ├── browser.ts
│   │   ├── handlers.ts
│   │   └── server.ts
│   ├── pages/
│   │   ├── DRGGrouping/
│   │   ├── DocumentSystem/
│   │   ├── ExecutionLog/
│   │   ├── RuleManagement/
│   │   ├── Settings/
│   │   ├── TaskCenter/
│   │   └── TestCase/
│   ├── services/
│   ├── stores/
│   ├── types/
│   ├── utils/
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
├── package.json
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── tsconfig.json
└── vite.config.ts
```

## 4. 架构说明

### 4.1 页面层

页面代码位于 `src/pages/`：

- `TaskCenter/`：任务统计、任务列表、任务步骤详情。
- `DRGGrouping/`：核心入组工作台，包含病历输入、规则版本选择、执行入组、证据链展示。
- `RuleManagement/`：规则版本列表、规则导入、激活、搜索、规则详情 Tab。
- `DocumentSystem/`：文档类型入口、文档列表、文档详情、编辑、提交、版本历史。
- `TestCase/`：测试用例生成、列表、详情、执行、导出、提交文档系统。
- `ExecutionLog/`：执行日志筛选、展开查看输入输出。
- `Settings/`：LLM、存储、规则版本和健康检查配置。

### 4.2 组件层

通用组件位于 `src/components/`：

- `Layout/AppLayout.tsx`：主应用布局，包含侧边栏、顶部栏、内容区域和页脚。
- `Common/PageHeader.tsx`：统一页面标题区。
- `Common/Loading.tsx`：加载状态。
- `Common/EmptyState.tsx`：空状态。
- `Common/ErrorBoundary.tsx`：全局错误边界（类组件），捕获子树渲染异常。
- `Common/ErrorFallback.tsx`：错误边界的兜底界面，提供重试 / 刷新。

### 4.3 状态管理

状态管理位于 `src/stores/`，使用 Zustand：

- `groupingStore.ts`：病历提交、解析、入组执行、结果和历史任务。
- `documentStore.ts`：文档列表、当前文档、生成和提交。
- `testcaseStore.ts`：测试用例列表、筛选和生成任务。
- `taskStore.ts`：任务中心和执行日志。
- `settingsStore.ts`：系统配置和健康检查。

### 4.4 API 请求层

请求封装位于 `src/services/`：

- `api.ts`：Axios 实例、基础 URL、超时、统一错误提示。
- `cases.ts`：病历接口。
- `rules.ts`：规则接口。
- `grouping.ts`：入组接口。
- `documents.ts`：文档接口。
- `testcases.ts`：测试用例接口。
- `tasks.ts`：任务与日志接口。
- `system.ts`：系统配置与健康检查接口。

默认 API 地址为相对路径 `/api/v1`，开发环境由 Vite 代理（`vite.config.ts` 中的 `server.proxy`）转发到后端 `http://localhost:8000`，因此浏览器视角为同源、不触发跨域。

Axios 不设置固定请求超时，允许文档 / 测试用例生成持续执行多轮 LLM 工具调用。响应拦截器仍会对网络中断等错误给出友好中文提示。

如需直接指定后端地址（不走代理），可设置环境变量：

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 4.5 Mock 服务

Mock 位于 `src/mocks/`，使用 MSW，其响应结构与真实后端契约保持一致：

- `handlers.ts`：Mock API 路由。
- `browser.ts`：浏览器开发环境 Worker。
- `server.ts`：Vitest Node 环境 Mock Server。
- `data/`：病例、规则、入组结果、文档、测试用例、任务和日志样例数据。

**Phase 3 起浏览器端默认不启用 MSW**，`corepack pnpm dev` 直接连接真实后端。仅在后端未就绪、需离线开发前端时显式启用：

```bash
VITE_ENABLE_MSW=true corepack pnpm dev
```

Vitest 单元测试始终通过 `src/mocks/server.ts` 拦截请求，不受上述开关影响。

## 5. 安装依赖

在仓库根目录或 `web/` 目录下均可进入前端工程：

```bash
cd web
corepack pnpm install
```

如果 pnpm 提示构建脚本被拦截，本项目已在 `pnpm-workspace.yaml` 中允许：

- `esbuild`
- `msw`

正常执行 `corepack pnpm install` 即可完成安装。

## 6. 启动开发服务

前端默认连接真实后端，启动前请确保后端已运行（见 `server/README.md`，或在仓库根目录执行 `./start.sh` 一键启动整套环境）。

```bash
cd web
corepack pnpm dev
```

默认访问地址：

```text
http://localhost:5173/
```

Vite 会监听 `0.0.0.0`，局域网地址也会在终端中显示。若 5173 被占用，Vite 会自动改用 5174 等端口。

若后端尚未就绪、希望仅调试前端，可启用 MSW Mock：

```bash
VITE_ENABLE_MSW=true corepack pnpm dev
```

## 7. 关闭开发服务

如果开发服务运行在当前终端：

```text
Ctrl + C
```

如果服务在后台运行，可以先查找端口占用：

```bash
lsof -i :5173
```

然后结束对应进程：

```bash
kill <PID>
```

如需强制结束：

```bash
kill -9 <PID>
```

## 8. 常用脚本

```bash
corepack pnpm dev
```

启动 Vite 开发服务器。

```bash
corepack pnpm build
```

执行 TypeScript 类型检查并构建生产包。

```bash
corepack pnpm typecheck
```

只执行 TypeScript 类型检查。

```bash
corepack pnpm lint
```

执行 ESLint 检查。

```bash
corepack pnpm test
```

运行 Vitest 测试。

```bash
corepack pnpm format
```

使用 Prettier 格式化前端代码。

## 9. 构建产物

生产构建输出目录：

```text
web/dist/
```

`dist/` 为构建产物目录，不应手动编辑。重新构建会覆盖其中内容。

当前 Ant Design 相关依赖会让主 bundle 偏大，Vite 构建时可能提示 chunk size warning。这是未做代码分割时的正常提示，不影响运行。后续如需优化，可引入 `React.lazy` 或 Rollup `manualChunks`。

## 10. 测试说明

测试目录：

```text
src/__tests__/
```

当前测试覆盖：

- 主布局渲染与折叠。
- DRG 入组页面核心交互。
- 规则管理页面加载与搜索。
- 文档系统生成对话框。
- Zustand store 的关键状态动作。

运行：

```bash
corepack pnpm test
```

测试环境中使用 `src/mocks/server.ts` 拦截 API 请求，不依赖真实后端。

## 11. 与后端联调

Phase 3 起这是**默认模式**，无需额外环境变量。

1. 启动后端（确保 `http://localhost:8000/api/v1` 可访问）：

```bash
cd server && ../.venv/bin/uvicorn main:app --reload --port 8000
```

2. 启动前端：

```bash
cd web && corepack pnpm dev
```

3. 打开 <http://localhost:5173/>。前端请求 `/api/v1/*` 由 Vite 代理转发到后端，浏览器视角同源。

4. 首次使用在「系统配置」页点击「初始化演示数据」，或执行
   `curl -X POST http://localhost:8000/api/v1/system/demo/init`，导入规则与样例病历。

> 也可在仓库根目录执行 `./start.sh` 一键启动 Docker + 后端 + 前端并自动初始化演示数据。

## 12. 注意事项

- 本项目前端说明文件名为 `READMD.md`（沿用建仓时的命名）。
- Phase 3 起开发模式默认连接真实后端；MSW 仅在 `VITE_ENABLE_MSW=true` 时启用。
- 生产构建不会启用 MSW。
- 文档 / 测试用例生成含真实 LLM 调用，当前版本不设置固定请求超时，请等待模型完成。
- 通过根目录 `start.sh` 启动时，若 5173 被其他程序占用会直接报错，避免前端自动漂移到错误端口。
- 前端报「网络连接失败」时，多为后端未启动，请先启动 `server`。
- 不要提交 `node_modules/` 和 `dist/`。
