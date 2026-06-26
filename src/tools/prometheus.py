"""Prometheus/VictoriaMetrics 查询工具（节点4「指标分析」调用）。

D1 demo_real_query 的工程化版本：返回 float（可填 MetricEvidence.current_value），
带错误处理，配合 topology.metrics 的 PromQL。
"""

import os

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv("app/.env")

PROM_URL = os.environ["PROM_URL"].rstrip("/")
PROM_AUTH = (os.environ["PROM_USER"], os.environ["PROM_PASS"])


def query_prometheus(promql: str) -> float | None:
    """查 PromQL 即时值，返回float。失败/空结果返回None

    Args:
        promql: PromQL 查询语句（来自 topology.metrics 定义）。
    """
    try:
        r = requests.get(
            f"{PROM_URL}/query",
            params={"query": promql},
            auth=PROM_AUTH,
            verify=False,
            timeout=15,
        )
        data = r.json()
        if data.get("status") != "success":
            return None
        result = data["data"]["result"]
        if not result:
            return None
        return float(result[0]["value"][1])
    except Exception:
        return None


# Function Calling 工具定义（节点4注入LLM，让LLM决定查哪条PromQL）
# 三定调：FC用于【节点内查询生成】，不用于节点间路由

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_prometheus",
            "description": (
                "查询 VictoriaMetrics 监控指标。输入 PromQL 返回当前数值（float）"
                "用于 RCA 指标分析节点查 topology.metrics 定义的指标"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "promql": {
                        "type": "string",
                        "description": (
                            "PromQL 查询语句，需带 instance 标签过滤，"
                            "如 'mysql_global_status_threads_running{instance=\"10.3.240.116:19211\"}'"
                        ),
                    }
                },
                "required": ["promql"],
            }
        }
    }
]
