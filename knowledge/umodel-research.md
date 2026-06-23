# UModel 调研留档

> **调研时间**: 2026-06-23
> **调研方式**: librarian（外部官方源）+ explore（本地知识库交叉核对）
> **结论**: UModel 真实、开源、技术上可部署，但**本周不部署**——它不等于"大模型部署"，且开源版是 plan-only 半成品。

---

## 1. UModel 是什么

**UModel（Unified Model）不是大模型，是"语义层/对象图"中间件。** 它不训练、不打包任何 LLM，而是把运维数据（实体/遥测/拓扑）建模成对象图，给**外部 LLM**（Qwen/Claude/Cursor）当上下文用。

架构位置：
```
存储(Prom/MySQL) → UModel 对象图 → MCP → 外部 LLM Agent
                                 ↑
                          UModel 在这层，不是 LLM
```

三大组件（与本地知识库描述一致）：
- **Ontology 建模**：EntitySet / TelemetryDataSet / Storage + 4 种关系
- **Runbook 机制**：5 类结构化诊断协议（Observation/Toolkit/Knowledge/Automation/Skill）
- **MCP 工具封装**：umodel-mcp server

## 2. 开源状态（确认真实）

- 仓库：`github.com/alibaba/UnifiedModel`（Apache-2.0，alibaba 官方 org）
- 首发：2026-05-06（很新）
- 学术背书：arXiv:2606.04799（*UModel: An Agent-Ready Observability Data Modeling Method at Scale*）
- 本地知识库标注 ~182 stars，"2026 战略级开源"

## 3. 部署可行性 + 关键 caveat

**技术上可部署**：`make quickstart`，Go+React+MCP，**纯 CPU 不用 GPU**，demo 约 15-30 分钟。依赖 Go 1.22+ / Node 22+ / pnpm 9 / Python 3.10。

**⚠️ 关键 caveat：开源版是 plan-only**（来自 `examples/service-localization/README.md` 原文）：
> "Plan-only. UModel open source returns query *plans*; an executor (e.g. umodel-assistant) runs them against real storage."

**翻译**：开源 UModel 会**生成**一条 PromQL，但**不会真去 Prometheus 执行**。要跑完整 RCA 闭环（真取数 → 真根因），得用阿里云商用版 `umodel-assistant`，或自己写执行器——那是 **1-3 天的坑**。

## 4. 「部署 UModel」≠ 比赛「大模型部署」

这是本次调研最重要的澄清：

| | 部署 UModel | 大模型部署（vLLM/Ollama） |
|---|---|---|
| 装什么 | Go 服务 + React UI + MCP | **模型权重 + 推理引擎** |
| 硬件 | CPU，任意笔记本 | 通常 GPU；Ollama 可 CPU 但慢 |
| 学的技能 | Ontology 建模、MCP 协议 | **量化、KV cache、显存、模型服务化** |
| 工具 | `go run` / `make` / `umctl` | **`vllm serve` / `ollama run`** |

**比赛 rubric 里的"大模型部署"几乎肯定指右列**（vLLM/Ollama 跑 Qwen/Llama）。部署 UModel 学的是左列，**裁判不考**。

## 5. 决策

**本周（6/23-6/30）不部署 UModel**，理由：
1. 开源版 plan-only，跑完整 RCA 闭环要 1-3 天自写执行器 → 23.5h 预算内是坑
2. 部署 UModel 不补"大模型部署"分（那是 vLLM/Ollama 的活）
3. 本地知识库自己警告过：`reference-alibaba-rca.md:231`「不要直接用 LangGraph + 阿里生态混搭」；且明确写「不要在一周内照搬」

**替代**：补"大模型部署"分用 **Ollama**（`ollama pull qwen2.5:7b`，30-60min，已纳入 PLAN.md v2.1 D6 周末可选）。

**UModel 留到赛后（7/1 后）精读**：`examples/incident-investigation/`（完整 RCA demo）+ `skills/umodel-rca/SKILL.md`。那时已有跑通的 LangGraph agent，对照 UModel 能看出"8 节点图 → 本体驱动 agent"的升级路径。

---

## 6. 借鉴应用：Runbook 节点思路（C 项，待 D5 落地）

> 不引入 UModel 框架，只借"结构化排查清单"这一个 idea。

### 问题
D1 demo 中，模型自由 FC 时对"order-service 频繁重启"先查了 CPU（`container_cpu_usage_seconds_total`），但真实根因是内存。**自由发挥会查错方向。**

### 思路：场景→指标 的诊断 checklist
在「指标分析」节点里，给模型一张**告警类型 → 该查指标族**的对照表，约束它在正确范围里用 FC 选具体 PromQL：

| 告警类型 | 该查的指标（写进 system prompt 或 FC tool description）|
|---|---|
| PodOOMKilled / 频繁重启 | `container_memory_usage_bytes`, `kube_pod_container_status_restarts_total` |
| 响应变慢 / 超时 | `http_request_duration_seconds`, db 连接池使用率 |
| NodeDown / 节点不可用 | `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, `kube_node_status_condition` |
| 5xx 错误率升 | `http_requests_total{status=~"5.."}` |

### 落地方式（D5 写 8 节点图时）
- 把这张表塞进「指标分析」节点的 system prompt（或 FC 工具的 description 字段）
- 模型仍用 FC **自主生成具体 PromQL**，但**被 checklist 约束在正确指标族内**
- 本质：用结构化先验知识治"自由发挥的错位"，零框架成本

### 不做什么
- ❌ 不引入 UModel 的 Ontology YAML / MCP server / 对象图——一周外的事
- ✅ 只借"结构化排查清单"这一个 idea，作为 prompt 工程的一部分

### 与定调的关系
这条思路与 PLAN.md v2.1 的「FC 用于节点内查询生成」定调**互补**：定调说"FC 在节点内用"，Runbook checklist 说"节点内 FC 被这张表约束"。二者一起，既保留模型自主生成 PromQL 的灵活性，又防止它查错方向。
