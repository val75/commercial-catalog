from __future__ import annotations

import json

from pipeline import review_draft
from review.checks_json import checks_to_json
from tests.quote_builders import cpu, drive, inferred, item, memory, quote, raid
from validation.properties import PropertyIssue


def test_two_lines_sharing_a_count_share_its_id():
    result = checks_to_json(review_draft(quote(item(raid(1), raid(1)))))
    first, second = result["items"][0]["components"]
    assert first["count"] == second["count"] == "c0"
    assert len(result["counts"]) == 1
    assert result["counts"]["c0"]["per_server"] is None


def test_separate_counts_get_separate_ids():
    result = checks_to_json(review_draft(quote(item(cpu(2), memory(16)))))
    assert [component["count"] for component in result["items"][0]["components"]] == ["c0", "c1"]
    assert result["counts"]["c0"]["per_server"] == 2
    assert result["counts"]["c1"]["per_server"] == 16


def test_a_standard_ssd_size_is_kept_as_a_proposal():
    result = checks_to_json(review_draft(quote(item(cpu(2), drive(3.8)))))
    capacity = result["items"][0]["components"][1]["capacity"]
    assert capacity["value"] == 3.84
    assert capacity["unit"] == "TB"
    assert capacity["automatic"] is True
    assert capacity["flags"] == []
    assert result["items"][0]["components"][0]["capacity"] is None


def test_flags_carry_their_kind_issue_and_property():
    result = checks_to_json(review_draft(quote(item(cpu(2, physical_cores=inferred(32, reason=None))))))
    flags = result["items"][0]["components"][0]["flags"]
    flag = next(flag for flag in flags if flag["property"] == "physical_cores")
    assert flag["kind"] == "PropertyIssue"
    assert flag["issue"] == PropertyIssue.INFERRED_WITHOUT_REASON.value
    assert "physical cores" in flag["message"]


def test_the_result_is_plain_json():
    result = checks_to_json(review_draft(quote(item(cpu(8, "order_total"), raid(1), raid(1), drive(4.0)))))
    assert json.loads(json.dumps(result)) == result
