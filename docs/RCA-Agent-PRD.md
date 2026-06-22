# 运维根因分析(RCA)智能体 — 产品需求文档

> **版本**: v1.0  
> **日期**: 2025-06-22  
> **状态**: 已确认需求边界,待实施  
> **目标**: 一周内完成比赛 Demo 级 MVP

---

## 1. 项目概述

### 1.1 一句话定义

基于 LLM 的运维根因分析智能体,接收 Prometheus/Alertmanager 告警或用户自然语言提问,自动查询指标、日志、拓扑,输出根因分析报告和处置建议。

### 1.2 核心价值

| 价值点 | 说明 |
|---|---|
| **自动化** | 告警触发后 30 秒内输出根因报告,无需人工排查 |
| **可解释** | 每一步推理过程可见(指标→日志→推断→结论),非黑盒 |
| **知识沉淀** | 历史故障案例通过 RAG 检索,系统越用越准 |
| **多场景覆盖** | IaaS / PaaS / SaaS / 容器(Docker/K8s) 四层统一分析 |

### 1.3 技术亮点(评委关注点)

- **LangGraph 状态机编排**:RCA 本质是多步推理状态机,LangGraph 天然适配
- **Function Calling**:LLM 自主决定何时查 Prometheus、查 Loki、查拓扑
- **RAG 知识库**:历史故障案例检索,实现"经验积累"
- **双触发模式**:告警自动触发 + 人工对话查询

---

## 2. 系统架构

### 2.1 架构图

```
┌──────────────────────────────────────────────────────────┐
│                        用户层                             │
│   ┌────────────┐       ┌──────────────┐                  │
│   │  告警入口   │       │   对话入口    │                  │
│   │ (Webhook)  │       │  (Web 界面)   │                  │
│   └─────┬──────┘       └──────┬───────┘                  │
│         │                     │                           │
├─────────┼─────────────────────┼─────────────────────────┤
│         ▼                     ▼        服务层            │
│   ┌──────────────────────────────────┐                   │
│   │         FastAPI 网关              │                   │
│   └──────────────┬───────────────────┘                   │
│                  │                                        │
│   ┌──────────────▼───────────────────┐                   │
│   │      LangGraph RCA 工作流         │                   │
│   │                                   │                   │
│   │  告警接收 → 告警聚合 → 拓扑关联    │                   │
│   │     → 指标分析 → 日志分析         │                   │
│   │     → 历史案例检索 → 根因推断     │                   │
│   │     → 报告生成                    │                   │
│   └──┬───────┬───────┬───────┬───────┘                   │
│      │       │       │       │        数据层             │
│   ┌──▼──┐ ┌──▼──┐ ┌─▼───┐ ┌─▼────┐                      │
│   │Prom │ │Loki │ │CMDB │ │Chroma│                      │
│   │QL    │ │QL   │ │YAML │ │(RAG) │                      │
│   └─────┘ └─────┘ └─────┘ └──────┘                      │
│                  │                                       │
│   ┌──────────────▼───────────────────┐                   │
│   │     硅基流动 LLM API              │                   │
│   │     (DeepSeek-V3)                │                   │
│   └──────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| LLM | 硅基流动 DeepSeek-V3 | 免费额度、中文优秀、Function Calling 完善 |
| Agent 编排 | LangGraph | 状态机式,天然适合 RCA 多步推理 |
| 后端 | FastAPI | 异步、自动文档、Python 生态 |
| 前端 | React + Ant Design / Gradio | 比赛展示用(待最终确认) |
| 向量库 | Chroma | 轻量嵌入式,无需额外服务 |
| Embedding | bge-m3(硅基流动) | 中文效果好 |
| 指标查询 | prometheus-api-client | Python 官方推荐 |
| 日志查询 | Loki HTTP API | 简单直接 |

---

## 3. RCA 工作流详解(核心)

### 3.1 工作流状态机

```
START
  │
  ▼
[1. 告警接收] ──→ [2. 告警聚合] ──→ [3. 拓扑关联]
                                        │
                         ┌──────────────┼──────────────┐
                         ▼              ▼              ▼
                   [4. 指标分析]  [5. 日志分析]  [6. 案例检索]
                         │              │              │
                         └──────────────┼──────────────┘
                                        │
                                        ▼
                                  [7. 根因推断]
                                        │
                                        ▼
                                  [8. 报告生成]
                                        │
                                        ▼
                                       END
```

### 3.2 各节点职责

| 步骤 | 节点 | 输入 | 动作 | 输出 | 工具 |
|---|---|---|---|---|---|
| 1 | 告警接收 | Alertmanager webhook | 解析告警 JSON,提取关键字段 | AlertEvent 对象 | - |
| 2 | 告警聚合 | AlertEvent 列表 | 按(服务+告警名)分组去重 | 聚合后事件 | - |
| 3 | 拓扑关联 | 事件对象 | 查 topology.yaml,找上下游依赖 | 受影响资源列表 | 读 YAML |
| 4 | 指标分析 | 受影响资源 | 查 Prometheus,找异常指标 | 异常指标列表 | PromQL 查询 |
| 5 | 日志分析 | 受影响资源 | 查 Loki,找 ERROR 日志 | 错误日志摘要 | LogQL 查询 |
| 6 | 案例检索 | 事件描述 | 向量检索相似历史故障 | Top-3 相似案例 | Chroma 查询 |
| 7 | 根因推断 | 上述全部结果 | LLM 综合分析 | 根因假设(带置信度) | LLM 推理 |
| 8 | 报告生成 | 根因+全过程 | 生成结构化报告 | Markdown + Grafana 链接 | LLM 生成 |

### 3.3 对话模式

用户提问时,跳过步骤 1-2,直接从步骤 3 开始:

```
用户: "为什么 order-service 响应变慢?"
  → 拓扑关联: 找到 order-service 依赖 MySQL + Redis
  → 指标分析: 查 MySQL 慢查询指标
  → 日志分析: 查 order-service ERROR 日志
  → 根因推断: MySQL 慢查询导致连接池耗尽
  → 报告: 文字报告 + Grafana 链接
```

---

## 4. 数据模型

### 4.1 告警事件

```python
@dataclass
class AlertEvent:
    alert_id: str           # 告警唯一 ID
    alertname: str          # 告警名称,如 "PodOOMKilled"
    severity: str           # critical / warning / info
    service: str            # 受影响服务,如 "order-service"
    resource_type: str      # pod / node / container / service
    resource_name: str      # 具体资源名
    layer: str              # iaas / paas / saas / container
    labels: dict            # 原始 Prometheus labels
    annotations: dict       # 告警描述
    starts_at: str          # 告警开始时间(ISO 8601)
    status: str             # firing / resolved
```

### 4.2 拓扑定义(YAML)

```yaml
# topology.yaml
services:
  order-service:
    layer: saas
    type: deployment
    namespace: prod
    replicas: 3
    depends_on:
      - mysql-order-db
      - redis-cache
    metrics:
      latency_p95: >
        histogram_quantile(0.95,
          rate(http_request_duration_seconds_bucket
            {service="order-service"}[5m]))
      error_rate: >
        rate(http_requests_total
          {service="order-service",status=~"5.."}[5m])

  mysql-order-db:
    layer: paas
    type: statefulset
    depends_on:
      - node-01
    metrics:
      connections: "mysql_global_status_threads_connected"
      slow_queries: "rate(mysql_global_status_slow_queries[5m])"

  redis-cache:
    layer: paas
    type: deployment
    depends_on:
      - node-02
    metrics:
      memory_used: "redis_memory_used_bytes"
      hit_rate: "redis_keyspace_hits_total"

nodes:
  node-01:
    layer: iaas
    role: worker
    metrics:
      cpu_usage: >
        100 - (avg by (instance)
          (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
      memory_usage: >
        100 * (1 - (node_memory_MemAvailable_bytes
          / node_memory_MemTotal_bytes))
```

### 4.3 RCA 报告

```python
@dataclass
class RCAReport:
    event_id: str
    timestamp: str
    summary: str              # 一句话概述
    severity: str             # 严重程度
    affected_resources: list  # 受影响资源列表
    root_cause: str           # 根因分析(详细)
    evidence: dict            # 证据 {metrics: ..., logs: ...}
    confidence: float         # 置信度 0.0 - 1.0
    recommendations: list     # 处置建议列表
    grafana_links: list       # Grafana Dashboard 链接
    similar_incidents: list   # 相似历史案例 Top-3
    workflow_trace: list      # 推理过程每一步记录
```

---

## 5. 接口设计

### 5.1 告警接收(Webhook)

```
POST /api/alerts
Content-Type: application/json

# Alertmanager 标准 webhook 格式
{
  "version": "4",
  "groupKey": "{...}",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "PodOOMKilled",
        "service": "order-service",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Pod was OOM killed"
      },
      "startsAt": "2025-06-22T10:30:00Z"
    }
  ]
}
```

### 5.2 对话查询

```
POST /api/chat
Content-Type: application/json

Request:
{
  "message": "为什么 order-service 响应变慢?",
  "context": {}  // 可选:附加上下文
}

Response:
{
  "report": { ... },       // RCAReport 对象
  "workflow_trace": [...]  // 推理过程
}
```

### 5.3 报告查询

```
GET /api/reports/{event_id}     # 查询单个报告
GET /api/reports?limit=10       # 查询报告列表
GET /api/reports/{event_id}/trace  # 查询推理过程
```

### 5.4 健康检查

```
GET /api/health
Response: { "status": "ok", "version": "1.0.0", "llm": "connected" }
```

---

## 6. 演示场景(3 个)

### 场景 1:容器 OOM(告警触发)

```
告警: PodOOMKilled / order-service / pod-xxx
  │
  ├─ 拓扑关联: pod-xxx 调度在 node-01,属 order-service(deployment)
  ├─ 指标分析: node-01 内存 92%,pod-xxx 内存接近 limit(512Mi)
  ├─ 日志分析: "java.lang.OutOfMemoryError: Java heap space"
  ├─ 案例检索: 匹配历史案例 #2024-0815(内存泄漏)
  ├─ 根因推断: 应用内存泄漏 → 达到 limit → OOMKilled
  ├─ 建议: 临时提高 limit 至 1Gi;长期排查 Full GC 频率
  └─ Grafana: 内存趋势图 / Pod 状态图
```

### 场景 2:节点宕机连锁故障(告警触发)

```
告警: NodeDown / node-02 / critical
  │
  ├─ 拓扑关联: node-02 上运行 order-service(2/3副本)、payment-service
  ├─ 指标分析: node-02 心跳丢失,关联 Pod 状态 Pending
  ├─ 日志分析: 调度器 "0/3 nodes available: resource insufficient"
  ├─ 案例检索: 匹配历史案例 #2024-0301(资源不足)
  ├─ 根因推断: node-02 宕机 → 资源不足 → Pod 无法重调度
  ├─ 建议: 检查 node-02 硬件;扩容 node-03
  └─ Grafana: 集群资源概览 / Pod 调度图
```

### 场景 3:数据库慢查询致超时(对话触发)

```
用户提问: "为什么 payment-service 请求超时?"
  │
  ├─ 拓扑关联: payment-service → 依赖 mysql-payment-db
  ├─ 指标分析: MySQL 慢查询 50+/min,连接池使用率 100%
  ├─ 日志分析: "HikariPool-1 - Connection is not available"
  ├─ 案例检索: 匹配历史案例 #2024-0512(慢SQL致连接池耗尽)
  ├─ 根因推断: 慢 SQL 占满连接池 → 请求排队 → 超时
  ├─ 建议: 优化慢 SQL;增大连接池上限;加索引
  └─ Grafana: MySQL 性能面板 / 服务延迟面板
```

---

## 7. 一周实施计划

> **时间预算**: 工作日晚 3h × 5 + 周末 8h × 2 = 31 小时

### Day 1(周一)晚 3h:环境 + 跑通 LLM 调用

| 时段 | 任务 | 验收 |
|---|---|---|
| 19:00-20:00 | Python 3.11 环境 + 注册硅基流动 + 获取 API Key | API Key 到手 |
| 20:00-21:00 | `pip install openai langchain langgraph` | 安装成功 |
| 21:00-22:00 | 跑通第一段 LLM 调用代码 | 控制台有回答 |

**验收清单**:
- [ ] 硅基流动 API 可调通,返回正常
- [ ] LangChain 基础 Chain 跑通
- [ ] 笔记记录 API Key 和 base_url

### Day 2(周二)晚 3h:Prometheus 查询工具

| 时段 | 任务 | 验收 |
|---|---|---|
| 19:00-20:00 | `pip install prometheus-api-client`,连接真实 Prometheus | 能查询指标 |
| 20:00-21:00 | 封装 `query_prometheus(promql)` 函数 | 输入 PromQL 返回值 |
| 21:00-22:00 | 封装 `query_loki(logql)` 函数 | 输入 LogQL 返回日志 |

**验收清单**:
- [ ] 能用 Python 查 Prometheus 指标
- [ ] 能用 Python 查 Loki 日志
- [ ] 两个函数封装好,接口稳定

### Day 3(周三)晚 3h:LangGraph 工作流骨架

| 时段 | 任务 | 验收 |
|---|---|---|
| 19:00-20:30 | 定义 StateGraph + 8 个节点函数骨架 | 图能编译 |
| 20:30-22:00 | 实现"告警接收→聚合→拓扑关联"前 3 个节点 | Mock 数据跑通 |

**验收清单**:
- [ ] LangGraph StateGraph 能编译
- [ ] 前三个节点用 Mock 数据跑通
- [ ] 拓扑 YAML 定义好(至少 3 个服务)

### Day 4(周四)晚 3h:工作流核心节点

| 时段 | 任务 | 验收 |
|---|---|---|
| 19:00-20:30 | 实现"指标分析+日志分析"节点(调真实 Prometheus) | 有真实输出 |
| 20:30-22:00 | 实现"根因推断"节点(LLM 分析) | 输出根因文本 |

**验收清单**:
- [ ] 指标分析节点返回异常指标
- [ ] 日志分析节点返回错误日志
- [ ] 根因推断节点输出有逻辑的根因

### Day 5(周五)晚 3h:RAG + 报告生成

| 时段 | 任务 | 验收 |
|---|---|---|
| 19:00-20:00 | `pip install chromadb`,存入 10 条历史案例 | 能检索 |
| 20:00-21:00 | 实现"案例检索"节点 | 返回 Top-3 相似案例 |
| 21:00-22:00 | 实现"报告生成"节点 | 输出完整 Markdown 报告 |

**验收清单**:
- [ ] Chroma 存入历史案例,能检索
- [ ] 完整工作流 8 个节点全部跑通
- [ ] 输出结构化报告

### Day 6(周六)8h:FastAPI + 前端 + 联调 ⭐

| 时段 | 任务 | 验收 |
|---|---|---|
| 9:00-11:00 | FastAPI 后端:4 个接口实现 | Postman 调通 |
| 11:00-12:00 | Alertmanager webhook 对接 | 告警能触发 RCA |
| 14:00-17:00 | 前端页面(3 个页面:告警列表/对话/报告) | 页面能交互 |
| 19:00-21:00 | 端到端联调:触发告警→RCA→展示报告 | 完整流程跑通 |

**验收清单**:
- [ ] FastAPI 4 个接口可用
- [ ] Alertmanager webhook 能触发
- [ ] 前端能展示 RCA 过程和报告
- [ ] 端到端流程跑通

### Day 7(周日)8h:演示数据 + 优化 + 排练

| 时段 | 任务 | 验收 |
|---|---|---|
| 9:00-12:00 | 准备 3 个演示场景的完整数据 | 场景可复现 |
| 14:00-16:00 | 优化 Prompt(防幻觉、提升准确率) | 报告质量提升 |
| 16:00-17:00 | Grafana 链接集成 | 报告带可点击链接 |
| 19:00-21:00 | 演示排练 ×3 遍 | 流程顺畅 |

**验收清单**:
- [ ] 3 个场景都能完美演示
- [ ] 报告准确率 >70%
- [ ] 演示流程 <3 分钟

---

## 8. 风险评估

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| Prometheus 查询语句写错 | 高 | 中 | 提前准备好常用 PromQL |
| LLM 根因推断不准 | 中 | 高 | 用 Few-shot + CoT 提升推理质量 |
| 前端耗时超预期 | 高 | 高 | 备选 Gradio 方案 |
| LangGraph 学习曲线 | 中 | 中 | 参考 LangGraph 官方 RCA 示例 |
| 硅基流动免费额度用完 | 低 | 中 | 备选 DeepSeek API |

### 应急预案

| 情况 | 处理 |
|---|---|
| Day 3 LangGraph 搞不定 | 降级为 LangChain Chain(线性流程) |
| Day 6 前端做不完 | 换 Gradio,1h 出界面 |
| Day 7 整体没跑通 | 至少保证场景 1(OOM)能演示 |

---

## 9. 目录结构(预期)

```
rca-agent/
├── docs/
│   └── RCA-Agent-PRD.md          # 本文档
├── demo/
│   └── index.html                # HTML 演示页面
├── src/
│   ├── main.py                   # FastAPI 入口
│   ├── config.py                 # 配置(API Key 等)
│   ├── models.py                 # 数据模型
│   ├── topology.yaml             # 静态拓扑
│   ├── workflow/
│   │   ├── graph.py              # LangGraph 定义
│   │   ├── nodes.py              # 8 个节点函数
│   │   └── state.py              # 工作流状态定义
│   ├── tools/
│   │   ├── prometheus.py         # PromQL 查询封装
│   │   ├── loki.py               # LogQL 查询封装
│   │   └── rag.py                # Chroma 向量检索
│   └── api/
│       ├── alerts.py             # 告警 webhook
│       ├── chat.py               # 对话接口
│       └── reports.py            # 报告查询
├── data/
│   └── incidents/                # 历史案例数据
├── frontend/                     # 前端代码
├── requirements.txt
└── docker-compose.yml            # 本地基础设施
```

---

## 10. 下一步

1. **确认本文档** → 有疑问随时提出修改
2. **打开 demo/index.html** → 在浏览器中查看交互式演示
3. **确认前端方案**(React vs Gradio)→ 影响 Day 6 工作量
4. **开始 Day 1** → 环境搭建 + LLM 调通
