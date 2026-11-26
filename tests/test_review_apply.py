from __future__ import annotations

import copy

import pytest

from pipeline import review_draft
from review.apply import QuoteNotReady, apply_decisions
from review.checks_json import checks_to_json
from review.decisions import decision_key, open_questions, validate_decision
from review.paths import get_at, inferred_paths, property_paths
from tests.quote_builders import cpu, drive, inferred, item, nic, quote, raid

CORES = "items/0/components/0/cpu/physical_cores"


def prepared(draft):
    return draft.model_dump(mode="json"), checks_to_json(review_draft(draft))


def decide(draft: dict, checks: dict, *decisions: dict) -> dict:
    return {decision_key(d): validate_decision(draft, checks, d) for d in decisions}


def guessing_cpu():
    return prepared(quote(item(cpu(2, physical_cores=inferred(32)))))


def test_property_paths_cover_components_and_the_chassis():
    draft, _ = prepared(quote(item(cpu(2, physical_cores=inferred(32)), drive(3.84))))
    assert property_paths(draft) == [
        "items/0/chassis/rack_height",
        "items/0/components/0/cpu/manufacturer",
        "items/0/components/0/cpu/model",
        CORES,
        "items/0/components/1/storage/storage_type",
        "items/0/components/1/storage/capacity",
    ]
    assert inferred_paths(draft) == [CORES]
    assert get_at(draft, CORES)["value"] == 32


def test_an_unused_guess_is_left_out():
    draft, checks = guessing_cpu()
    assert get_at(apply_decisions(draft, checks, {}), CORES) is None


def test_a_used_guess_is_kept_and_marked():
    draft, checks = guessing_cpu()
    result = apply_decisions(draft, checks, decide(draft, checks, {"kind": "use_guess", "path": CORES}))
    assert get_at(result, CORES) | {} == {
        "value": 32, "basis": "inferred", "reason": "From the model name", "source": "guess_used"
    }


def test_a_typed_value_replaces_the_guess():
    draft, checks = guessing_cpu()
    decisions = decide(draft, checks, {"kind": "use_guess", "path": CORES}, {"kind": "set_value", "path": CORES, "value": 28})
    assert len(decisions) == 1  # the later decision on the property replaced the first
    cores = get_at(apply_decisions(draft, checks, decisions), CORES)
    assert cores == {"value": 28, "basis": "stated", "reason": None, "source": "reviewer"}


def test_a_typed_value_is_checked_against_the_property():
    draft, checks = guessing_cpu()
    assert validate_decision(draft, checks, {"kind": "set_value", "path": CORES, "value": "28"})["value"] == 28
    with pytest.raises(ValueError):
        validate_decision(draft, checks, {"kind": "set_value", "path": CORES, "value": "many"})


def test_a_correction_can_change_a_stated_value_and_its_basis():
    draft, checks = guessing_cpu()
    path = "items/0/components/0/cpu/model"
    decisions = decide(draft, checks, {"kind": "set_value", "path": path, "value": "Xeon Gold 6538", "basis": "inferred"})
    model = get_at(apply_decisions(draft, checks, decisions), path)
    assert (model["value"], model["basis"], model["source"]) == ("Xeon Gold 6538", "inferred", "reviewer")
    assert get_at(apply_decisions(draft, checks, {}), "items/0/components/0/cpu/manufacturer")["source"] == "quote"


def test_a_value_set_to_nothing_removes_the_property():
    draft, checks = guessing_cpu()
    path = "items/0/components/0/cpu/model"
    decisions = decide(draft, checks, {"kind": "set_value", "path": path, "value": None})
    assert get_at(apply_decisions(draft, checks, decisions), path) is None


def test_the_standard_ssd_size_is_applied_unless_kept():
    draft, checks = prepared(quote(item(cpu(2), drive(3.8))))
    path = "items/0/components/1/storage/capacity"
    changed = get_at(apply_decisions(draft, checks, {}), path)
    assert (changed["value"], changed["unit"], changed["source"], changed["as_written"]) == (3.84, "TB", "standard_size", "3.8 TB")

    kept = get_at(apply_decisions(draft, checks, decide(draft, checks, {"kind": "keep_original", "path": path})), path)
    assert (kept["value"], kept["source"]) == (3.8, "quote")


def test_counts_become_quantity_per_server():
    draft, checks = prepared(quote(item(cpu(8, "order_total"), raid(1), raid(1))))
    assert open_questions(checks, {}) == ["c1"]
    result = apply_decisions(draft, checks, decide(draft, checks, {"kind": "answer", "count": "c1", "per_server": 1}))
    assert [c["quantity_per_server"] for c in result["items"][0]["components"]] == [2, 1, 1]


def test_an_open_question_blocks():
    draft, checks = prepared(quote(item(nic(4, "unknown"))))
    with pytest.raises(QuoteNotReady) as raised:
        apply_decisions(draft, checks, {})
    assert raised.value.questions == ["c0"]


def test_open_questions_lists_unanswered_counts_only():
    draft, checks = prepared(quote(item(cpu(2), nic(4, "unknown"), raid(None))))
    assert open_questions(checks, {}) == ["c1", "c2"]
    answered = decide(draft, checks, {"kind": "answer", "count": "c1", "per_server": 4})
    assert open_questions(checks, answered) == ["c2"]


@pytest.mark.parametrize(
    "decision",
    [
        {"kind": "use_guess", "path": "items/0/components/9/cpu/physical_cores"},
        {"kind": "set_value", "path": "items/0/components/0/cpu/nonsense", "value": 1},
        {"kind": "answer", "count": "c9", "per_server": 1},
        {"kind": "answer", "count": "c0", "per_server": 1},  # c0 is already counted, not a question
        {"kind": "use_guess", "path": "items/0/components/0/cpu/model"},  # stated, not a guess
        {"kind": "answer", "count": "c1", "per_server": 0},
        {"kind": "answer", "count": "c1", "per_server": True},
        {"kind": "keep_original", "path": "items/0/components/2/storage/capacity"},  # 3.84 TB: no change
        {"kind": "set_value", "path": CORES, "value": 28, "basis": "maybe"},
        {"kind": "guess"},
    ],
)
def test_decisions_about_things_that_dont_exist_are_refused(decision):
    draft, checks = prepared(quote(item(cpu(2, physical_cores=inferred(32)), nic(4, "unknown"), drive(3.84))))
    with pytest.raises(ValueError):
        validate_decision(draft, checks, decision)


def test_applying_never_changes_the_draft_it_was_given():
    draft, checks = prepared(quote(item(cpu(8, "order_total", physical_cores=inferred(32)), drive(3.8))))
    before = copy.deepcopy((draft, checks))
    apply_decisions(draft, checks, decide(draft, checks, {"kind": "set_value", "path": CORES, "value": 28}))
    assert (draft, checks) == before
