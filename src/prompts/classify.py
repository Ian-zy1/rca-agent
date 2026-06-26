"""
告警分类 Prompt (节点1【告警接收节点】调用)

用途：输入Alertmanager webhook原始 payload，输出结构化分类字段
    （severity / resource_type / layer推断+关键字段提取），
    供后续构造AlertEvent

设计依据三定调：FC不用于节点间路由，故此处用结构化JSON输出而非Function Calling
"""

import json
from typing import Any

# System Prompt: 定义任务、输出schema与推断规则
SYSTEM_PROMPT = """你是运维RCA助手的告警分类模块。
任务：从Alertmanager webhook 原始告警中提取关键字段，并推断resource_type 和layer。

输出必须是合法JSON，schema如下：
{
    "alertname":str,
    "severity": "critical" | "warning" | "info",
    "resource_type": "mysql" | "redis" | "elasticsearch" | "node",
    "layer": "iaas" | "paas" | "saas",
    "instance": str,
    "summary": str
}

判断规则：
- resource_type 看 metric 名前缀：mysql_* -> mysql, redis_* -> redis,
    elasticsearch_* -> elasticsearch,node_*->node。
- layer: 主机类(node) -> iaas；数据库/中间件（mysql/redis/elasticsearch） -> paas；应用 -> saas。
- severity 优先取 alertmanager 原始labels.severity；缺失时按metric名推断
 （含down/error/oom/critical -> critical；high/warn ->warning；其余->info）。
- instance从labels.instance取，标准格式host:port；ES额外保留labels.cluster。
- summary用中文一句话概括【资源+现象】    
    
约束：
- 只输出上述JSON，不要附加任何解释文字。
- 不要臆造instance / cluster，只能从输入labels中提取。
"""

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


def build_classify_prompt(webhook_payload: dict[str, Any]) -> list[dict[str, str]]:
    """构造 chat.completions 的 messages 列表。

    System Prompt + 3 个 Few-shot（user/assistant 成对）+ 实际输入，依序拼装，
    可直接传给硅基流动 DeepSeek-V3。
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Few-shot: 成对注入 user 输入与assistant 标准输出
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
