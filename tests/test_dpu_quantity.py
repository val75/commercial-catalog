from __future__ import annotations

from extraction.schema import QuoteItem
from validation.quantity import Issue, dpus_per_server


def _dpu_line(quantity=None, basis="unknown", **properties) -> dict:
    dpu = {name: {"value": value, "basis": "stated"} for name, value in properties.items()}
    return {"component_type": "dpu", "quantity": quantity, "quantity_basis": basis, "dpu": dpu}


def _server(*components, servers=4) -> QuoteItem:
    return QuoteItem.model_validate({"description": "Example Server", "quantity": servers, "components": list(components)})


def test_a_whole_order_count_of_dpus_is_divided_by_the_number_of_servers():
    # "DPU-...(x4)" under a line of 4 servers.
    check = dpus_per_server(_server(_dpu_line(quantity=4, basis="order_total"), servers=4))
    assert (check.per_server, check.calculated, check.flags) == (1, True, [])


def test_a_per_server_count_is_kept():
    check = dpus_per_server(_server(_dpu_line(quantity=2, basis="per_unit")))
    assert (check.per_server, check.flags) == (2, [])


def test_an_unknown_basis_is_asked():
    check = dpus_per_server(_server(_dpu_line(quantity=4)))
    assert Issue.UNKNOWN_BASIS in [flag.issue for flag in check.flags]


def test_two_crypto_variants_are_asked_not_added():
    check = dpus_per_server(
        _server(
            _dpu_line(quantity=1, basis="per_unit", model="DX-3 D3220", crypto="Crypto Enable"),
            _dpu_line(quantity=1, basis="per_unit", model="DX-3 D3220", crypto="Crypto Disabled"),
        )
    )
    assert check.per_server is None and check.flags


def test_an_item_without_a_dpu_has_nothing_to_check():
    nic = {"component_type": "nic", "quantity": 1, "nic": {"model": {"value": "Example 25GbE", "basis": "stated"}}}
    assert dpus_per_server(_server(nic)) is None
