# Day 2 知识储备:Prompt 工程 + 数据建模 + 拓扑设计

> 明早(6/24 周三)D2 前的预习。D2 要交付四件:**topology.yaml(真实标签) / AlertEvent·RCAReport 模型 / 告警分类 Prompt / 三个定调**。本文直接喂这四件的弹药。读完约 25 分钟。

## 场景锚定(先记住)

D2 之后所有代码都对准真实 VictoriaMetrics(**非 K8s**):
- 主键 = `instance`(host:port) + `cluster`(ES) + `ip`(主机名)
- 三层 = IaaS(主机 `node_*`) / PaaS(MySQL/Redis/ES) / SaaS(跨层症状)
- **没有** pod/container/service/namespace

---

## 模块 1 · Prompt 工程(System / Few-shot / CoT)

### 1.1 System Prompt:agent 定位焊死的地方

System 消息是**控制模型行为的最强杠杆**。RCA agent 的 system 至少四块:

```
角色:你是运维根因分析智能体
流程:拓扑关联 → 指标分析 → 日志分析 → 案例检索 → 根因推断
约束:需要数据时调工具;不会就答"信息不足",不要编造
输出:JSON,符合 RCAReport 结构
```

> 法则:**system 写"规则"(不变),user 写"具体输入"(每次变)**。这和你写 Controller 时把校验规则放拦截器、把入参放 DTO 是一个思路。

### 1.2 Few-shot:用例子控制输出

零样本(Zero-shot)只下指令;少样本(Few-shot)塞 2-3 个"输入→输出"示例,模型照着模仿。告警分类 Few-shot:

```python
messages = [
    {"role":"system","content":"把告警分到 iaas/paas/saas/container 之一,输出 JSON"},
    {"role":"user","content":"node-01 内存 95%"},                   # 例子1
    {"role":"assistant","content":'{"layer":"iaas","reason":"主机内存"}'},
    {"role":"user","content":"MySQL 连接数打满"},                    # 例子2
    {"role":"assistant","content":'{"layer":"paas","reason":"MySQL 连接池"}'},
    {"role":"user","content":"ES 搜索接口延迟飙高"},                 # 真实任务
]
```

模型看过两个例子,第三个会照格式输出。**Few-shot = 用示范代替啰嗦的指令**,对"格式严格"的任务最有效。

### 1.3 CoT(Chain-of-Thought):逼模型多步推理

RCA 根因不是一步能推出。让模型**先列证据,再下结论**,而不是直接猜。两种触发:
- system 加一句:"先逐步列出证据,再给根因"
- Few-shot 示例里展示推理过程(更稳)

> CoT 让复杂推理准确率提升 20-40%。RCA 根因推断节点必用。

### 1.4 告警分类 Prompt 模板(D2 直接用)

```python
SYSTEM = """你是 RCA 智能体的告警分类节点。
输入:一条告警描述。任务:判定故障层 + 关联的 instance/cluster。
只输出 JSON:{"layer":..., "resource":..., "reason":...}。
参考:
- 主机 CPU/内存/磁盘告警 → iaas
- MySQL/Redis/ES/Kafka 指标告警 → paas
- 业务接口慢/错误率 → saas(跨层症状)
"""
```

---

## 模块 2 · 领域数据建模(AlertEvent / RCAReport)

### 2.1 AlertEvent(对齐 Alertmanager webhook + 真实标签)

Alertmanager 推过来的 JSON 不规整,`AlertEvent` 是**清洗后的契约**:

```python
class AlertEvent(BaseModel):
    alertname: str            # HighCPU / RedisOOM / MysqlSlowQueries...
    severity: str             # critical / warning
    instance: str             # 真实 VM 主键 host:port
    layer: str                # iaas / paas / saas / container
    labels: dict              # 原始 labels 保留(identifier/ip/cluster...)
    starts_at: str            # ISO8601
```

**关键修正**:真实 VM 没有 service/pod,所以 AlertEvent 主键是 `instance`,**不是** PRD 原写的 `service`。这是 D1 真实标签核对逼出来的改动。

### 2.2 RCAReport(对齐真实根因结构)

基于 D1 真实 MySQL RCA 的发现,报告要能装"多指标交叉验证":

```python
class RCAReport(BaseModel):
    summary: str              # 一句话根因
    root_cause: str           # 详细
    confidence: float         # 0-1
    evidence: list[dict]      # [{metric, value, interpretation}, ...]
    layer_chain: list[str]    # 跨层链 ["saas:下单慢","paas:MySQL锁","iaas:CPU低"]
    suggestions: list[str]
    grafana_links: list[str] | None = None
```

`evidence` 用 `list[dict]` 而非 `list[str]`——D1 跑出来就是"命中率99.97% / 锁等待18h / QPS27"多指标,要带值带解读,不能光一句"锁竞争高"。

---

## 模块 3 · 拓扑建模(topology.yaml 真实版)

### 3.1 真实标签下的拓扑主键

PRD 原版用 `service: order-service`,真实 VM 要换成 `instance`/`cluster`:

```yaml
services:
  mysql-order:
    layer: paas
    type: mysql
    instance: "10.3.240.116:19211"
    metrics:
      connections: "mysql_global_status_threads_connected{instance='10.3.240.116:19211'}"
      slow_queries: "rate(mysql_global_status_slow_queries{instance='10.3.240.116:19211'}[5m])"
      row_lock_time: "mysql_global_status_innodb_row_lock_time{instance='10.3.240.116:19211'}"
    depends_on: ["host-10.3.240.116"]

  redis-cache:
    layer: paas
    type: redis
    instance: "hw-agent:19213"
    metrics:
      mem_used: "redis_memory_used_bytes{instance='hw-agent:19213'}"
      mem_rss: "redis_memory_used_rss_bytes{instance='hw-agent:19213'}"

  es-heimdall:
    layer: paas
    type: elasticsearch
    cluster: "heimdall-es"
    metrics:
      jvm_heap: "elasticsearch_jvm_memory_used_bytes{cluster='heimdall-es',area='heap'}"

hosts:
  host-10.3.240.116:
    layer: iaas
    metrics:
      mem_avail: "node_memory_MemAvailable_bytes"
```

### 3.2 拓扑关联节点怎么用

"拓扑关联"节点:输入告警 → 查 topology.yaml → 找到该 `instance` 的服务 + `depends_on` 的下游。**关键是 instance 匹配**,不是 service 名。

> 法则:**topology.yaml 的主键必须和真实 PromQL 里的 label 值一字不差**。D2 首动作"核对真实标签"就为这个——写错一个字符,指标查询全空。

---

## 模块 4 · D2 三个定调的理论支撑

### 4.1 FC 用于节点内查询生成(非节点间路由)

| 谁决定 | 由什么定 |
|---|---|
| **节点间**走哪步 | LangGraph 固定边(拓扑→指标→日志→...) |
| **节点内**查哪条指标 | LLM 用 FC 自主生成 PromQL |

**为什么这么分**:节点间让 LLM 决定 = 不可控(可能瞎走);节点内让 LLM 生成查询 = 灵活(适应不同告警)。**固定骨架 + 节点内灵活 = 可控又适配**。

### 4.2 对话模式跳过告警聚合,直入拓扑

- 告警 webhook 模式:接收 → 聚合(去重) → 拓扑 → ...
- 对话模式:用户提问 → **跳过接收/聚合** → 直接拓扑关联 → 后续同

**理由**:对话里没有"告警"可聚合,用户问题本身就是入口。砍两个节点省时间,逻辑也对。

### 4.3 接口钉死 4 个

`POST /api/alerts`(告警)/ `POST /api/chat`(对话)/ `GET /api/reports/{id}`(查报告)/ `GET /api/health`。

砍掉 list/trace 端点——demo 用 Gradio 简化,不需要列表页和推理回放页。**4 个够演示,不多不少**。

---

## 速记卡

| 要点 | 内容 |
|---|---|
| System vs User | system=规则(不变),user=占位符填输入(每次变) |
| Few-shot | 2-3 个 输入→输出 示例控制格式,胜过啰嗦指令 |
| CoT | 逼模型先列证据再下结论,根因节点必用 |
| AlertEvent 主键 | `instance`(非 service),对齐真实 VM |
| RCAReport.evidence | `list[dict]`(带值带解读),装多指标交叉验证 |
| topology 主键 | 必须和真实 PromQL label 值一字不差 |
| FC 定调 | 节点内生成查询,节点间由图决定 |

### 比赛理论题预测(Prompt / 建模向)

1. **System Prompt 和 User Prompt 区别?RCA 为什么把规则放 System?**(System 是不变规则;放 user 会被当输入)
2. **Few-shot 是什么?什么时候用?**(给示例控制输出;任务复杂/格式严格时)
3. **CoT 为什么能提升 RCA 准确率?**(逼多步推理,避免直觉猜)
4. **为什么 Agent 数据要建模成 Pydantic 而非 dict?**(类型校验 + 边界守卫 + 自动 schema)
5. **拓扑关联在 RCA 里干什么?**(找上下游依赖,定位影响范围和根因层)

---

> **读完本文,D2 的四件交付物(topology.yaml / 两个模型 / 告警分类 Prompt / 三个定调)都有了模板和理论依据。** 明早 1.5h 直接照真实标签填代码,不用临时查概念。
