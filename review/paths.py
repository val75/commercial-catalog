"""Finding a draft's properties by path, such as items/0/components/2/cpu/physical_cores.

A property is a dict with a "basis" key (stated or inferred). They sit under each
component's typed properties and under each item's chassis.
"""

from __future__ import annotations

from typing import Any

TYPED_PROPERTIES = ("cpu", "memory", "gpu", "storage", "nic", "dpu", "psu", "raid_controller")


def property_paths(draft: dict) -> list[str]:
    """Every property, in document order: each item's chassis, then its components."""
    paths = []
    for i, item in enumerate(draft.get("items") or []):
        paths += _properties(item.get("chassis"), f"items/{i}/chassis")
        for j, component in enumerate(item.get("components") or []):
            kind = component.get("component_type")
            if kind in TYPED_PROPERTIES:
                paths += _properties(component.get(kind), f"items/{i}/components/{j}/{kind}")
    return paths


def inferred_paths(draft: dict) -> list[str]:
    return [path for path in property_paths(draft) if get_at(draft, path)["basis"] == "inferred"]


def _properties(properties: dict | None, prefix: str) -> list[str]:
    if not properties:
        return []
    return [f"{prefix}/{name}" for name, value in properties.items() if isinstance(value, dict) and "basis" in value]


def get_at(data: dict, path: str) -> Any:
    node: Any = data
    for part in path.split("/"):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def set_at(data: dict, path: str, value: Any) -> None:
    *parents, last = path.split("/")
    node = get_at(data, "/".join(parents)) if parents else data
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
