# AI 应用 / Agent 开发知识图谱（ROADMAP）

> **本文是整个知识库的脊柱**：把 LLM/AI 应用/Agent 开发的必备能力组织成 9 层依赖图，每层标注「现有覆盖 vs 缺口」，并给出补文档的优先顺序。**以后生成新知识文档时，照这张图的缺口挑，不再无从下手。**
>
> 基于 2026.6 当前框架（roadmap.sh / DeepLearning.AI 课纲 / LangChain Academy / Anthropic+OpenAI 工程指南 / OWASP LLM Top 10 2026）。含 2025-2026 新增项，过期内容会随调研滚动更新。

## 怎么用这张图

1. **查覆盖**：每个主题标了 ✅已覆盖（哪个文件）/ ⚠️缺口
2. **补文档**：按文末「缺口优先级」顺序生成新文件
3. **学习路径**：按层从 L0 到 L8 顺序学；MUST 项优先
4. **时效维护**：标 🆕 的是 2025-2026 新增，重点核验

---

## L0 · 软件工程基础

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| Python 3.10+（async/类型注解/Pydantic v2）| ✅ | Pydantic v2 是事实标准 | ✅ 002/agent-dev |
| REST + async HTTP（requests/httpx/fastapi）| ✅ | | ✅ 002/agent-dev |
| JSON / JSON Schema | ✅ | MCP 强制 2020-12 | ✅ |
| Git / Docker / 密钥管理 | ✅ | | ✅ |
| ML/数学基础 | 选 | | ⚠️ 知识面缺口（AI 工程用预训练模型，不必深）|

## L1 · LLM 核心（模型交互）

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| Token / 上下文窗口 / 上下文腐烂（context rot）| ✅ | context rot 2025 新命名 | ✅ 002/llm-theory |
| 采样参数（temperature/top-p/top-k）| ✅ | | ✅ 002/llm-theory |
| 成本与延迟（$/1M、TTFT、tokens/sec）| ✅ | **推理 token 是新成本维度** | ✅ 002/llm-theory |
| 模型怎么工作（Transformer/KV-cache/训练）| ✅ | | ✅ 002/llm-theory |
| **推理模型**（o 系列/DeepSeek-R1/extended thinking）| ✅ | 🆕 **2025 最大变量**：测试时计算成可调参数 | ⚠️ **缺口（高优）** |
| 推理服务（vLLM/量化/batching）| 选 | | ⚠️ 缺口（选）|
| 微调（SFT/LoRA/DPO）| 选 | | ⚠️ 缺口（选）|

## L2 · Prompt 与上下文工程

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| System/user 角色 + Few-shot + CoT | ✅ | | ✅ 003/prompt-and-modeling |
| Prompt 模板化/版本化（当代码管）| ✅ | | ✅ 003/langchain-bridge |
| **结构化输出**（JSON Schema + `strict:true`）| ✅ | 🆕 取代 JSON Mode，成默认 | ✅ 002/agent-dev |
| **上下文工程**（curate 上下文窗口）| ✅ | 🆕 **Anthropic 2025.9 立的新学科** | ⚠️ **缺口（高优）** |
| 压缩（compaction，总结重启上下文）| ✅ | 🆕 Claude API 原生 | ⚠️ 缺口 |
| 工具结果清理 / 智能体记忆 | ✅ | 🆕 | ⚠️ 缺口 |
| Prompt 缓存 / DSPy 程序化优化 | 选 | 🆕 缓存是 2025 省钱大招 | ⚠️ 缺口（选）|

## L3 · 工具调用与 Function Calling

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| Function Calling（schema/tool_choice/strict）| ✅ | strict 模式推荐常开 | ✅ 002/agent-rag、003/langchain-bridge |
| 工具设计（窄工具/清晰契约/≤25K token 响应）| ✅ | | ⚠️ 缺口（设计准则）|
| Agent 循环（model→tool→model）| ✅ | | ✅ 003/langgraph-depth |
| **MCP（Model Context Protocol）**| ✅ | 🆕 **2026 标准**：Linux Foundation 治理，OpenAI/Anthropic/Google 全支持 | ⚠️ **缺口（高优，2026-07-28 新规范）** |
| MCP 原语（tools/resources/prompts/elicitation）| ✅ | 🆕 | ⚠️ 缺口 |
| MCP 传输（stdio / Streamable HTTP + OAuth 2.1）| ✅ | 🆕 2026 无状态模式支持 LB | ⚠️ 缺口 |
| 工具延迟加载（tool_search）| 选 | 🆕 | ⚠️ 缺口（选）|

## L4 · RAG（检索增强）

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| Embedding（MTEB 选型）| ✅ | Qwen3-Embedding 2025 登顶 | ✅ 002/agent-rag |
| Chunking 策略 | ✅ | | ✅ 002/agent-rag |
| 向量库（选一个：pgvector/Pinecone/Qdrant）| ✅ | "比四家的时代过了" | ✅ 002/agent-rag（ChromaDB）|
| **混合检索**（BM25 + 稠密）| ✅ | 🆕 已成默认，非进阶 | ⚠️ 缺口（深度）|
| Reranking（cross-encoder）| ✅ | | ✅ 002/agent-rag（提了）|
| **Contextual Retrieval**（Anthropic）| 选 | 🆕 切块前加上下文前缀 | ⚠️ 缺口（选）|
| Graph RAG / 多模态 RAG / Agentic RAG | 选 | | ⚠️ 缺口（选）|

## L5 · Agent 与编排（增长最快）

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| ReAct 模式 | ✅ | | ✅ 002/agent-rag |
| Agent 设计模式（反思/工具/规划/多智能体）| ✅ | | ✅ 002/agent-rag |
| **LangGraph 1.0**（state/node/edge/checkpoint）| ✅ | 🆕 **2025.10 GA**；create_react_agent 废弃→create_agent | ✅ 003/langgraph-depth |
| create_agent + middleware（LangChain 1.0）| ✅ | 🆕 | ✅ 003/langgraph-depth（提了）|
| State & memory（短期/长期）| ✅ | | ✅ 003/langgraph-depth |
| HITL（interrupt/approve）| ✅ | 2025 起是 middleware | ✅ 003/langgraph-depth |
| 持久化/恢复 + 流式 | ✅ | | ✅ 003/langgraph-depth |
| **子 Agent / 委托**（隔离上下文）| ✅ | 🆕 Anthropic 子 agent 模式 | ⚠️ 缺口 |
| 多 Agent 编排（CrewAI/AutoGen/supervisor）| 选 | "单 Agent 熟练前别上多 Agent 戏" | ⚠️ 缺口（选）|
| **A2A（Agent2Agent 协议）**| 选 | 🆕 Google/IBM；补 MCP（工具↔Agent 通信）| ⚠️ 缺口（选）|
| Deep Agents / 长时序 harness | 选 | 🆕 | ⚠️ 缺口（选）|
| 框架全景（OpenAI Agents SDK/Claude Agent SDK/Google ADK）| 选 | 🆕 识别原语即可，新框架=读文档 | ⚠️ 缺口（选）|

## L6 · 评估（2026 升级为独立学科）

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| 金标准数据集（25-50 例起步）| ✅ | | ✅ 003/agent-reliability-and-eval |
| LLM-as-judge（+ 校准/去偏）| ✅ | 季度对人校准，Pearson>0.8 | ✅ 003/agent-reliability-and-eval |
| 回归测试（漂移检测/CI 门）| ✅ | | ✅ 003/agent-reliability-and-eval |
| RAG eval（RAGAS：faithfulness/relevancy/precision/recall）| ✅ | 分离检索器 vs 生成器错误 | ⚠️ 缺口（RAGAS 四指标）|
| **Agent eval**（任务完成/工具选择/trajectory/stepwise）| ✅ | 🆕 错误会跨步累积，需 trace 级 | ⚠️ 缺口（trajectory）|
| Trace 驱动（LangSmith/Langfuse/Phoenix）| ✅ | | ✅ 003/agent-reliability-and-eval（提了）|
| 配对/竞技场 eval；随机回归；在线 eval | 选 | 🆕 | ⚠️ 缺口（选）|

## L7 · 安全与护栏（2026 升为一等公民）

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| **OWASP LLM Top 10（v2025）**| ✅ | 🆕 加 System Prompt Leakage；扩 Excessive Agency | ⚠️ **缺口（最大缺口）** |
| **Prompt 注入**（直接 + 间接，间接更危险）| ✅ | 🆕 2026：上下文池/记忆/Agent 执行放大爆炸半径 | ⚠️ **缺口** |
| 纵深防御（假设模型会听恶意指令；限制爆炸半径）| ✅ | "prompt 注入目前基本无法完全防" | ⚠️ 缺口 |
| 最小权限工具设计 | ✅ | | ⚠️ 缺口 |
| 不可逆动作的 HITL | ✅ | | ✅ 003/langgraph-depth（HITL）|
| 护栏（NeMo Guardrails/Guardrails AI/Llama Guard）| ✅ | | ⚠️ 缺口 |
| 双 LLM 模式（特权+隔离）| 选 | Simon Willison | ⚠️ 缺口（选）|
| MCP 安全（OAuth 2.1/工具描述审计/签名验证）| ✅ | 🆕 | ⚠️ 缺口 |

## L8 · 生产 / 可观测 / 领域

### L8a · 生产与可观测（LLMOps）

| 主题 | MUST | 🆕 | 现有覆盖 |
|---|---|---|---|
| 部署（FastAPI + Docker + 云）| ✅ | | ✅ 002/agent-dev |
| **OpenTelemetry GenAI 语义约定**| ✅ | 🆕 **2026 可观测标准**：厂商可移植 | ⚠️ **缺口（高优）** |
| OTel GenAI 属性（gen_ai.usage.* 等）| ✅ | 🆕 | ⚠️ 缺口 |
| OTel MCP/Agent span（跨服务上下文传播）| ✅ | 🆕 v1.39 引入 | ⚠️ 缺口 |
| 稳定性 opt-in（`OTEL_SEMCONV_STABILITY_OPT_IN`）| ✅ | 🆕 规范仍 Development，需显式 pin | ⚠️ 缺口 |
| 成本归因（每成功任务/每客户）| ✅ | | ⚠️ 缺口 |
| 可靠性（超时/重试/幂等/最大迭代）| ✅ | | ✅ 003/agent-reliability-and-eval |
| 金丝雀/A-B（prompt/retrieval）| 选 | | ⚠️ 缺口（选）|

### L8b · 领域（RCA / AIOps）

| 主题 | MUST | 现有覆盖 |
|---|---|---|
| 可观测性地基（三支柱/SLI-SLO/四黄金信号/RED-USE）| ✅ | ✅ 003/observability |
| 故障模式库（IaaS/PaaS/SaaS 指标→根因）| ✅ | ✅ 003/observability |
| RCA 方法论 + AIOps（5 能力/异常检测/关联去噪）| ✅ | ✅ 003/rca-methodology-and-aiops |
| PromQL/MetricsQL（真实后端）| ✅ | ✅ 003/promql-for-rca |
| 领域评估 rubric | ✅ | ✅ 003/agent-reliability-and-eval |

---

## 学习顺序

**1 周 MVP 必备（不可妥协）**：L0 全 → L1 token/上下文/成本 → L2 system/few-shot/结构化输出 → L3 FC + 基础 MCP → L4 一个向量库+embedding+chunk → L5 LangGraph 1.0 create_agent + 工具循环 + HITL → L6 一个金标准集 + LLM-judge → L8a FastAPI 部署 + tracing。

**1 月可信生产再加**：L1 推理模型 + 推理 token 预算 → L2 上下文工程（压缩+记忆）→ L4 混合检索+rerank+RAGAS → L5 子 agent+持久化+流式 → L6 trajectory eval+回归 CI → **L7 OWASP+间接注入+护栏+最小权限** → L8a OTel GenAI + 成本归因。

**专项深挖（按需）**：微调、vLLM 自托管、多 Agent、A2A、Graph RAG、随机回归、双 LLM 安全、Deep Agents。

---

## 🎯 缺口优先级（下次补文档照这个顺序，不再无从下手）

| 优先级 | 缺口 | 归属层 | 为什么先补 |
|---|---|---|---|
| **P0** | **L7 安全与护栏**（OWASP Top 10/间接注入/excessive agency/护栏）| L7 | **最大缺口 + 生产必备 + 考试可能考** |
| **P0** | **L1 推理模型**（o/R1/extended thinking/测试时计算/推理 token 成本）| L1 | 2025 最大变量，当前完全没讲 |
| **P1** | **L2 上下文工程**（压缩/清理/记忆）| L2 | 2025 新学科，长时序 Agent 必备 |
| **P1** | **L8a OTel GenAI 语义约定** | L8a | 2026 可观测标准，厂商可移植 |
| **P1** | **L3 MCP 2026-07-28 深度**（Tasks/无状态 HTTP/OAuth 2.1）| L3 | 现有 MCP 浅，规范已大更新 |
| **P2** | L6 RAGAS 四指标 + Agent trajectory eval | L6 | 评估精度，已有基础 |
| **P2** | L5 子 Agent + 多 Agent 编排 + A2A | L5 | 单 Agent 熟后扩 |
| **P2** | L4 Contextual Retrieval + 混合检索深度 | L4 | RAG 精度 |
| **P3** | L1 微调 / vLLM 自托管 | L1 | 按需深挖 |

---

## 🆕 2025-2026 必须纳入的 11 项（2024 路线图会漏）

1. 推理模型 + 测试时计算（o1→DeepSeek-R1→o3/Claude thinking）
2. MCP 标准化（Linux Foundation，2026-07-28 规范）
3. 结构化输出取代 JSON Mode（`strict:true` 默认）
4. 上下文工程成独立学科（压缩/清理/记忆）
5. Agent 评估成正式学科（trajectory/stochastic 回归）
6. OpenTelemetry GenAI 语义约定
7. LangChain/LangGraph 1.0（create_agent + middleware）
8. OWASP LLM Top 10 v2025 + 2026 更新（"prompt 注入基本无法完全防"）
9. A2A 协议（补 MCP，Agent 间通信）
10. Agent SDK 成类别（OpenAI/Claude/Google ADK）
11. Deep Agents / 长时序 harness

**2026 共识建议跳过的 4 类**（[Medium 路线图](https://medium.com/data-science-collective/the-agentic-ai-engineer-roadmap-for-2026-skills-stack-and-order-fc1dfa17948d)）：旧 LangChain AgentExecutor 模式、向量库四家对比、前 LLM 的 NLP 流水线、单 Agent 没熟练就上多 Agent 戏。

---

## 权威路线图源（本文据此合成）

- [roadmap.sh/ai-engineer](https://roadmap.sh/ai-engineer) — 社区图谱标杆
- [DeepLearning.AI 课程](https://www.deeplearning.ai/courses)（123 门；Agents 42/RAG 31/LLMOps 27/Eval 20）
- [LangChain Academy](https://academy.langchain.com/)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic — Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/agents/)
- [MCP 规范](https://modelcontextprotocol.io/specification/2025-11-25/index)
- [OTel GenAI 语义约定](https://github.com/open-telemetry/semantic-conventions-genai)
- [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/)

---

> **这张图是知识库的总目录。** 现有 17 个文件挂载其上；未来补文档按「缺口优先级」挑；时效维护重点核验 🆕 项。每补一个缺口，回来更新对应行的「现有覆盖」。
