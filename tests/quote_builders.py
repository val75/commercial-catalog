"""Invented quote drafts for the review tests. No real vendor, customer or part data."""

from __future__ import annotations

from typing import Any

from extraction.schema import QuoteDraft


def stated(value: Any) -> dict:
    return {"value": value, "basis": "stated"}


def inferred(value: Any, reason: str | None = "From the model name") -> dict:
    return {"value": value, "basis": "inferred", "reason": reason}


def cpu(quantity: int | None = 2, basis: str = "per_unit", model: str = "Xeon Gold 6530", **properties) -> dict:
    return {
        "component_type": "cpu",
        "quantity": quantity,
        "quantity_basis": basis,
        "cpu": {"manufacturer": stated("Intel"), "model": stated(model), **properties},
    }


def memory(quantity: int | None = 16, basis: str = "per_unit", capacity_gb: int = 64, memory_type: str = "DDR5",
           **properties) -> dict:
    return {
        "component_type": "memory",
        "quantity": quantity,
        "quantity_basis": basis,
        "memory": {"capacity_gb": stated(capacity_gb), "memory_type": stated(memory_type), **properties},
    }


def gpu(quantity: int | None = 2, basis: str = "per_unit", model: str = "L40S", memory_gb: int = 48) -> dict:
    return {
        "component_type": "gpu",
        "quantity": quantity,
        "quantity_basis": basis,
        "gpu": {
            "manufacturer": stated("NVIDIA"),
            "model": stated(model),
            "memory_capacity_gb": {"value": memory_gb, "basis": "stated"},
        },
    }


def drive(capacity_tb: float = 3.84, quantity: int | None = 2, basis: str = "per_unit") -> dict:
    return {
        "component_type": "storage",
        "quantity": quantity,
        "quantity_basis": basis,
        "storage": {
            "storage_type": stated("SSD"),
            "capacity": {"value": capacity_tb, "unit": "TB", "basis": "stated"},
        },
    }


def nic(quantity: int | None = 1, basis: str = "per_unit", model: str = "ConnectX-7") -> dict:
    return {"component_type": "nic", "quantity": quantity, "quantity_basis": basis, "nic": {"model": stated(model)}}


def raid(quantity: int | None = 1, basis: str = "per_unit", model: str = "RC-9000") -> dict:
    return {
        "component_type": "raid_controller",
        "quantity": quantity,
        "quantity_basis": basis,
        "raid_controller": {"model": stated(model)},
    }


def chassis(rack_height: str = "2U", **properties) -> dict:
    return {"rack_height": stated(rack_height), **properties}


def item(*components: dict, servers: int | None = 4, with_chassis: bool = True, **fields) -> dict:
    data = {
        "description": "Example SR-650 2U server",
        "manufacturer": "Example",
        "model": "SR-650 2U",
        "quantity": servers,
        "components": list(components),
        **fields,
    }
    if with_chassis and "chassis" not in fields:
        data["chassis"] = chassis()
    return data


def quote(*items: dict, **fields) -> QuoteDraft:
    return QuoteDraft.model_validate({"quote_number": "Q-1", "vendor_name": "Example Systems", "currency": "USD",
                                      "items": list(items), **fields})


def example_quote() -> QuoteDraft:
    """The invented quote from the mockups: 4 servers, one network adapter question."""
    return quote(
        item(
            cpu(8, "order_total", physical_cores=inferred(32), threads=inferred(64)),
            memory(64, "order_total"),
            gpu(8, "order_total"),
            drive(3.8, 8, "order_total"),
            nic(4, "unknown"),
            unit_price=24500,
            extended_price=98000,
        ),
        quote_number="Q-48210",
        total=98000,
    )
