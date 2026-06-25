"""
RCA Agent 数据模型（Pydantic v2）。

对应 PRD §4：AlertEvent（告警事件）+ RCAReport（根因分析报告）。
设计依据 PLAN.md 三定调（FC 节点内 / 对话直入拓扑 / 4 接口）。

类型对齐约束：枚举 value 必须与 topology.yaml 的 services[*].type / layer 严格一致。
"""
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Layer(StrEnum):
    """资源层级 （对齐 topology.yaml services[*].layer）"""
    IAAS = "iaas"
    PAAS = "paas"
    SAAS = "saas"


class ResourceType(StrEnum):
    """资源类型 （对齐 topology.yaml services[*].type）
    值即 VM metric 名前缀（node_* / mysql_* / redis_* / elasticsearch_*）
    """
    MYSQL = "mysql"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"
    NODE = "node"


class Severity(StrEnum):
    """告警严重级别（对齐 Alertmanager severity 标签）。"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class TriggerMode(StrEnum):
    """RCA 触发模式。

    ALERT=告警触发（全流程 8 节点）；CHAT=对话触发（跳过聚合直入拓扑）。
    """
    ALERT = "alert"
    CHAT = "chat"


class AlertEvent(BaseModel):
    """告警事件（告警模式入口数据，告警接收节点输出）

    service_id 初始为 None，由[拓扑关联节点] 反查topology后填充
    """
    alert_id: str = Field(description="告警唯一 ID")
    alertname: str = Field(description="告警名称，如MySQLSlowQueries")
    severity: Severity = Field(description="严重级别")
    instance: str = Field(description="真实VM标签 instance(host:port)")
    resource_type: ResourceType = Field(description="资源类型，对齐topology.type")
    layer: Layer = Field(description="资源层级，对齐topology.layer")
    service_id: str | None = Field(
        None,
        description="topology 中的 service key，拓扑关联节点反查后填充"
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="原始Prometheus标签（instance/ip/identifier/sysId/cluster/job）"
    )
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="告警描述（summary/description）"
    )
    starts_at: datetime = Field(description="告警开始时间 ISO 8601")
    status: str = Field(default="firing", description="状态 firing/resolved")


class MetricEvidence(BaseModel):
    """单条指标证据（指标分析节点输出）"""
    name: str = Field(description="指标逻辑名，对齐topology metrics key,如threads_running")
    promql: str = Field(description="真实 PromQL （来自topology metrics 定义）")
    current_value: float = Field(description="当前查询值")
    threshold: float | None = Field(None, description="异常阈值（来自topology thresholds）")
    is_anomaly: bool = Field(description="是否异常（current_value 越过threshold）")


class LogEvidence(BaseModel):
    """单条日志证据（日志分析节点输出）"""
    source: str = Field(description="日志源，如mysql-error-log / dmesg")
    logql: str | None = Field(None, description="Loki LogQL查询 （可能为空）")
    line: str = Field(description="日志原文")
    keywords: list[str] = Field(
        default_factory=list,
        description="需要高亮的关键词（如 ERROR / OOM / deadlock）"
    )


class RCAReport(BaseModel):
    """RCA 分析报告（工作流最终输出）

    evidence 用 dict[str,Any]装载三类证据，key固定:
        'metrics' -> list[MetricEvidence]
        'logs' -> list[LogEvidence]
        'similar_incidents' -> list[dict]（案例检索节点输出）
    """

    # --标识--
    event_id: str = Field(description="事件ID（关联 AlertEvent.alert_id 或对话session）")
    timestamp: datetime = Field(default_factory=datetime.now, description="报告生成时间 ISO 8601")
    trigger_mode: TriggerMode = Field(description="触发模式 alert/chat")

    # --根因结论--
    summary: str = Field(description="根因概论")
    severity: Severity = Field(description="最终判定的严重级别")
    root_cause: str = Field(description="根因详细分析")
    failure_mode_id: str | None = Field(
        None,
        description="命中的topology failure_modes.id (如FM-MYSQL-LOCK-CONTENTION)"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="置信度 0.0-1.0")

    # --证据 + 建议--
    affected_resources: list[str] = Field(
        description="受影响资源service_id 列表 （含上下游host）",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="证据集合{'metrics':[...],'logs':[...],'similar_incidents':[...]}"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="处置建议（来自topology failure_modes.recommendations + LLM 补充）"
    )

    # --交付物--
    grafana_links: list[str] = Field(
        default_factory=list,
        description="Grafana 快照链接"
    )
    workflow_trace: list[dict[str, Any]] = Field(
        default_factory=list,
        description="推理过程追踪：[{node,input_summary,output_summary,duration_ms}]"
    )


class RCAState(BaseModel):
    """LangGraph工作流状态（所有节点共享读写）

    对话模式 trigger_mode=chat 时 alert_event=None，从 user_query开始
    FC在节点内生成PromQl，结果写进metric_evidence / log_evidence
    """
    # --输入--
    trigger_mode: TriggerMode = Field(description="触发模式")
    alert_event: AlertEvent | None = Field(
        None,
        description="告警模式有值，对话模式为None"
    )
    user_query: str | None = Field(None, description="对话模式自然语言提问")

    # --节点3 拓扑关联输出--
    affected_service_ids: list[str] = Field(
        default_factory=list,
        description="命中的service_id列表（含runs_on主机）"
    )
    topology_context: dict[str, Any] = Field(
        default_factory=dict,
        description="命中的service定义片段（metrics/thresholds/failure_modes）"
    )

    # --节点4 指标分析输出--
    metric_evidence: list[MetricEvidence] = Field(default_factory=list)

    # --节点5 日志分析输出--
    log_evidence: list[LogEvidence] = Field(default_factory=list)

    # --节点6 案例检索输出--
    similar_incidents: list[dict[str, Any]] = Field(
        default_factory=list,
        description="ChromaDB 向量检索 Top-K 历史案例"
    )

    # --节点7 根因推断输出--
    root_cause: str | None = None
    failure_mode_id: str | None = None
    confidence: float = 0.0

    # --节点8 报告生成输出--
    final_report: RCAReport | None = None

    # -- 推理追踪（贯穿全流程）--
    workflow_trace: list[dict[str, Any]] = Field(
        default_factory=list,
        description="每步推理记录，最终汇入 RCAReport.workflow_trace"
    )
