# 002 - RCA 智能体 MVP 开发

## 版本

v1.0

## 创建时间

2025-06-22

## 完成时间

{done 时自动写入}

## 目标

基于 PRD(docs/RCA-Agent-PRD.md),完成一个可演示的 RCA 智能体 MVP:接收告警或对话提问,自动查询 Prometheus/Loki/拓扑,输出根因分析报告 + Grafana 链接。覆盖 3 个典型故障场景。

## 范围外

- 自动修复 / 自愈执行(L4 自治级)
- 多 Agent 并行推理(单 Agent 顺序工作流)
- 摄像头 / IoT 场景(已移除)
- 真实 CMDB 动态拓扑(用手写 YAML)
- 模型微调 / 训练(用云 API)
- 生产级高可用 / 并发 / 鉴权

## 完成标准

- [ ] LangGraph 工作流跑通 8 个节点(告警→聚合→拓扑→指标→日志→案例→根因→报告)
- [ ] Function Calling 能查询真实 Prometheus 指标
- [ ] Function Calling 能查询真实 Loki 日志
- [ ] ChromaDB 存入历史故障案例,能语义检索 Top-3
- [ ] FastAPI 提供 3 个接口(告警webhook / 对话 / 报告查询)
- [ ] Alertmanager webhook 能触发完整 RCA 流程
- [ ] 前端页面展示 RCA 推理过程 + 最终报告
- [ ] 场景1(容器OOM)端到端跑通,报告准确率 >70%
- [ ] 场景2(节点宕机)端到端跑通
- [ ] 场景3(慢查询)对话模式跑通
- [ ] RCA 报告包含 Grafana 快照链接

## 任务分解

### Phase 1: 基础工具(对应学习 Day 1-5)
- [ ] 封装 `query_prometheus(promql)` — prometheus-api-client
- [ ] 封装 `query_loki(logql)` — HTTP API
- [ ] 封装 `load_topology()` — 读 topology.yaml
- [ ] 封装 `search_incidents(query)` — ChromaDB 检索
- [ ] 定义 Function Calling 工具集(JSON Schema)

### Phase 2: 工作流(对应学习 Day 6)
- [ ] 定义 RCAState(TypedDict)
- [ ] 实现 8 个节点函数
- [ ] 用 LangGraph 组装状态图
- [ ] 条件分支:指标够不够→出报告/再查日志

### Phase 3: RAG(对应学习 Day 7)
- [ ] 准备 10+ 条历史故障案例数据
- [ ] 向量化存入 ChromaDB
- [ ] 案例检索节点接入工作流
- [ ] 报告生成节点(含相似案例引用)

### Phase 4: API(周末开发)
- [ ] FastAPI 网关 + 3 个接口
- [ ] Alertmanager webhook 对接
- [ ] 对话接口(跳过前2节点,直接进拓扑关联)

### Phase 5: 前端(周末开发)
- [ ] 告警列表页
- [ ] RCA 推理过程展示(步骤动画)
- [ ] 报告展示(根因/证据/建议/Grafana链接)
- [ ] 对话入口

### Phase 6: 联调 + 演示(最后1天)
- [ ] 3 个场景数据准备
- [ ] 端到端联调
- [ ] Prompt 优化(防幻觉)
- [ ] 演示排练 ×3

## 关键决策

| 决策 | 选择 | 原因 | 变更前 |
|------|------|------|--------|
| Agent框架: 编排引擎 | LangGraph | 状态机式,适合RCA多步推理;硅基流动+LangGraph配合好 | — |
| LLM: 服务商 | 硅基流动 DeepSeek-V3 | 免费额度,Function Calling 完善 | — |
| 拓扑: 数据来源 | 手写 YAML 静态拓扑 | Demo 可控,一周内可行 | — |
| 触发: 模式 | 告警webhook + 对话双模式 | 展示完整性 | — |
| 根因: 粒度 | 资源级(Pod/Node/Service) | 时间够,不做代码级 | — |
| 摄像头: 场景 | 移除 | 无真实设备,砍掉最大风险 | 曾考虑 |
| 前端: 方案 | React+AntD(主) / Gradio(备选) | ⚠️ 时间不够则降级 Gradio | — |
| 输出: 形式 | 文字报告 + Grafana链接 | 不做拓扑图可视化 | — |

## 进度记录

### 2025-06-22

- **完成**: PRD 文档(505行)、HTML交互演示(482行)、知识库(3份学习材料)、阿里RCA调研、Oracle交叉评审
- **阻塞**: 代码尚未开始(依赖 001 学习计划先打基础)
- **下一步**: 等 Day4(Function Calling)学完后,开始 Phase 1 工具封装

### 2026-06-23（D1 实操，超额）

- **环境就绪**: python3.12 venv + langchain/langgraph/openai/dotenv；硅基流动三项去风险全绿（chat ✅ / FC tool_call ✅ / bge-m3 1024维 ✅）
- **Phase 1 前置完成**: 亲手跑通 5 个 demo（chat/FC/embeddings/agent循环/结构化输出）+ 真实 `query_prometheus()` 工具打 VictoriaMetrics
- **重大发现（影响场景设计）**: 真实 VM 监控的是**传统基础设施（ES/MySQL/Redis/Kafka 主机）**，非 K8s；PRD 原 3 场景（PodOOMKilled/NodeDown/HikariPool）**全部不匹配**
- **场景重设计**: 改为 **IaaS/PaaS/SaaS 跨层 RCA**（容器场景周末用 rca-simulator 补）；3 个真实场景锁定：MySQL 慢查询→行锁竞争 / Redis 内存→OOM / ES JVM 堆→泄漏
- **真 RCA 跑通**: demo_agent_real 在真实 MySQL 上做多轮并行取证，正确识别行锁竞争根因（交叉验证 慢查询+缓冲池命中率99.97%+锁等待）
- **真实标签摸清**: 主键 `instance`(host:port) + `cluster`(ES) + `ip`，**无** pod/container/service；Redis `maxmemory=0`（场景需改用 RSS vs 主机内存）
- **Plan 更新**: PLAN.md → v2.1（D2 减载、Ollama 挪周末、3 跨层场景、缓冲策略）；UModel 调研留档（本周不部署，借 Runbook 思路）
- **阻塞**: 无
- **下一步（D2 周三）**: 据真实标签写 `topology.yaml` + 定义 `AlertEvent`/`RCAReport` 模型 + 告警分类 Prompt + 三个定调（FC节点内/对话直入拓扑/接口4个）
