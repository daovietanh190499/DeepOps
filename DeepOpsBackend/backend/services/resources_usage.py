"""Cluster resource allocation summary for end users.

This is "allocated" (requested resources) rather than real-time utilization.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from backend.services.cluster import get_directpv_drives
from backend.services.k8s_env import NAMESPACE


def _run_json(cmd: list[str], *, timeout: int = 60) -> dict | None:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0 or not (result.stdout or "").strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _cpu_to_cores(qty: str | None) -> float:
    s = str(qty or "").strip()
    if not s:
        return 0.0
    if s.endswith("m"):
        try:
            return float(s[:-1]) / 1000.0
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


_MEM_UNITS = {
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
    "Pi": 1024**5,
    "Ei": 1024**6,
    "K": 1000,
    "M": 1000**2,
    "G": 1000**3,
    "T": 1000**4,
    "P": 1000**5,
    "E": 1000**6,
}


def _mem_to_bytes(qty: str | None) -> int:
    s = str(qty or "").strip()
    if not s:
        return 0
    for unit, mult in _MEM_UNITS.items():
        if s.endswith(unit):
            try:
                return int(float(s[: -len(unit)]) * mult)
            except ValueError:
                return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _bytes_to_gib(n: int) -> float:
    return round((n or 0) / (1024**3), 2)


def _parse_directpv_size_like(text: str) -> int:
    """Parse strings like '930.96 GiB' / '1 TiB' from directpv output."""
    raw = (text or "").strip()
    if not raw:
        return 0
    parts = raw.split()
    if not parts:
        return 0
    try:
        value = float(parts[0])
    except ValueError:
        return 0
    unit = parts[1] if len(parts) > 1 else "GiB"
    unit = unit.replace("iB", "i").replace("B", "")  # GiB->Gi, TiB->Ti
    mult = _MEM_UNITS.get(unit) or _MEM_UNITS.get(unit + "i")
    if not mult:
        # Fallback: treat unknown as GiB.
        mult = 1024**3
    return int(value * mult)


def _sum_container_requests(container: dict) -> dict[str, float]:
    resources = container.get("resources") or {}
    req = resources.get("requests") or {}
    out: dict[str, float] = {
        "cpu_cores": _cpu_to_cores(req.get("cpu")),
        "mem_bytes": float(_mem_to_bytes(req.get("memory"))),
        "gpu_count": float(req.get("nvidia.com/gpu") or 0),
        "gpu_mem_bytes": float(_mem_to_bytes(req.get("nvidia.com/gpumem"))),
    }
    return out


def get_cluster_resources_usage() -> dict:
    nodes_data = _run_json(["kubectl", "get", "nodes", "-o", "json"])
    pods_data = _run_json(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            NAMESPACE,
            "-l",
            "app.kubernetes.io/name=codehub",
            "-o",
            "json",
        ],
        timeout=90,
    )

    if not nodes_data:
        return {
            "ok": False,
            "error": "failed to list nodes",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [],
        }

    nodes: dict[str, dict] = {}
    for item in nodes_data.get("items") or []:
        meta = item.get("metadata") or {}
        status = item.get("status") or {}
        alloc = status.get("allocatable") or {}
        name = meta.get("name", "")
        if not name:
            continue
        nodes[name] = {
            "name": name,
            "cpu_total": _cpu_to_cores(alloc.get("cpu")),
            "ram_total_gib": _bytes_to_gib(_mem_to_bytes(alloc.get("memory"))),
            "gpu_total": int(float(alloc.get("nvidia.com/gpu") or 0)),
            "gpu_mem_total_gib": _bytes_to_gib(_mem_to_bytes(alloc.get("nvidia.com/gpumem"))),
            "cpu_allocated": 0.0,
            "ram_allocated_gib": 0.0,
            "gpu_allocated": 0,
            "gpu_mem_allocated_gib": 0.0,
            "drive_total_gib": 0.0,
            "drive_allocated_gib": 0.0,
        }

    if pods_data:
        for pod in pods_data.get("items") or []:
            spec = pod.get("spec") or {}
            node_name = (spec.get("nodeName") or "").strip()
            if not node_name or node_name not in nodes:
                continue
            for c in spec.get("containers") or []:
                req = _sum_container_requests(c)
                nodes[node_name]["cpu_allocated"] += float(req["cpu_cores"])
                nodes[node_name]["ram_allocated_gib"] += _bytes_to_gib(int(req["mem_bytes"]))
                nodes[node_name]["gpu_allocated"] += int(req["gpu_count"])
                nodes[node_name]["gpu_mem_allocated_gib"] += _bytes_to_gib(int(req["gpu_mem_bytes"]))

    dpv = get_directpv_drives()
    if dpv.get("ok"):
        for drive in dpv.get("drives") or []:
            node = (drive.get("node") or "").strip()
            if not node or node not in nodes:
                continue
            size_b = _parse_directpv_size_like(drive.get("size") or "")
            alloc_b = _parse_directpv_size_like(drive.get("allocated") or "")
            nodes[node]["drive_total_gib"] += _bytes_to_gib(size_b)
            nodes[node]["drive_allocated_gib"] += _bytes_to_gib(alloc_b)

    out_nodes = sorted(nodes.values(), key=lambda n: n.get("name") or "")
    return {
        "ok": True,
        "error": "",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "nodes": out_nodes,
    }

