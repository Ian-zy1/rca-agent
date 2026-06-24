# D2 前置定调（v1.0 · 2026-06-24）

> PLAN.md v2.1 第 32-36 行的三条定调正式落字。这三条决定 D3+ 代码形态，必须在 D2 末确认。

---

## 1. Function Calling 用途

**决策**：FC 用于「节点内动态生成 PromQL/LogQL 查询」，**不用于节点间路由**。

**含义**：
- 「指标分析」节点内部：LLM 拿到 service topology_context → 用 FC 决定查哪几条 PromQL（如场景 1 选 `slow_queries_rate` + `row_lock_waits_rate` 而非 `threads_connected`）
- 「日志分析」节点内部：LLM 用 FC 生成 LogQL（如 `{instance="hw-agent:19213"} |= "OOM"`）
- **节点间走哪条边由 LangGraph StateGraph 固定边决定**，不让 LLM 自由选

**理由**：
- 8 节点固定图自洽，路由权交给 LLM 会引入不可控性
- D1 已验证：DeepSeek-V3 自由 FC 时对「频繁重启」先查 CPU 而非内存（语义偏移），证明 LLM 路由不可靠
- 节点内 FC 粒度小、范围明确（只选 PromQL），可控性高

**对后续的影响**：
- **D3**：FC 工具集 schema 只暴露 `query_prometheus(promql)` 一个工具，不暴露 `route_to_node()` 之类
- **D5**：8 节点用 `add_edge` 固定连接，不用 `add_conditional_edges` 让 LLM 决定走向（除拓扑关联后的并行扇出，那是固定扇出）
- **D5**：节点内用 `model.bind_tools([query_prometheus])` + agent loop，不是顶层 `create_react_agent`

**验证**：
- grep `add_conditional_edges` 在 workflow/ 目录下出现次数：应为 0 或仅用于固定分支（如"指标够不够"的布尔判断，不让 LLM 决定）
- FC 工具集只有数据查询类，无路由类

---

## 2. 对话模式工作流

**决策**：对话入口 → **跳过告警接收/聚合** → 直接进拓扑关联 → 后续与告警模式同流。**不做意图识别节点**，**不做慢SQL定位专属节点**。

**含义**：
- 对话触发：用户问"为什么 X 慢" → 构造一个轻量 AlertEvent（trigger_mode=chat, user_query=原文, alert_event=None）→ 直接进节点3 拓扑关联
- 拓扑关联节点：从 user_query 关键词匹配 topology services（如"搜索慢" → es-heimdall），不依赖 alertname
- 不做"用户意图是查日志还是查指标"的 LLM 分类节点（多余）

**理由**：
- 与 PRD §3.3 一致："用户提问时，跳过步骤 1-2，直接从步骤 3 开始"
- 覆盖 demo 偏差（demo 里写了独立的"对话分类"节点，PRD 没要求）
- 意图识别增加节点数，对一周 MVP 是过度设计
- 慢SQL 定位本质就是日志分析节点的子任务（搜 `slow query` + `lock wait`），独立成节点浪费

**对后续的影响**：
- **D5**：StateGraph 有两个 START 边：
  - 告警入口 → 节点1 告警接收 → 节点2 聚合 → 节点3 拓扑
  - 对话入口 → 节点3 拓扑（跳过1/2）
- **D5**：拓扑关联节点要兼容两种输入：AlertEvent（告警）或 user_query 字符串（对话）
- **D6**：`POST /api/chat` 接口直接 invoke workflow from 节点3，不走节点1/2

**验证**：
- workflow/ 里节点1、节点2 不在对话路径上（grep `trigger_mode == "chat"` 应在路由代码中出现）
- 不存在名为 `intent_classification` 或 `chat_router` 的节点

---

## 3. 接口数量

**决策**：FastAPI 接口钉死 **4 个**：
- `POST /api/alerts` —— Alertmanager webhook 入口
- `POST /api/chat` —— 对话查询入口
- `GET  /api/reports/{event_id}` —— 查询单个 RCA 报告
- `GET  /api/health` —— 健康检查

**砍掉**（PRD §5 提过但 002 需求减过的）：
- ~~`GET /api/reports` 列表查询~~（演示不需要历史列表）
- ~~`GET /api/reports/{event_id}/trace` 单独的 trace 端点~~（trace 已嵌在 report.workflow_trace 里）

**理由**：
- 统一 PRD §5（6 个接口）与 002 需求（3 个）的口径
- 一周 MVP 时间紧，每砍一个接口省 30 分钟（含 OpenAPI 文档 + 测试 + 前端联调）
- 演示只需"触发 → 出报告"闭环，列表/独立 trace 是 nice-to-have

**对后续的影响**：
- **D6**：FastAPI app 注册路由 = 4 个，多一个都不写
- **D6**：前端 3 个页面够用（告警触发页 / 对话页 / 报告展示页），不做"历史报告列表"页
- **D6**：webhook 用 `curl` 模拟，不真接 Alertmanager

**验证**：
- grep `@app\.(post|get)` 在 api/ 目录下计数：应为 4
- 没有 `/api/reports`（不带 event_id）这种列表端点

---

## 状态

- [x] FC 用途定调
- [x] 对话工作流定调
- [x] 接口数量定调

> D3+ 代码必须遵守这三条。变更需重新评审（zy-xr）。
