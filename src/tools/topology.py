from pathlib import Path
import yaml

# topology.yaml 在src/ 根，本文件在src/tools/，向上一级
TOPOLOGY_PATH = Path(__file__).parent.parent / "topology.yaml"


def load_topology() -> dict:
    """读 topology.yaml 返回完整拓扑 dict 。

    Returns:
        {"meta":..., "hosts":..., "services":...}
    """
    with open(TOPOLOGY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_service_by_instance(topology: dict, instance: str) -> dict | None:
    """按 instance 反查 service（节点3 核心逻辑）。

    告警带 instance 标签 -> 在 topology.services 里找 instance 匹配的 service。
    MYSQL/Redis 直接 match；ES 告警也带 instance（hw-agnet:19212）可命中。

    Args:
        topology: load_topology() 的返回值。
        instance: 告警的 instance 标签（host:port）。

    Returns:
        {"service_id":...,"service":{...}} 或 None。
    """
    for service_id, svc in topology.get("services", {}).items():
        if svc.get("instance") == instance:
            return {"service_id": service_id, "service": svc}
    return None
