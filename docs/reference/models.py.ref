"""
RCA Agent 数据模型（Pydantic v2）。

对应 PRD §4：
  - §4.1 AlertEvent（告警事件，已适配真实 VictoriaMetrics 标签）
  - §4.3 RCAReport（根因分析报告）

设计依据 PLAN.md 三定调：
  1. Function Calling 用于节点内生成 PromQL/LogQL，不用于节点间路由；
  2. 对话模式跳过告警接收/聚合，直入拓扑关联（无意图识别节点）；
  3. 接口钉死 4 个（POST /api/alerts / POST /api/chat / GET /api/reports/{id} / GET /api/health）。

类型对齐约束：
  - 枚举 value 必须与 topology.yaml 的 services[*].type / services[*].layer 严格一致；
  - 真实环境为传统基础设施，无 K8s，故 ResourceType 暂不含 pod/container（留扩展位）。
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# 枚举（替代魔法字符串，值与 topology.yaml 严格对齐）
# =============================================================================

class Layer(StrEnum):
    """资源层级（对齐 topology.yaml services[*].layer）。

    iaas=主机层，paas=数据库/中间件，saas=应用层。
    """
    IAAS = "iaas"
    PAAS = "paas"
    SAAS = "saas"


class ResourceType(StrEnum):
    """资源类型（对齐 topology.yaml services[*].type）。

    值即 VictoriaMetrics metric 名前缀（node_* / mysql_* / redis_* / elasticsearch_*），
    告警分类节点据此从 metric 名推断 resource_type。
    """
    MYSQL = "mysql"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"
    NODE = "node"
    # K8s 扩展位（D2 无容器监控，container_* = 0，故不启用）
    # POD = "pod"
    # CONTAINER = "container"


class Severity(StrEnum):
    """告警严重级别（对齐 Alertmanager severity 标签）。"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class TriggerMode(StrEnum):
    """RCA 触发模式。

    ALERT=告警 webhook 触发（走全流程 8 节点）；
    CHAT=对话触发（按三定调跳过告警接收/聚合，直入拓扑关联）。
    """
    ALERT = "alert"
    CHAT = "chat"


# =============================================================================
# AlertEvent（PRD §4.1，适配真实 VM 标签）
# =============================================================================

class AlertEvent(BaseModel):
    """告警事件（告警模式入口数据，告警接收节点输出）。

    设计要点：
    - labels 保留原始 Prometheus/VM 标签（instance/ip/identifier/sysId/cluster 等），
      告警分类节点从 webhook payload 原样透传；
    - service_id 对齐 topology.yaml 的 services key（如 'mysql-prod-56'），
      初始为 None，由「拓扑关联节点」从 instance/cluster 反查 topology 后填充；
    - resource_type / layer 由「告警分类节点」从 metric 名前缀推断（见 classify prompt）。
    """
    alert_id: str = Field(description="告警唯一 ID（由接收节点生成，如 webhook 去重 key 的 hash）")
    alertname: str = Field(description="告警名称，如 MySQLSlowQueries / RedisMemoryHigh")
    severity: Severity = Field(description="严重级别 critical/warning/info")
    instance: str = Field(description="真实 VM 标签 instance（host:port 格式）")
    resource_type: ResourceType = Field(description="资源类型，对齐 topology services.type")
    layer: Layer = Field(description="资源层级，对齐 topology services.layer")
    service_id: str | None = Field(
        None,
        description="topology.yaml 中的 service key，拓扑关联节点反查后填充",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="原始 Prometheus 标签（instance/ip/identifier/sysId/cluster/job 等）",
    )
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="告警描述（summary/description 等）",
    )
    starts_at: datetime = Field(description="告警开始时间（ISO 8601）")
    status: str = Field(default="firing", description="状态 firing/resolved")


# =============================================================================
# 证据模型（指标 / 日志，供 RCAReport.evidence 复用）
# =============================================================================

class MetricEvidence(BaseModel):
    """单条指标证据（指标分析节点输出）。"""
    name: str = Field(description="指标逻辑名，对齐 topology metrics key，如 threads_running")
    promql: str = Field(description="真实 PromQL（来自 topology metrics 定义）")
    current_value: float = Field(description="当前查询值")
    threshold: float | None = Field(None, description="异常阈值（来自 topology thresholds）")
    is_anomaly: bool = Field(description="是否异常（current_value 越过 threshold）")


class LogEvidence(BaseModel):
    """单条日志证据（日志分析节点输出）。"""
    source: str = Field(description="日志源，如 'mysql-error-log' / 'dmesg'")
    logql: str | None = Field(None, description="Loki LogQL 查询（可能为空）")
    line: str = Field(description="日志原文")
    keywords: list[str] = Field(
        default_factory=list,
        description="需高亮的关键词（如 ERROR / OOM / deadlock）",
    )


# =============================================================================
# RCAReport（PRD §4.3）
# =============================================================================

class RCAReport(BaseModel):
    """RCA 分析报告（根因推断节点 + 报告生成节点最终输出）。

    evidence 用 dict[str, Any] 灵活装载三类证据，key 固定为：
      'metrics' -> list[MetricEvidence]
      'logs'    -> list[LogEvidence]
      'similar_incidents' -> list[dict]（案例检索节点输出）
    """
    event_id: str = Field(description="事件 ID（关联 AlertEvent.alert_id 或对话 session）")
    timestamp: datetime = Field(default_factory=datetime.now, description="报告生成时间")
    trigger_mode: TriggerMode = Field(description="触发模式 alert/chat")
    summary: str = Field(description="一句话根因概述")
    severity: Severity = Field(description="最终判定的严重级别")
    affected_resources: list[str] = Field(
        description="受影响资源 service_id 列表（含上下游 host）",
    )
    root_cause: str = Field(description="根因详细分析")
    failure_mode_id: str | None = Field(
        None,
        description="命中的 topology failure_modes.id（如 FM-MYSQL-LOCK-CONTENTION）",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="证据集合 {'metrics':[...], 'logs':[...], 'similar_incidents':[...]}",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="置信度 0.0-1.0")
    recommendations: list[str] = Field(
        default_factory=list,
        description="处置建议（来自 topology failure_modes.recommendations + LLM 补充）",
    )
    grafana_links: list[str] = Field(
        default_factory=list,
        description="Grafana 快照链接",
    )
    workflow_trace: list[dict[str, Any]] = Field(
        default_factory=list,
        description="推理过程追踪：[{node, input_summary, output_summary, duration_ms}]",
    )


# =============================================================================
# RCAState（LangGraph 工作流内部状态，所有节点共享）
# =============================================================================

class RCAState(BaseModel):
    """LangGraph 工作流状态（所有节点共享读写）。

    设计依据 PLAN.md 三定调：
    - 对话模式 trigger_mode=chat 时 alert_event=None，直接从 user_query + topology_context 开始；
    - FC 在节点内动态生成 PromQL（指标/日志节点），结果写入 metric_evidence / log_evidence，
      节点间路由由 StateGraph 固定边决定，不在此 State 体现路由逻辑。
    """
    # ── 输入 ──
    trigger_mode: TriggerMode = Field(description="触发模式")
    alert_event: AlertEvent | None = Field(
        None,
        description="告警模式有值，对话模式为 None",
    )
    user_query: str | None = Field(None, description="对话模式自然语言提问")

    # ── 拓扑关联节点输出 ──
    affected_service_ids: list[str] = Field(
        default_factory=list,
        description="命中的 service_id 列表（含 runs_on 主机）",
    )
    topology_context: dict[str, Any] = Field(
        default_factory=dict,
        description="命中的 service 定义片段（metrics/thresholds/failure_modes）",
    )

    # ── 指标分析节点输出 ──
    metric_evidence: list[MetricEvidence] = Field(default_factory=list)

    # ── 日志分析节点输出 ──
    log_evidence: list[LogEvidence] = Field(default_factory=list)

    # ── 案例检索节点输出 ──
    similar_incidents: list[dict[str, Any]] = Field(
        default_factory=list,
        description="ChromaDB 向量检索 Top-K 历史案例",
    )

    # ── 根因推断节点输出 ──
    root_cause: str | None = None
    failure_mode_id: str | None = None
    confidence: float = 0.0

    # ── 报告生成节点输出 ──
    final_report: RCAReport | None = None

    # ── 推理追踪（贯穿全流程）──
    workflow_trace: list[dict[str, Any]] = Field(
        default_factory=list,
        description="每步推理记录，最终汇入 RCAReport.workflow_trace",
    )
