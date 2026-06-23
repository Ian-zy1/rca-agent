"""
探测真实 Prometheus 的标签命名，供 D2 写 topology.yaml 参考。
用法：
  1. 在 app/.env 加一行：PROM_URL=http://你的prometheus地址:9090
  2. python app/demo/demo_probe_prom.py
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()
PROM = os.environ.get("PROM_URL", "http://localhost:9090").rstrip("/")


def get(path, params=None):
    r = requests.get(f"{PROM}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])


def distinct_labels(series_list, keys):
    found = {k: set() for k in keys}
    for s in series_list:
        for k in keys:
            if k in s:
                found[k].add(str(s[k])[:40])
    return {k: sorted(v)[:15] for k, v in found.items()}


print(f"=== 连接 {PROM} ===\n")

print("【1】所有 label key（看有没有 service/job/container/pod/namespace 这些）")
try:
    print(" ", get("/api/v1/labels"))
except Exception as e:
    print("  ❌", repr(e)[:150])

print("\n【2】up 指标 —— service/job/instance 怎么命名")
try:
    s = get("/api/v1/series", {"match[]": "up"})
    print(f"  共 {len(s)} 条 up series")
    print(" ", distinct_labels(s, ["job", "instance", "service", "namespace"]))
except Exception as e:
    print("  ❌", repr(e)[:150])

print("\n【3】container_memory_usage_bytes —— 容器/pod/namespace 怎么命名")
try:
    s = get("/api/v1/series", {"match[]": "container_memory_usage_bytes"})
    print(f"  共 {len(s)} 条容器内存 series")
    print(" ", distinct_labels(s, ["container", "pod", "namespace", "image"]))
except Exception as e:
    print("  ❌", repr(e)[:150])

print("\n【4】node 指标 —— 节点怎么命名")
for metric in ["node_uname_info", "node_cpu_seconds_total"]:
    try:
        s = get("/api/v1/series", {"match[]": metric})
        print(f"  {metric}: {len(s)} 条")
        print("   ", distinct_labels(s, ["instance", "nodename", "node"]))
    except Exception as e:
        print(f"  {metric}: ❌", repr(e)[:100])

print("\n【5】搜 order/payment 等业务服务名（看真实标签里有没有这些服务）")
try:
    names = get("/api/v1/label/__name__/values")
    hints = [n for n in names if any(k in n.lower() for k in ["order", "payment", "http", "request"])]
    print(f"  相关指标名（前15）: {hints[:15]}")
except Exception as e:
    print("  ❌", repr(e)[:150])
