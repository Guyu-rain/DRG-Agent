# Phase 3: 前后端连接 + 整体测试验证

## 总览

**目标**: 将 Phase 1 (后端) 和 Phase 2 (前端) 对接，关闭 MSW mock，切换到真实后端 API。完成完整的端到端测试、性能测试、跨浏览器验证，确保系统在课程演示环境中可正常运行。

**前置条件**:
- Phase 1 后端所有测试通过，43 个 API 全部可用
- Phase 2 前端所有页面开发完成，组件测试通过
- Docker PostgreSQL + Redis 正常运行
- LLM API Key 已配置 (`.env` 文件)

**完成的标志**:
- 前端通过真实后端 API 完成全部业务流程
- 课程示例 (A01.002+G01* → BB11) 从输入到结果显示全链路通过
- 文档自动生成 → 编辑 → 提交全流程通过
- 测试用例生成 → 执行 → 验证全流程通过
- E2E 测试套件全部通过
- Chrome 和 Safari 渲染一致

---

## Step 1: 前后端 API 连接

### 1.1 关闭 MSW，连接真实后端

修改 `web/src/main.tsx`:

```typescript
// Phase 2 (开发阶段): 启用 MSW
// if (import.meta.env.DEV) {
//   const { worker } = await import('./mocks/browser');
//   await worker.start();
// }

// Phase 3 (集成阶段): 禁用 MSW，连接真实后端
// 不启用 MSW，直接调用 localhost:8000
```

### 1.2 Vite 代理配置

修改 `web/vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

**作用**: 前端开发时请求 `/api/v1/...` 自动代理到后端 `http://localhost:8000/api/v1/...`，避免跨域问题。

### 1.3 API 请求层调整

确保 `web/src/services/api.ts` 中 `baseURL` 不包含域名 (使用相对路径通过 Vite 代理)：

```typescript
const apiClient = axios.create({
  baseURL: '/api/v1',  // 相对路径，走 Vite 代理
  timeout: 30000,
});
```

**验收**:
- [ ] `pnpm dev` 启动后，DevTools Network 标签中请求走真实后端
- [ ] CORS 不再报错（通过 Vite 代理转发）
- [ ] 所有页面数据从真实后端加载

---

## Step 2: 完整业务流程走查

### 2.1 核心流程: DRG 入组 (最重要)

```
启动系统
  │
  ▼
初始化演示数据
  POST /api/v1/system/demo/init
  → 导入规则 + 样例病历
  │
  ▼
打开 DRG 入组页面 (/drg)
  │
  ▼
选择规则版本 (DRG 2.0 演示规则)
  │
  ▼
输入课程示例病历:
  主诊断: A01.002+G01* (伤寒性脑膜炎)
  次要诊断: J96.0 (急性呼吸衰竭)
  主要手术: 38.1000x002 (动脉内膜剥脱术)
  │
  ▼
点击"开始入组"
  POST /api/v1/grouping/execute {caseId, ruleVersionId}
  → taskId
  │
  ▼
轮询入组结果
  GET /api/v1/grouping/results/{taskId}
  → 完成后显示:
    MDC: MDCB (神经系统疾病及功能障碍)
    ADRG: BB1 (神经系统复合手术)
    DRG: BB11 (神经系统复合手术，伴严重合并症或并发症)
    证据链 5 步完整显示
```

**验收**:
- [ ] 课程示例输入 → 输出 `BB11`，时间戳 < 5 秒
- [ ] 证据链 5 步全部显示，每步有匹配的编码和规则
- [ ] 候选规则列表显示 `BB11 (命中)` 和 `BB15 (未命中)`
- [ ] 解释文本包含"主诊断"、"手术"、"MCC"、"排除表"等关键词

### 2.2 异常场景: 无法入组

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| 主诊断缺失 | 不填主诊断 | 校验失败，提示"主诊断编码缺失" |
| 编码无法匹配 MDC | 主诊断: `Z99.9` (无意义编码) | 显示 `is_grouped=False`, `stage="mdc_matching"`, 建议"检查诊断编码" |
| 编码格式错误 | 主诊断: `INVALID_CODE` | 校验失败，高亮非法编码 |

**验收**:
- [ ] 每个异常场景显示明确的错误类型和修正建议
- [ ] 异常任务被保存到数据库 (任务状态 `failed`)
- [ ] 前端错误提示使用 antd `Alert` 组件，非浏览器弹窗

### 2.3 规则管理流程

```
导入规则文件
  POST /api/v1/rules/import (multipart/form-data)
  → 文件上传 → 后台解析 → 返回 versionId
  │
  ▼
查看规则版本列表
  GET /api/v1/rules/versions
  → 显示所有版本，当前活跃版本有绿色标记
  │
  ▼
查看版本详情
  GET /api/v1/rules/versions/{versionId}
  → Tab 切换 MDC/ADRG/DRG/MCC/CC 列表
  │
  ▼
激活版本
  POST /api/v1/rules/versions/{versionId}/activate
  → 原活跃版本变为非活跃，新版本激活
  │
  ▼
删除旧版本
  DELETE /api/v1/rules/versions/{versionId}
  → 活跃版本不可删除，提示先激活其他版本
```

**验收**:
- [ ] 规则文件上传成功，解析结果可在详情页查看
- [ ] 版本激活后，入组页面自动切换到新版本
- [ ] 删除非活跃版本成功，活跃版本删除被阻止

### 2.4 文档自动生成流程

```
DRG 入组完成后
  │
  ▼
点击"生成文档"
  POST /api/v1/documents/generate
  {docType: "requirements", title: "...", context: {...}}
  → docTaskId
  │
  ▼
异步生成 (Celery)
  → 上下文收集 → LLM 生成 → Markdown 格式化
  │
  ▼
轮询文档任务状态
  GET /api/v1/documents/tasks/{docTaskId}
  → status: completed → docId
  │
  ▼
预览文档
  GET /api/v1/documents/{docId}/preview
  → 显示 Markdown 渲染内容
  │
  ▼
编辑文档
  PUT /api/v1/documents/{docId}
  {content: "修改后的内容..."}
  │
  ▼
提交文档
  POST /api/v1/documents/{docId}/submit
  → 状态变为 "submitted"，生成提交记录
  │
  ▼
查看文档列表
  GET /api/v1/documents?type=requirements
  → 列表中显示新文档
```

**验收**:
- [ ] Celery worker 正常接收和执行文档生成任务
- [ ] 文档生成完成后，前端自动刷新显示
- [ ] 文档可预览、编辑、提交、下载
- [ ] 提交记录包含提交时间、版本号、文件路径
- [ ] 文档版本历史记录历次修改

### 2.5 测试用例生成流程

```
规则已导入，有病历样例
  │
  ▼
打开测试用例页面 (/tests)
  │
  ▼
配置生成参数:
  规则版本: DRG 2.0 演示规则
  场景: 正常 + 边界 + 异常
  数量: 30
  │
  ▼
点击"生成用例"
  POST /api/v1/testcases/generate
  → testTaskId
  │
  ▼
异步生成 (Celery)
  → 规则分析 → 场景构造 → LLM 生成用例
  │
  ▼
查看生成的测试用例
  GET /api/v1/testcases?scenarioType=normal
  → 列表: TC-D-001, TC-D-003, ...
  │
  ▼
执行单个测试用例
  → 用输入的病历调用 POST /api/v1/grouping/execute
  → 比对实际结果 vs 预期结果
  │
  ▼
导出测试用例
  POST /api/v1/testcases/export
  {testCaseIds: [...], format: "excel"}
  → 下载 xlsx 文件
  │
  ▼
提交到文档系统
  POST /api/v1/testcases/submit-to-documents
  → 生成测试文档
```

**验收**:
- [ ] 正常场景用例 ≥ 8 条
- [ ] 边界场景用例 ≥ 8 条
- [ ] 异常场景用例 ≥ 5 条
- [ ] 执行测试用例后，实际结果与预期结果对比正确
- [ ] 导出 Excel 文件包含所有字段
- [ ] 提交到文档系统后，文档列表中可见测试文档

---

## Step 3: 端到端 (E2E) 测试

### 3.1 Playwright E2E 测试

安装 Playwright:

```bash
cd web
pnpm add -D @playwright/test
npx playwright install chromium
```

测试文件: `web/e2e/`

```typescript
// web/e2e/grouping.spec.ts
import { test, expect } from '@playwright/test';

test.describe('DRG Grouping E2E', () => {
  test('课程示例: 伤寒性脑膜炎 → BB11', async ({ page }) => {
    await page.goto('http://localhost:5173/drg');
    
    // 等待页面加载
    await page.waitForSelector('.rule-version-selector');
    
    // 选择规则版本
    await page.click('.rule-version-selector');
    await page.click('text=DRG 2.0 演示规则');
    
    // 输入病历
    await page.fill('textarea[name="rawText"]', 
      '主诊断：A01.002+G01* 伤寒性脑膜炎\n' +
      '次要诊断：J96.0 急性呼吸衰竭\n' +
      '主要手术：38.1000x002 动脉内膜剥脱术'
    );
    
    // 点击开始入组
    await page.click('button:has-text("开始入组")');
    
    // 等待结果
    await page.waitForSelector('.grouping-result-panel', { timeout: 10000 });
    
    // 验证结果
    await expect(page.locator('.drg-code')).toHaveText('BB11');
    await expect(page.locator('.mdc-code')).toHaveText('MDCB');
    
    // 验证证据链
    const evidenceSteps = page.locator('.ant-timeline-item');
    await expect(evidenceSteps).toHaveCount(5);
  });
  
  test('主诊断缺失 → 显示错误', async ({ page }) => {
    await page.goto('http://localhost:5173/drg');
    
    // 不填写主诊断，直接点击开始入组
    await page.click('button:has-text("开始入组")');
    
    // 验证错误提示
    await expect(page.locator('.ant-alert-error')).toBeVisible();
    await expect(page.locator('.ant-alert-error')).toContainText('主诊断');
  });
});
```

### 3.2 E2E 测试场景清单

| 编号 | 测试场景 | 输入/预期 | 类型 |
|------|---------|----------|------|
| E2E-01 | 课程示例入组 | A01.002+G01* + J96.0 + 38.1000x002 → BB11 (MCC) | 核心流程 |
| E2E-02 | example Case1 入组 | C16.301 + [K66.002,...] + 43.7x03 → GB29 (CC) | 核心流程 |
| E2E-03 | example Case2 入组 | J86.000x013 + [K66.002,...] + 34.8200x002 → EC29 (CC) | 核心流程 |
| E2E-04 | example Case3 入组 | K83.105 + [K83.109,...] + 51.6303 → HC15 (NONE) | 核心流程 |
| E2E-05 | 结构化病历入组 | 表单填写 → 入组成功 | 核心流程 |
| E2E-06 | 无编码病历入组 (nocode) | 仅有疾病名称无编码 → warning 提示 | 边界场景 |
| E2E-07 | 主诊断缺失 → 错误提示 | 不填主诊断 → 校验失败 | 异常场景 |
| E2E-08 | 编码非法 → 错误提示 | INVALID_CODE → 格式错误 | 异常场景 |
| E2E-09 | 无法匹配 MDC → 未入组说明 | Z99.9 → 无匹配 | 异常场景 |
| E2E-10 | 规则文件上传 → 解析 → 激活 | 上传 Excel → 版本列表更新 | 规则管理 |
| E2E-11 | 生成需求分析文档 → 提交 | POST generate → 预览 → submit | 文档系统 |
| E2E-12 | 生成测试用例 → 导出 Excel | POST generate → 导出 xlsx | 测试用例 |
| E2E-13 | 任务中心查看任务详情 | 点击任务 → 步骤列表 + 耗时 | 任务管理 |
| E2E-14 | 系统配置修改 → 健康检查 | PUT config + GET health | 系统管理 |

**验收**:
- [ ] `npx playwright test` 14 个 E2E 场景全部通过
- [ ] Playwright HTML report 可正常查看
- [ ] Playwright trace 可回放失败的操作步骤

---

## Step 4: 性能测试

### 4.1 后端性能指标

| 指标 | 目标 | 测试方法 |
|------|------|----------|
| 单病历入组响应时间 | < 5 秒 (NFR-05) | `time curl -X POST /api/v1/grouping/execute` |
| 规则引擎入组耗时 | < 200ms (不含 LLM 解释) | GroupingEngine.group() 计时 |
| 病历解析 (LLM) | < 10 秒 | LLM call 计时 |
| 解释生成 (LLM) | < 5 秒 | LLM call 计时 |
| API 响应时间 (P95) | < 500ms (不含 LLM 调用) | Apache Bench / wrk |

### 4.2 性能测试脚本

```bash
# 入组 API 性能
ab -n 50 -c 5 -p grouping_request.json -T application/json \
   http://localhost:8000/api/v1/grouping/execute

# 病历列表 API
ab -n 100 -c 10 http://localhost:8000/api/v1/cases
```

### 4.3 前端性能指标

| 指标 | 目标 | 测试方法 |
|------|------|----------|
| 首屏加载时间 | < 3 秒 | Chrome DevTools Lighthouse |
| 页面切换延迟 | < 300ms | React Profiler |
| 输入响应延迟 | < 100ms | 手动测试 |
| Bundle 大小 | < 500KB (gzipped) | `pnpm build` 产物分析 |

**验收**:
- [ ] 课程示例入组全流程 (含 LLM) < 15 秒
- [ ] 规则引擎纯计算 < 200ms
- [ ] 前端首屏 Lighthouse score > 80
- [ ] 无内存泄漏 (DevTools Memory Profiler)

---

## Step 5: 错误处理与健壮性

### 5.1 后端错误场景覆盖

| 场景 | 预期行为 |
|------|----------|
| PostgreSQL 容器停止 | 健康检查返回 `database: disconnected`，API 返回 500 |
| Redis 容器停止 | Celery 任务失败但 API 仍可用 |
| LLM API 不可达 | 3 次重试 → 返回降级内容或 503 错误 |
| 规则文件格式错误 | 导入失败，返回 parse_errors，不覆盖已有版本 |
| 并发入组请求 | 每个请求独立处理，不相互影响 |
| 超大文件上传 | 返回 413 或限制提示 |

### 5.2 前端错误场景覆盖

| 场景 | 预期行为 |
|------|----------|
| 后端 API 500 | 显示 antd `message.error("服务器错误")` |
| 网络断开 | 显示 antd `message.error("网络连接失败")` |
| 请求超时 | 显示 antd `message.error("请求超时")` |
| 空数据 | 显示 `EmptyState` 组件 ("暂无数据") |
| 长文本溢出 | 使用 Ant Design `Typography.Paragraph` ellipsis |

### 5.3 全局错误边界

```tsx
// src/components/Common/ErrorFallback.tsx
<ErrorBoundary fallback={<ErrorFallback />}>
  <App />
</ErrorBoundary>
```

**验收**:
- [ ] Docker 服务手动停止后，健康检查显示 disconnected
- [ ] LLM API 断连后，文档生成返回模板化降级内容
- [ ] 前端页面任意组件报错不导致白屏

---

## Step 6: 跨浏览器验证

### 6.1 目标浏览器

| 浏览器 | 版本 | 平台 |
|--------|------|------|
| Chrome | ≥ 120 | macOS / Windows |
| Safari | ≥ 17 | macOS |
| Edge | ≥ 120 | Windows |

### 6.2 验证要点

- [ ] 页面布局无错位 (Flexbox/Grid 兼容)
- [ ] Ant Design 组件渲染一致
- [ ] 字体渲染一致 (系统默认字体)
- [ ] 表单交互一致 (focus/blur/enter)
- [ ] 滚动条样式正常

**验收**:
- [ ] Chrome 全部页面正常
- [ ] Safari 全部页面正常

---

## Step 7: 数据库完整性验证

### 7.1 数据一致性检查

- 入组任务 (`GroupingTask`) 必须关联有效的 `PatientCase` 和 `RuleVersion`
- 每个 `GroupingTask` 有且仅有一个 `GroupingResult` (1:1 关系)
- 文档 (`Document`) 必须有关联的 `DocumentTask` (来源记录)
- 测试用例 (`TestCase`) 必须有关联的 `TestTask` (来源记录)
- 删除 `RuleVersion` 时检查是否有 `GroupingTask` 引用，如有则阻止删除

### 7.2 数据清理

- 测试完成后，提供清理脚本删除测试数据
- Demo 数据初始化幂等 (重复调用不创建重复数据)

**验收**:
- [ ] 外键约束全部生效
- [ ] 删除被引用的规则版本时，API 返回 409
- [ ] `POST /api/v1/system/demo/init` 重复调用不报错

---

## Step 8: 文档与最终检查

### 8.1 交付文档更新

| 文档 | 说明 |
|------|------|
| `README.md` | 更新启动命令、环境要求、常见问题 |
| `plans/01_tech_stack.md` | 已更新为 PostgreSQL / 版本号 |
| `plans/02_architecture.md` | 已更新基础设施层 |
| `plans/development_phases/phase1_backend.md` | 后端开发任务清单 |
| `plans/development_phases/phase2_frontend.md` | 前端开发任务清单 |
| `plans/development_phases/phase3_integration.md` | 本文档 |

### 8.2 代码仓库检查

- [ ] `.gitignore` 正确忽略 `.venv/`, `node_modules/`, `.env`, `dist/`, `__pycache__/`
- [ ] `package.json` 锁定 pnpm 版本 (`packageManager`)
- [ ] `.node-version` 和 `.mise.toml` 锁定运行时版本
- [ ] 无 API Key 或密码提交 (`.env` 在 gitignore 中)
- [ ] `requirements.txt` 和 `uv.lock` (如有) 提交到仓库
- [ ] 代码注释覆盖关键逻辑 (规则引擎、智能体编排)

### 8.3 演示环境启动检查

```bash
# 一键启动脚本 (start.sh / start.ps1)
docker compose up -d
cd server && source ../.venv/bin/activate && uvicorn main:app --reload &
celery -A app.tasks worker --loglevel=info &
cd ../web && pnpm dev &

# 等待服务就绪
curl http://localhost:8000/api/v1/system/health

# 初始化演示数据
curl -X POST http://localhost:8000/api/v1/system/demo/init

echo "系统已就绪: http://localhost:5173"
```

**验收**:
- [ ] 从 `git clone` 到系统可运行 ≤ 10 分钟
- [ ] 一键启动脚本正常工作
- [ ] 演示数据初始化后立即可用

---

## Phase 3 最终验收清单

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 1 | 前后端 API 连接正常 | 前端无 MSW，数据来自后端 |
| 2 | 4 个示例入组全链路通过 | A01.002 + C16.301 + J86.000x013 + K83.105 全部正确 |
| 3 | 文档自动生成 → 编辑 → 提交 | Markdown 预览正确，提交记录可查 |
| 4 | 测试用例生成 → 执行 → 导出 | Excel 导出完整，执行结果对比正确 |
| 5 | 规则文件导入 → 激活 → 删除 | 版本管理全流程正常 |
| 6 | 异常场景处理正确 | 每种异常有明确错误提示，nocode 场景有 warning |
| 7 | E2E 测试全部通过 | `npx playwright test` 14/14 通过 |
| 8 | 后端性能达标 | 规则引擎 < 200ms，全流程 < 15s |
| 9 | 前端性能达标 | Lighthouse > 80，首屏 < 3s |
| 10 | Chrome + Safari 渲染一致 | 手动验证 |
| 11 | Docker 服务健壮性 | 手动停止 PostgreSQL → 健康检查报 disconnected |
| 12 | 数据库外键完整性 | 删被引用资源 → 409 错误 |
| 13 | 代码仓库整洁 | 无 secret 泄露，注释完整 |
| 14 | 一键启动可用 | `start.sh` → 全部服务就绪 |

---

## 后续改进建议

1. **CI/CD 流水线**: 添加 GitHub Actions，自动运行 lint + test + build
2. **API 版本化**: 当前 v1，未来可扩展 v2 接口，保持向后兼容
3. **SSE/WebSocket 实时推送**: 替代前端轮询，实时推送任务状态变化
4. **用户认证**: 添加 JWT 登录，实现角色权限隔离
5. **生产环境部署**: Docker Compose → Kubernetes，添加 Nginx 反向代理
6. **监控告警**: Prometheus + Grafana 监控 API 响应时间和错误率
7. **DRG 规则热加载**: 运行时重新加载规则文件而不重启服务
8. **批量入组性能优化**: 使用 asyncio.gather 并行执行多个入组任务
9. **文档国际化**: 支持中英文文档生成
10. **审计日志持久化**: 将操作日志写入数据库，支持长期存储和检索

---

## 附录: 三阶段依赖关系图

```
Phase 1 (后端)
├── Step 1-2: 数据库 + 规则引擎 ──────────┐
├── Step 3-4: LLM + Schemas               │
├── Step 5-6: Agent + Services            │
├── Step 7-10: API + Celery + Demo        │
└── Step 11: 后端测试                      │
                                          │
          ┌───────────────────────────────┘
          │ (API 接口定义 stable)
          ▼
Phase 2 (前端)
├── Step 1-2: 脚手架 + 基础设施 ──────────┐
├── Step 3-7: 7 个页面开发                │
├── Step 8-9: 状态管理 + 类型定义          │
└── Step 10-11: 前端测试 + 代码质量        │
                                          │
          ┌───────────────────────────────┘
          │ (前端代码完成)
          ▼
Phase 3 (集成)
├── Step 1: 关闭 MSW，连接真实 API ────────┐
├── Step 2: 完整业务流程走查               │
├── Step 3: E2E 测试 (Playwright)          │
├── Step 4-6: 性能 + 错误处理 + 跨浏览器   │
└── Step 7-8: 数据库完整性 + 最终检查      │
```

**开发建议**: Phase 2 和 Phase 1 可以部分并行开发，但 Phase 2 的页面开发 (Step 3-7) 之前必须确保 Phase 1 的 API 接口定义 (Step 7) 已完成。MSW mock 使得前端可以在 API 尚未完全实现时先行开发。
