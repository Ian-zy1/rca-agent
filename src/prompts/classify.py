"""
告警分类 Prompt（节点1「告警接收节点」调用）。

用途：输入 Alertmanager webhook 原始 payload，输出结构化分类字段
      （severity / resource_type / layer 推断 + 关键字段提取），
      供后续构造 AlertEvent。

设计依据 PLAN.md 三定调：
  - FC 不用于节点间路由，故此处采用**结构化 JSON 输出**
    （OpenAI response_format=json_object 或 Pydantic 解析）而非 Function Calling；
  - Few-shot 覆盖真实环境 3 场景（MySQL / Redis / ES），instance / cluster 全部真实。
"""

import json
from typing import Any

# =============================================================================
# System Prompt：定义任务、输出 schema 与推断规则
# =============================================================================

SYSTEM_PROMPT = """你是运维 RCA 助手的告警分类模块。
任务：从 Alertmanager webhook 原始告警中提取关键字段，并推断 resource_type 和 layer。

输出必须是合法 JSON，schema 如下：
{
  "alertname": str,                         // 告警名
  "severity": "critical" | "warning" | "info",
  "resource_type": "mysql" | "redis" | "elasticsearch" | "node",
  "layer": "iaas" | "paas" | "saas",
  "instance": str,                          // host:port 格式
  "summary": str                            // 一句话概述
}

判断规则：
- resource_type 看 metric 名前缀：mysql_* → mysql，redis_* → redis，
  elasticsearch_* → elasticsearch，node_* → node。
- layer：主机类(node) → iaas；数据库/中间件(mysql/redis/elasticsearch) → paas；应用 → saas。
- severity 优先取 alertmanager 原始 labels.severity；缺失时按 metric 名推断
 （含 down/error/oom/critical → critical；high/warn → warning；其余 → info）。
- instance 从 labels.instance 取，标准格式 host:port；ES 额外保留 labels.cluster。
- summary 用中文一句话概括「资源 + 现象」。

约束：
- 只输出上述 JSON，不要附加任何解释文字。
- 不要臆造 instance / cluster，只能从输入 labels 中提取。
"""


# =============================================================================
# Few-shot 例子（基于真实环境 3 场景，instance / cluster / identifier / sysId
# 均为 VictoriaMetrics 实测值，禁止修改）
# =============================================================================

FEW_SHOT_EXAMPLES = [
    # ── 场景1：MySQL 慢查询（行锁竞争）──
    {
        "input": {
            "alerts": [
                {
                    "labels": {
                        "alertname": "MySQLSlowQueries",
                        "instance": "10.3.240.116:19211",
                        "identifier": "56",
                        "sysId": "20",
                        "severity": "critical",
                    },
                    "annotations": {
                        "summary": "MySQL 慢查询速率 > 10/s 持续 5 分钟",
                    },
                    "startsAt": "2026-06-24T10:30:00Z",
                }
            ]
        },
        "output": {
            "alertname": "MySQLSlowQueries",
            "severity": "critical",
            "resource_type": "mysql",
            "layer": "paas",
            "instance": "10.3.240.116:19211",
            "summary": "MySQL 10.3.240.116:19211 慢查询速率异常",
        },
    },
    # ── 场景2：Redis 内存 OOM（maxmemory=0 为真实核心约束）──
    {
        "input": {
            "alerts": [
                {
                    "labels": {
                        "alertname": "RedisMemoryHigh",
                        "instance": "hw-agent:19213",
                        "identifier": "4",
                        "sysId": "1",
                        "severity": "critical",
                    },
                    "annotations": {
                        "summary": "Redis RSS 接近主机物理内存上限",
                    },
                    "startsAt": "2026-06-24T11:00:00Z",
                }
            ]
        },
        "output": {
            "alertname": "RedisMemoryHigh",
            "severity": "critical",
            "resource_type": "redis",
            "layer": "paas",
            "instance": "hw-agent:19213",
            "summary": "Redis hw-agent:19213 RSS 内存触顶（注意 maxmemory=0 未设上限）",
        },
    },
    # ── 场景3：ES JVM heap 高位（cluster=heimdall-es 真实）──
    {
        "input": {
            "alerts": [
                {
                    "labels": {
                        "alertname": "ESJvmHeapHigh",
                        "instance": "hw-agent:19212",
                        "cluster": "heimdall-es",
                        "identifier": "3",
                        "sysId": "1",
                        "severity": "warning",
                    },
                    "annotations": {
                        "summary": "ES JVM heap 使用率 > 85%",
                    },
                    "startsAt": "2026-06-24T09:15:00Z",
                }
            ]
        },
        "output": {
            "alertname": "ESJvmHeapHigh",
            "severity": "warning",
            "resource_type": "elasticsearch",
            "layer": "paas",
            "instance": "hw-agent:19212",
            "summary": "ES heimdall-es 集群 JVM heap 高位",
        },
    },
]


# =============================================================================
# 构造消息列表
# =============================================================================

def build_classify_prompt(webhook_payload: dict[str, Any]) -> list[dict[str, str]]:
    """构造 chat.completions 的 messages 列表。

    将 System Prompt、3 个 Few-shot 例子（user/assistant 成对）、实际输入
    依序拼装，可直接传给 OpenAI 兼容 client（硅基流动 DeepSeek-V3）。

    Args:
        webhook_payload: Alertmanager webhook 原始 JSON（含 alerts 数组）。

    Returns:
        messages 列表，每个元素形如 {"role": ..., "content": ...}。
        Few-shot 的 assistant 内容用 json.dumps 序列化，确保示例本身就是
        合法 JSON（与 SYSTEM_PROMPT 的 JSON 输出要求保持一致）。
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Few-shot：成对注入 user 输入与 assistant 标准输出
    for example in FEW_SHOT_EXAMPLES:
        messages.append(
            {"role": "user", "content": "输入：" + json.dumps(example["input"], ensure_ascii=False)}
        )
        messages.append(
            {"role": "assistant", "content": json.dumps(example["output"], ensure_ascii=False)}
        )

    # 实际待分类输入
    messages.append(
        {"role": "user", "content": "输入：" + json.dumps(webhook_payload, ensure_ascii=False)}
    )
    return messages
