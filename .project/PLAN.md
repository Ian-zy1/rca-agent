# RCA Agent 统一执行计划（双轨日历）

> **版本**: v2.1（v2 + D1 实际进展回灌 / D2 减载 / 周末可选本地部署）
> **状态**: ✅ 已采纳 zy-xr 评审（见 `PLAN.xr.md`）；D1 超额完成，本版据实调整
> **创建**: 2026-06-23（周二）
> **预算**: 25h（工作日 1.5h × 6 + 周末 8h+ × 2）
> **截止**: 2026-06-30（周二）演示就绪

---

## 背景与动机

本项目存在两套互相冲突的 7 天日历：
- `.project/requirements/001-ai-knowledge-sprint.md`：Day0–7 学习计划
- `docs/RCA-Agent-PRD.md` §7：Day1–7 开发计划

两者占同一段日期但内容冲突（一个学一个写），且 PRD §7 时间预算虚高（31h vs 真实 23.5h），星期标注错位（6/22 实为周一非周日）。本文件**废止上述两套 Day 号**，作为唯一权威执行计划。

---

## 核心策略

**Interleaved 双轨**：每天先学概念、立刻用来建对应模块，避免「学完忘一半」。

**切片→扩展（周末核心手法，定位收紧）**：
- 周六上午建一个 **3 节点纵向切片 agent**（receive_alert → investigate → infer_and_report），**只验证 LangGraph 骨架（State + 边 + compile + invoke 能跑通）**，`investigate`/`infer_and_report` 用 3 行 Mock 占位，**禁止写真实推理逻辑**（扩展时这两节点会被拆掉重写）。
- 周六下午把切片的 `investigate` **拆成 5 个正式节点**（指标/日志/案例/拓扑/根因）+ 加条件分支，扩成 PRD §3.1 的 8 节点 StateGraph。
- 真正复用的只有：State 定义、receive_alert 节点、D1–D4 工具函数、图骨架。切片的价值是「证明管线通 + 拿到可跑骨架」，**不是保底方案**。

> ⚠️ 修正 v1 错误宣称：切片 ≠ PRD §8 降级预案（§8 降级是 LangChain Chain 线性流程，切片是 LangGraph 3 节点，框架不同）。降级预案若需要，另建一条 LangChain 链。

**三个前置定调（必须在 D2 末完成，决定后续交付物形态）**：
1. **FC 用途**：Function Calling 用于「节点内动态生成 PromQL/LogQL 查询」，**不用于节点间路由**（节点间路由由 StateGraph 固定边决定）。即「指标分析/日志分析」节点内让 LLM 用 FC 决定查哪条指标，而非 LLM 决定走哪个节点。
2. **对话工作流**：对话入口 → **跳过告警接收/聚合** → 直接进拓扑关联 → 后续与告警模式同流。**不做意图识别节点**，**不做慢SQL定位专属节点**（并入日志分析）。与 PRD §3.3 一致，覆盖 demo 的偏差。
3. **接口数量钉死 4 个**：`POST /api/alerts`、`POST /api/chat`、`GET /api/reports/{id}`、`GET /api/health`（砍掉 list/trace 端点，统一 002 的 3 与 PRD §5 的 6 之争）。

---

## 时间核算

| 类型 | 天数 | 单日 | 小计 |
|---|---|---|---|
| 工作日（1.5h）| D1-D4 + D7-D8 = 6 天 | 1.5h | 9h |
| 周末（8h+）| D5-D6 = 2 天 | 8h+ | 16h+ |
| **合计** | | | **25h+** |

---

## 日历明细（对齐真实星期）

| # | 日期 | 时长 | 学（轨1） | 建（轨2） | 产出/验收 |
|---|---|---|---|---|---|
| **D1** | **Tue 6/23**（今天）| 1.5h | LLM API/Token/Temperature；Transformer 一句话；Pretrain→SFT→RLHF | `pip install langchain langgraph openai`（chromadb 挪 D4）；跑通 `chat.completions.create()` | `hello_llm.py`；**验收:✅chat可用 ✅FC tool_call返回有效 ✅embeddings(bge-m3)返回向量** |
| **D2** | Wed 6/24 | 1.5h | Few-shot/CoT 补（Pydantic 结构化输出 ✅D1 已预习）| **首动作**:`curl`真实 Prom `/series`+Loki `/labels`核对标签→**据实写**`topology.yaml`；定义`AlertEvent`/`RCAReport`模型；告警分类Prompt；**完成三个前置定调**(见上) | `models.py`+`topology.yaml`(真实标签)+定调记录 |
| **D3** | Thu 6/25 | 1.5h | **Function Calling ⭐**；JSON Schema；tool_call 流程 | 封装 **`query_prometheus()` 一个工具** + 定义 FC 工具集 schema；用真实 Prom 验证 tool_call 真返回（`query_loki` 挪 D4） | `tools/prometheus.py`+FC schema；✅FC真实可用 |
| **D4** | Fri 6/26 | 1.5h | Embedding；余弦相似度；向量库；bge-m3 | **装 chromadb**；封装 `query_loki()`；ChromaDB 存 10 案例；`search_incidents()`；`load_topology()`；**晚 30min**:LangGraph 2节点 hello-world 预热 | `tools/loki.py`+`rag.py`+种子；✅检索Top-3 |
| **D5** | **Sat 6/27** | **8h+** | LangGraph State/Node/Edge/Compile ⭐⭐（穿插） | **上午3h**:Q&A集中刷1h+**建切片**(只验骨架,3节点Mock,场景1)<br>**下午5h**:拆 investigate→实现正式8节点+条件分支+compile | **验收:场景1告警入→产出RCAReport含根因文本+≥1指标证据+≥1日志证据+Grafana链接** |
| **D6** | **Sun 6/28** | **8h+** | — | **上午3h**:RAG/报告节点接入+真实Prom/Loki接入+**Grafana链接生成**<br>**下午3h**:FastAPI **4接口**(alerts/chat/reports/health)+webhook(**curl模拟**,不真接Alertmanager)<br>**晚上2h**:**Gradio前端**+场景1真实端到端+**排练第1遍**+【可砍】对话模式/美化+【可选,周末】**本地Ollama部署**(大模型部署补分) | API+前端+场景1全通 |
| **D7** | Mon 6/29 | 1.5h | — | 场景2(节点宕机)数据+端到端；**Prompt 验证(非"优化")**:3场景各预设标准根因关键词 | **验收:3场景≥2命中标准根因(=准确率>70%)** |
| **D8** | Tue 6/30 | 1.5h | — | **缓冲+排练日**:若场景3(对话)未做则补；否则全天排练×3+补漏 | 3场景全通+演示<3min+**有真缓冲** |

### 周末结构（D5/D6 重点）

周末是开发主力（16h+），采用「**先切片验骨架，再做复杂编排**」：

**D5 周六（8h+）**
- 上午 3h：Q&A 集中刷 1h + 建切片 agent（**只验 LangGraph 骨架**，3 节点 Mock，场景 1 纵向打通）
- 下午 5h：切片 → 8 节点扩展（拆 investigate，加拓扑/条件分支/并行节点，填真实实现）

**D6 周日（8h+）**
- 上午 3h：RAG 节点 + 报告生成节点接入 + 真实 Prom/Loki 接入 + Grafana 链接
- 下午 3h：FastAPI 网关（**4 接口钉死**）+ webhook（curl 模拟）
- 晚上 2h：Gradio 前端 + 场景 1 真实端到端 + **排练第 1 遍前置** + 【可砍】对话模式/美化 + 【可选】本地 Ollama（大模型部署补分，见决策表）

---

## 缓冲策略（修正 v1「借 D8 = 缓冲」的错误）

真缓冲来自**预先指定的可砍项**，而非挪用 deadline 当天容量：

| 可砍项 | 触发条件 | 砍后影响 |
|---|---|---|
| D6 对话模式 | D6 晚超时 | 场景3 降级为「最简对话（跳过聚合直入拓扑）」或移 D8；demo 2/3 场景仍可演示 |
| Gradio 美化 | D6 晚超时 | 用默认样式，功能不缺 |
| 场景3 完整度 | D7/D8 滑 | 只保场景1+2，场景3 作为彩蛋口述 |
| 本地 Ollama 部署 | D6 晚超时 | 砍掉，只讲云 API；放弃"大模型部署"补分 |

**排练前置**：D6 晚场景1跑通后**立刻排练第1遍**（不等 D8），把演示风险最早暴露。D8 定位为「缓冲 + 排练×3 + 补漏」，**不再背 D7 溢出的死债**。

---

## 理论 Q&A（比赛理论占 30-50%）

- **修正 v1「工作日碎片做5题」的沉默债务**：工作日 1.5h 已被学+建占满，Q&A 不塞工作日
- **集中刷**：D5/D6 上午各 1h 集中刷本周 Q&A + 比赛高频题（约 35 题分两批）
- 工作日仅通勤时**听/看**当天 1 个概念术语，不强制 5 题

---

## 已采纳的决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 前端方案 | **Gradio**（砍 React） | 0 AI 基础 + 时间紧，React 学习成本太高；Gradio 1h 出界面，与 LangGraph 天然配 |
| 学习/开发顺序 | **Interleaved**（非先学完再建） | 0 AI 基础下「学完忘一半」风险高；每天学完立刻用 |
| D7 超载处理 | **可砍项 + 排练前置 + D8 缓冲**（非「借D8」） | 挪用 deadline 容量不是真缓冲；必须预设可牺牲项 |
| 切片定位 | **只验骨架**（禁写真实推理） | 扩展时 investigate/infer_and_report 会丢弃重写；过度投入是浪费 |
| 切片次数 | **只做 1 次** | 第二次仅在首次暴露根本困惑时才做 |
| FC 用途 | **节点内查询生成**（非节点间路由） | 与 8 节点固定图自洽；D3 交付物有明确消费方 |
| 对话工作流 | **跳过聚合直入拓扑**，无意图识别节点 | 与 PRD §3.3 对齐，覆盖 demo 偏差 |
| 接口数量 | **4 个**（alerts/chat/reports/{id}/health） | 统一 002(3) 与 PRD(6) 之争 |
| Q&A 时机 | **周末集中刷**（非工作日碎片） | 避免 1.5h 工作日乘性超载导致的沉默债务 |
| LLM 服务 | **工作日(D1-D4,D7-D8): 硅基流动云 API；周末(D6晚)可选: 本地 Ollama(qwen2.5:7b)** | 工作日不折腾部署保进度；周末补"大模型部署"分，且能讲"本地+云双模式" |

---

## 前置依赖链（无阻塞）

```
env/去风险(D1) → 真实标签+模型+定调(D2) → FC/prom工具(D3) → loki/RAG/LangGraph预热(D4)
                                                          ↓
                                        切片骨架(D5上午) → 8节点图(D5下午) → API/前端/场景1(D6) → 场景2(D7) → 缓冲+排练(D8)
```

工具集成风险**前移**：D3 封完 prom 工具立刻打真实数据验 1 条，D4 封完 loki 同理，不让集成 bug 全堆到 D6。

---

## 本计划解决的问题

- ✅ 两套冲突日历 → 合并为单份权威
- ✅ 时间预算虚高（31h）→ 真实 25h
- ✅ 星期错位（6/22 标周日实为周一）→ 真实日期起算
- ✅ D7 单日超载 → 可砍项 + 排练前置 + D8 真**缓冲**（修正 v1「借D8」伪缓冲）
- ✅ FC 与 8 节点图架构矛盾 → D2 定调「FC 用于节点内查询生成」
- ✅ 对话工作流未定义 → D2 定调「跳过聚合直入拓扑，无意图识别节点」
- ✅ 真实 Prom/Loki 标签匹配 → D2 首动作核对标签据实写 topology.yaml
- ✅ 接口数量三套口径 → 钉死 4 个
- ✅ 切片「同一份代码长大」失实 → 收紧为「只验骨架禁写推理」
- ✅ 切片=§8降级预案 错误宣称 → 删除
- ✅ Q&A 沉默债务 → 改周末集中刷
- ✅ D5/D7 验收不可测 → 改为可测（RCAReport 含证据 / 3场景≥2命中）
- ✅ Grafana 链接缺位 → D6 报告节点补链接生成

## 本计划未解决（留给后续）

- ⚠️ PRD §3.1 并行 vs 条件分支控制流图示不自洽（D5 扩展时二选一，不影响 D3 交付）
- ✅ 比赛「大模型部署」补分 → D6 周末可选本地 Ollama（工作日仍用云 API；详见决策表）

---

## 日实际进展（每日回灌，CoT 调整）

### D1 · Tue 6/23 ✅ 超额
- **原计划**：装环境 + 跑通 chat + 验证 FC/embeddings
- **实际**：三件套全通（chat/FC/embeddings 均 ✅）+ **额外**完成迷你 Agent 循环（2 轮 tool_call→feed back→answer）+ 结构化输出（Pydantic + response_format）+ prompt 工程（system 控制行为）
- **关键发现**：模型自由 FC 时对"频繁重启"先查 CPU 而非内存 → 验证了「FC 用于节点内查询、节点间由工作流约束」的定调；引出 Runbook 节点思路（见 `knowledge/umodel-research.md` 借鉴节）
- **对后续影响**：D2 的 Pydantic/prompt 学习负担前移消化，D2 可聚焦真实标签核对 + 模型定义 + 定调

<!-- xr: 2026-06-23 | oracle | ❌ 5项必修(加真缓冲/D2定调FC用途/定义对话工作流/核对真实Prom标签/钉死接口数) | ⚠️ 8项建议见 PLAN.xr.md — v2 已全部采纳 -->
