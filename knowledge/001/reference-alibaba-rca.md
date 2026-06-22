# 阿里巴巴 RCA 智能体参考(技术调研)

> **文档定位**: 扩展阅读,非必学。在做 RCA 智能体时,如果需要业界参考,看这份  
> **适合**: 学完 Day 1-2 基础后,周末扩展阅读  
> **核心价值**: 阿里有一条完整的"学术研究 → 内部平台 → 云产品 → 开源生态"链路,是国内最成熟的 RCA 实践

---

## TL;DR(3 句话)

1. 阿里在 2026 年开源了 **UModel(UnifiedModel)** + **RCA-100 benchmark**,这是国内把"本体论(Ontology)"落到运维 Agent 上最完整的工程实践,**带真实种子数据,可一键跑通 RCA demo**。
2. 阿里的 Agent 框架首选 **AgentScope**(27K stars),ReAct 范式 + MCP 原生支持,适合国内部署。如果你的 RCA Agent 要用通义千问,选它而不是 LangGraph。
3. 阿里的 RCA 算法核心是 **"知识约束贝叶斯网络(KHBN)+ 异常传播链"**,生产验证可将 SRE 故障处理时间降低 20%+。

---

## 一、全景图(阿里 RCA 生态)

```
学术研究                    内部平台              云产品              开源生态
─────────────────────────────────────────────────────────────────────────
CloudRCA (CIKM'21)    ─┐                                       
MicroHECL (ICSE'21)   ├─→ EagleEye 追踪  ─→ ARMS (APM)     ─→  alibaba/UnifiedModel ⭐
iSQUAD (VLDB'20)      │   SLS 算法       ─→ SLS 智能分析     ─→  alibaba/sysom_mcp
Alibaba Trace(SoCC'21)│   CMDB 拓扑      ─→ 云监控 AIOps     ─→  alibabacloud-ack-mcp-server
DBPecker (VLDB'25)   ─┘   STAROps 平台   ─→ ACK AI 助手     ─→  agentscope (27K stars)
                                                              ─→  alibaba/clusterdata (数据集)
```

**关键转变**: 2026 年前阿里 RCA 论文代码大多不开源(只开源数据集)。2026 年开源 UModel + RCA-100 是战略级转变。

---

## 二、最值得精读的 3 个项目(按优先级)

### 🥇 `alibaba/UnifiedModel`(UModel)— 必读

| 项 | 内容 |
|---|---|
| GitHub | https://github.com/alibaba/UnifiedModel |
| Stars | ~182(2026 新开源,战略级) |
| 语言 | Go |
| 定位 | 让 AI Agent 看懂运维数据的"语义层" |

**它做了什么**: 把"实体 + 遥测数据 + 存储"及关系建模成**对象图(Object Graph)**,让 Agent 能理解"这个指标属于哪个服务、依赖什么资源"。

**核心概念**:
- 三类节点: `EntitySet`(实体) / `TelemetryDataSet`(遥测) / `Storage`(存储)
- 四类关系: `EntitySetLink` / `DataLink` / `StorageLink` / `ExplorerLink`
- **Runbook 机制**: 把专家诊断经验结构化为 5 类——`Observation`(观察) / `Toolkit`(工具) / `Knowledge`(知识) / `Automation`(自动化) / `Skill`(技能)

**为什么必读**: `examples/incident-investigation/` 是一个**完整可跑的 RCA demo**:
- 场景: 支付网关 SLO 违规 → 跨域拓扑遍历 → Runbook 引导 → 定位到"checkout-service 重试风暴"
- 带 Prometheus + ES 种子数据,`start.sh` 一键拉起
- **读懂它 = 理解"Ontology + Runbook + LLM"如何协作完成 RCA**

### 🥈 `agentscope-ai/agentscope`— Agent 框架首选

| 项 | 内容 |
|---|---|
| GitHub | https://github.com/modelscope/agentscope |
| Stars | **~27,075** |
| 语言 | Python,Apache-2.0 |
| 定位 | 阿里通义实验室旗舰 Agent 框架,2026 年已发布 2.0 |

**核心能力**:
- **ReAct 范式**(推理 + 行动闭环)作为推荐架构
- 原生支持 **MCP**(Model Context Protocol)+ **A2A** 协议
- **并行工具调用、异步执行、实时干预**(human-in-the-loop)
- 内置 browser-use / deep-research / meta-planner
- **多租户 Agent Service**(FastAPI + WebUI 开箱即用)

**与 LangGraph 的对比**(选型关键):

| 维度 | AgentScope | LangGraph |
|---|---|---|
| 核心范式 | ReAct + 异步 | 状态图(StateGraph) |
| 哲学 | 靠模型能力,不靠严格 prompt | 显式状态机,强编排 |
| MCP 支持 | 原生一等公民 | 需自行集成 |
| 生产部署 | 内置 K8s/Serverless 多租户 | LangGraph Platform |
| 中国生态 | 通义千问/DashScope 原生 | OpenAI 生态为主 |
| 多 Agent | MsgHub + Pipeline | Graph 节点 |

**选型建议**: 如果用通义千问 + 国内部署,选 AgentScope;如果用硅基流动(DeepSeek)+ 快速 demo,LangGraph 更简单。

### 🥉 `alibaba/sysom_mcp`— MCP 工具封装范例

| 项 | 内容 |
|---|---|
| GitHub | https://github.com/alibaba/sysom_mcp |
| Stars | ~70 |
| 定位 | 把 OS 诊断能力封装成 MCP 工具 |

**它做了什么**: 把 SysOM 的 20+ 个 OS 诊断能力(OOM、IO、网络丢包、Crash/vmcore)封装成 MCP 工具,让 Agent 通过自然语言调用。

**可借鉴**: "MCP 工具封装范式"——做你自己的 RCA Agent 时,把每个诊断动作(PromQL 查询、日志查询、拓扑查询)抽象成 MCP Tool,这是成熟套路。

---

## 三、架构借鉴(阿里验证过的范式)

### 混合推理架构(核心思路)

阿里不靠纯 LLM 做 RCA,而是**传统算法 + LLM 混合**:

```
传统算法(特征提取)        LLM(高层推理)         UModel(上下文)
─────────────────         ──────────           ──────────
异常检测(RobustSTL)  ─┐                       ┌─ 实体拓扑图
多维下探分析         ─┼─→ 喂给 LLM 综合判断  ←─┤ 依赖关系
异常传播链           ─┘                       └─ Runbook 知识
```

**为什么**: LLM 数值计算差、会幻觉。让传统算法做"找异常",LLM 做"解释为什么",各司其职。

### 双层 Agent 治理(阿里推荐)

```
AI 指挥官(Commander)
  ├─ 任务拆解、流程编排
  └─ AI 调度官(Dispatcher)
       └─ 模型路由:复杂任务→Qwen-Max,简单任务→Qwen-Turbo
          (实测降本 40%+ Token 成本)
```

### 你的 RCA Demo 可借鉴的架构

```
RCA Agent = AgentScope 或 LangGraph(骨架)
          + UModel 思路(实体/关系/拓扑图建模)
          + Runbook 机制(结构化诊断协议)
          + MCP 工具集(PromQL/日志/拓扑/异常检测)
          + 混合推理(传统算法做特征 + LLM 做判断)
          + Human-in-the-loop(高风险操作前暂停)
```

---

## 四、算法参考(按场景,论文级)

### 阿里生产验证的核心算法

| 场景 | 算法/论文 | 出处 | 效果 |
|---|---|---|---|
| 时序异常检测(周期性) | **RobustSTL** | SLS 流式分解 | 适合周期明显的业务指标 |
| 时序异常检测(高噪声) | **Time2Graph** | SLS 流式图 | 抗噪,无需周期假设 |
| 多维下探根因 | SLS 下探分析 | SLS 生产 | 异常事件→维度组合偏离分析 |
| 微服务根因定位 | **MicroHECL** | ICSE'21 | 异常传播链 + 剪枝,大规模高效 |
| 因果图推理 | **MicroCause** | IWQoS'20 | PCTS 因果图 + 时间因果随机游走 |
| 知识约束贝叶斯 | **CloudRCA(KHBN)** | CIKM'21 | MaxCompute 生产,SRE 处理时间降 20%+ |
| Trace 高延时定位 | SLS `trace_rca` | SLS 生产 | **95% 准确率,秒级千请求** |
| 慢查询根因 | **iSQUAD** | VLDB'20 | 间歇性慢查询,F1=80.4% |

### CloudRCA(KHBN)核心思路(最值得理解)

```
输入: KPI 异常 + 错误日志 + CMDB 拓扑
  ↓
知识驱动分层贝叶斯网络(KHBN):
  ├─ 用 CMDB 拓扑约束网络结构(避免过拟合)
  ├─ 用历史故障知识做先验
  └─ 推断: 最可能的根因服务 + 置信度
  ↓
输出: 根因服务 + 解释路径
```

**为什么重要**: 这是阿里 MaxCompute / Realtime Compute / Hologres 的**生产系统**,不是实验室玩具。

### 异常传播链(几乎所有阿里 RCA 论文的公共抽象)

```
初始异常服务
  ↓ 反向遍历调用图
  ├─ 服务 A 调用了异常服务(上游)
  ├─ 服务 A 的指标也异常? → 是 → 继续向上
  │                       → 否 → 剪枝
  └─ 最终定位: 最深的异常源 = 根因
```

---

## 五、阿里云产品中的 RCA 能力(了解即可)

### STAROps(顶层品牌,2026)
阿里云把所有 AIOps 能力收敛为 **STAROps**:
- **S**ense: 全域感知
- **T**arget: 目标导向
- **A**utonomy: 自主运维
- **R**esilience: 业务韧性

核心: UModel(数字孪生) + LLM + Agent,三位一体。

### ARMS(APM)的 RCA
- 数据: Trace + Log + Metric + 事件
- 算法: 取 1000 条最慢 Trace,对比正常 Trace,找特征差异
- **AI Copilot**: 自动解读火焰图,降低使用门槛
- **差异火焰图**: 红色=变慢,蓝色=变快

### SLS(日志服务)智能异常分析
- 三大能力: 智能巡检 / 文本分析 / 根因诊断
- Trace 高延时根因: `sls_builtin_service_trace_rca`,**95% 准确率**
- **注意**: 部分功能已下线,官方建议用"机器学习语法 + 定时 SQL"替代

---

## 六、给你的 RCA Demo 的建议

### 如果只做一件事

**花 2 天把 `alibaba/UnifiedModel/examples/incident-investigation` 跑通并读懂**。

它演示了完整链路:
```
Ontology 建模 → Runbook 诊断协议 → MCP 工具调用 → LLM 推理 → 定位根因
```

读懂后,你的 demo 架构就有了骨架。

### 对你的 7 天计划的影响

| 你的计划 | 阿里实践的启示 |
|---|---|
| Day 4 Function Calling | 参考 sysom_mcp 的工具封装范式 |
| Day 6 LangGraph | 对比 AgentScope,考虑是否切换 |
| Day 7 RAG | 参考 UModel 的 Runbook 知识结构化(比纯 RAG 更精准) |
| RCA 整体架构 | 考虑加入"混合推理"(传统异常检测 + LLM 判断) |

### ⚠️ 注意事项

1. 阿里 RCA 论文代码**大多没开源**,别指望能 clone 到 CloudRCA 实现。UModel 是例外。
2. **不要**直接用 LangGraph + 阿里生态混搭,会踩集成坑。选一条路:要么 LangGraph + 硅基流动,要么 AgentScope + 通义千问。
3. SLS 部分功能已下线,学习算法原理 OK,别指望直接用那个 App。
4. AgentScope 2.0 的 API 与 1.x **有较大变化**,看文档注意版本。

---

## 七、资源链接汇总

### 开源项目(按优先级)
| 项目 | 链接 | 用途 |
|---|---|---|
| **UnifiedModel** ⭐ | https://github.com/alibaba/UnifiedModel | 必读 RCA demo |
| **AgentScope** | https://github.com/modelscope/agentscope | Agent 框架备选 |
| SysOM MCP | https://github.com/alibaba/sysom_mcp | MCP 工具范例 |
| ACK MCP | https://github.com/aliyun/alibabacloud-ack-mcp-server | K8s 工具集 |
| SREWorks | https://github.com/alibaba/SREWorks | 运维平台参考 |
| 微服务数据集 | https://github.com/alibaba/clusterdata | 算法评估数据 |

### 关键论文
| 论文 | 链接 |
|---|---|
| CloudRCA (CIKM'21) | https://arxiv.org/pdf/2111.03753 |
| MicroHECL (ICSE'21) | https://arxiv.org/abs/2103.01782 |
| iSQUAD (VLDB'20) | http://www.vldb.org/pvldb/vol13/p1176-ma.pdf |
| Alibaba Trace (SoCC'21) | http://cloud.siat.ac.cn/pdca/socc2021-AlibabaTraceAnalysis.pdf |

### 产品文档
| 产品 | 链接 |
|---|---|
| STAROps | https://help.aliyun.com/zh/starops/ |
| SLS 算法原理 | https://help.aliyun.com/zh/sls/algorithms |
| ARMS Trace | https://www.alibabacloud.com/help/en/arms/ |

---

> **最后建议**: 这份文档是**扩展阅读**,不要在一周内全看。优先级:先把 7 天基础学完(Day 1-7),如果有余力,周末精读 UnifiedModel 的 incident-investigation 示例。比赛展示时,能提到"参考了阿里 UModel 的 Ontology 建模思路"会加分。
