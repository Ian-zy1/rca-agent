# LangGraph 深入：搭 8 节点 RCA 工作流

> D5 的核心。你 D1 写的 demo_agent 是**手写循环**，LangGraph 1.x 是**框架帮你管这个循环**——把工作流画成状态图，自动处理状态流转、持久化、人机协同。本文用 **2026 当前 API**（LangGraph 1.x，`create_react_agent` 已废弃）。

## 一个心智模型

**LangGraph = 把你的 agent 循环，画成一张"状态机图"。** 节点是函数（干一步活），边是流转（下一步去哪），状态是所有节点共享的"工作记忆"。你 D1 手写的 `for i in range(3)` 循环 + `messages.append`，LangGraph 用 State + reducer + edge 替你管。

---

## 模块 1：State —— 所有节点共享的工作记忆

State 是一个 `TypedDict`（或 Pydantic），定义"工作流里要流转什么"。**关键概念：reducer（归约器）**——控制多节点更新同一字段时怎么合并。

```python
from typing import Annotated, TypedDict
from operator import add
from pydantic import BaseModel

class Evidence(BaseModel):
    metric: str
    value: str
    interpretation: str

class RCAState(TypedDict):
    alert: dict                      # 原始告警，不变
    affected: list[str]              # 受影响资源
    evidence: Annotated[list[Evidence], add]   # ★ reducer=add：多节点追加，不覆盖
    root_cause: str
    report: dict
```

**为什么 reducer 关键**：没有 reducer，后一个节点写 evidence 会**覆盖**前一个；加了 `Annotated[..., add]`，指标节点和日志节点的证据会**累加**。RCA 的"多指标交叉验证"就靠这个。

> 你 D1 的 RCAReport.evidence 用 `list[dict]`——在 LangGraph 里它就是带 `add` reducer 的 State 字段。

## 模块 2：Node —— 一步活

节点就是个函数：**输入 State，返回要更新的部分**（不用返回全量，LangGraph 按 reducer 合并）。

```python
def topology_node(state: RCAState) -> dict:
    alert = state["alert"]
    affected = lookup_topology(alert["instance"])   # 查 topology.yaml
    return {"affected": affected}                    # 只返回更新

def metrics_node(state: RCAState) -> dict:
    evs = query_metrics_for(state["affected"])      # FC 查 Prom
    return {"evidence": evs}                         # 累加进 evidence
```

> 注意：节点**只返回 partial 更新**。这就是你 D1 学的"模型只下工单、你执行"的延伸——节点是执行单元，返回结果让框架合并。

## 模块 3：Edge —— 流转 + 条件分支

```python
from langgraph.graph import StateGraph, START, END

graph = StateGraph(RCAState)
graph.add_node("topology", topology_node)
graph.add_node("metrics", metrics_node)
graph.add_node("logs", logs_node)
graph.add_node("verdict", verdict_node)

graph.add_edge(START, "topology")
graph.add_edge("topology", "metrics")          # 固定边：拓扑→指标

def route_after_metrics(state: RCAState) -> str:   # ★ 条件分支
    if len(state["evidence"]) < 2:
        return "logs"      # 证据不够，再去查日志
    return "verdict"       # 够了，直接推断
graph.add_conditional_edges("metrics", route_after_metrics)

graph.add_edge("logs", "verdict")
graph.add_edge("verdict", END)
```

**条件分支**是 RCA 的核心——"证据够不够 → 出报告 / 再查"，你 PLAN.md 里"并行 vs 条件分支"的定调就在这里落地（选条件分支）。

## 模块 4：compile —— 图必须编译才能跑

```python
app = graph.compile(checkpointer=..., interrupt_before=["verdict"])
```

`compile()` 返回的 `CompiledStateGraph` 是个 Runnable（有 `invoke`/`stream`/`ainvoke`）。**checkpointer 和 HITL 开关在这里配。** 注意：StateGraph 本身是 builder，**不能直接 invoke**，必须先 compile。

## 模块 5：Checkpointing —— 持久化（生产必备）

每个节点跑完，checkpointer 把 State 存快照。**崩了/中断了，能从最后一个 checkpoint 恢复，不重跑已完成节点。**

```python
from langgraph.checkpoint.memory import InMemorySaver
app = graph.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "incident-001"}}
result = app.invoke(inputs, config)
```

`thread_id` 隔离不同事件流（一个 incident 一个 thread）。Demo 用 `InMemorySaver`；生产用 `SqliteSaver`/`PostgresSaver`。

## 模块 6：Human-in-the-loop —— 人工审核（评委爱看）

RCA agent 提了处置建议后，**先让人确认再执行**（不能自动 kill 进程/扩容）：

```python
from langgraph.types import interrupt, Command

def action_node(state: RCAState) -> dict:
    proposal = state["report"]["suggestions"]
    approved = interrupt({"proposal": proposal, "msg": "确认执行？"})  # ★ 暂停
    if approved:
        execute(proposal)
    return {"status": "approved" if approved else "cancelled"}
```

`interrupt()` 会**暂停整个图**，把 proposal 抛给调用方；前端用户点确认后，`app.invoke(Command(resume=True), config)` 继续跑。这是 2025+ 推荐的 HITL 方式（取代旧的 `interrupt_before`）。

## 模块 7：把 D1 的真工具接进图

你 D1 写的 `query_prometheus()` 真工具，在 LangGraph 里怎么用？**用 ToolNode + bind_tools**：

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def query_prometheus(promql: str) -> str:
    """查 VictoriaMetrics 指标，输入 PromQL"""
    return do_real_query(promql)

llm_with_tools = llm.bind_tools([query_prometheus])
tool_node = ToolNode([query_prometheus], handle_tool_errors=True)
# graph 里：metrics_node 调 llm_with_tools → tool_node 执行 → 结果回 State
```

`ToolNode` 的 `handle_tool_errors=True` 给你免费的工具错误恢复（见 003 reliability 文档）。

---

## ⚠️ 2026 当前 API 注意（避坑）

| 旧（0.x，已废弃）| 新（1.x，2026）|
|---|---|
| `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| `interrupt_before`/`interrupt_after` | 推荐 `interrupt()` + `Command(resume=)` |
| Python 3.9 | 要求 **Python 3.10+** |
| `langchain.chains.*` | 迁到 `langchain-classic` 包 |

LangGraph 核心（StateGraph/add_node/add_edge/compile/checkpointer）**1.0 没变**，你按上面写的就能跑。权威：[LangGraph 1.0 公告](https://www.langchain.com/blog/langchain-langgraph-1dot0)（2025-10）、[LangGraph 文档](https://docs.langchain.com/oss/python/langgraph/overview)

---

## 你的 8 节点 RCA 图（D5 蓝图）

```
START → 告警接收 → 告警聚合 → 拓扑关联 → 指标分析 ─┐
                                                  │(条件:证据够吗)
                                  ┌───────────────┘
                                  ▼
                              日志分析 → 案例检索 → 根因推断 → 报告生成 → (HITL) → END
```
- State 字段：`alert / affected / evidence(+) / hypotheses / root_cause / report`
- 条件分支：指标分析后"证据够不够 → 出报告 / 再查日志"
- HITL：报告生成后 interrupt，人确认建议再 END
- 对话模式：跳过"告警接收/聚合"，直接进拓扑关联

---

## 速记卡

| 要点 | 内容 |
|---|---|
| State | TypedDict；`Annotated[list, add]` 让证据累加不覆盖 |
| Node | 函数，输入 State，返回 partial 更新 |
| 条件分支 | `add_conditional_edges(src, router_fn, mapping)` |
| compile | builder 不能直接跑，必须 compile |
| checkpointer | 每节点存快照，崩溃可恢复；thread_id 隔离事件 |
| HITL | `interrupt()` + `Command(resume=)`，2025+ 推荐方式 |
| 8 节点 | 接收→聚合→拓扑→指标→(条件)→日志→案例→根因→报告→HITL |

### 比赛理论题预测

1. **LangGraph 和 LangChain Chain 区别？**（图 vs 链；支持循环/分支/持久化）
2. **State 的 reducer 是什么？为什么需要？**（控制多节点更新合并；没 reducer 会覆盖）
3. **条件分支怎么实现？**（add_conditional_edges + 路由函数）
4. **为什么需要 checkpoint？**（持久化 + 恢复 + HITL + 跨会话）
5. **HITL 在 RCA 里为什么重要？**（处置建议要人确认，不能自动执行高危操作）
6. **LangGraph 1.0 有什么变化？**（create_react_agent 废弃→create_agent；要求 Python 3.10+）

---

> **读完这个，D5 把 D1 的真工具（query_prometheus）接进 8 节点图，你知道每块怎么写了。** reducer/条件分支/checkpoint/HITL 是 D5 的四个关键点。
