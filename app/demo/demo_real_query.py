import os

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv()

PROM = os.environ["PROM_URL"].rstrip("/")


def query_prometheus(promql: str) -> str:
    r = requests.get(
        f"{PROM}/query",
        params={"query": promql},
        auth=(os.environ["PROM_USER"], os.environ["PROM_PASS"]),
        verify=False,
        timeout=15
    )

    return str(r.json()["data"]["result"])


print("Redis 内存:", query_prometheus("redis_memory_used_bytes")[:120])
print("MySQL 连接数:", query_prometheus("mysql_global_status_threads_connected")[:120])
print("ES 堆内存:", query_prometheus("elasticsearch_jvm_memory_userd_bytes")[:120])
print("主机可用内存:", query_prometheus("node_memory_MemAvailable_bytes")[:120])
