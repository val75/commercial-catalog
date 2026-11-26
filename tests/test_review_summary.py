from __future__ import annotations

from pipeline import review_draft
from review.checks_json import checks_to_json
from review.decisions import decision_key, validate_decision
from review.summary import Badges, badges, what_was_quoted
from tests.quote_builders import cpu, drive, example_quote, gpu, item, memory, quote

NIC_ANSWER = {"kind": "answer", "count": "c4", "per_server": 1}
CORES = "items/0/components/0/cpu/physical_cores"


def prepared(draft):
    return draft.model_dump(mode="json"), checks_to_json(review_draft(draft))


def decide(draft, checks, *decisions):
    return {decision_key(d): validate_decision(draft, checks, d) for d in decisions}


def test_the_example_quote_reads_as_in_the_mockup():
    draft, checks = prepared(example_quote())
    decisions = decide(draft, checks, NIC_ANSWER)
    assert what_was_quoted(draft, checks, decisions) == "4 × Example SR-650 2U · 2 × Xeon Gold 6530 · 2 × L40S 48 GB · 1 TB DDR5"


def test_an_unanswered_count_shows_a_question_mark():
    draft, checks = prepared(quote(item(cpu(8, "unknown"), memory(None), gpu(2), servers=None)))
    assert what_was_quoted(draft, checks, {}) == "? × Example SR-650 2U · ? × Xeon Gold 6530 · 2 × L40S 48 GB · ? × 64 GB DDR5"


def test_an_answered_count_is_used():
    draft, checks = prepared(quote(item(cpu(8, "unknown"))))
    decisions = decide(draft, checks, {"kind": "answer", "count": "c0", "per_server": 2})
    assert what_was_quoted(draft, checks, decisions) == "4 × Example SR-650 2U · 2 × Xeon Gold 6530 · no GPU"


def test_a_server_without_gpus_says_no_gpu():
    draft, checks = prepared(quote(item(cpu(2), memory(16, capacity_gb=32), servers=10)))
    assert what_was_quoted(draft, checks, {}) == "10 × Example SR-650 2U · 2 × Xeon Gold 6530 · no GPU · 512 GB DDR5"


def test_loose_parts_never_say_no_gpu():
    draft, checks = prepared(quote(item(drive(3.84, 4), servers=1, with_chassis=False, manufacturer=None, model=None,
                                        description="Spare drives for an existing cluster, four of them")))
    assert what_was_quoted(draft, checks, {}) == "1 × Spare drives for an existing cluster, fo"


def test_memory_under_a_terabyte_is_in_gb():
    draft, checks = prepared(quote(item(cpu(2), memory(12), gpu(4))))
    assert what_was_quoted(draft, checks, {}).endswith(" · 768 GB DDR5")


def test_several_items_are_joined():
    draft, checks = prepared(quote(item(cpu(2), servers=2), item(cpu(1), servers=1, model="GX-880 8U")))
    assert what_was_quoted(draft, checks, {}) == (
        "2 × Example SR-650 2U · 2 × Xeon Gold 6530 · no GPU; 1 × Example GX-880 8U · 1 × Xeon Gold 6530 · no GPU"
    )


def test_badges_count_open_questions_undecided_guesses_and_changes():
    draft, checks = prepared(example_quote())
    assert badges(draft, checks, {}) == Badges(questions=1, guesses=2, changes=1, ready=False)
    assert badges(draft, checks, decide(draft, checks, NIC_ANSWER)).ready is True


def test_a_used_guess_is_no_longer_counted():
    draft, checks = prepared(example_quote())
    decisions = decide(draft, checks, {"kind": "use_guess", "path": CORES})
    assert badges(draft, checks, decisions).guesses == 1


def test_a_kept_original_is_no_longer_a_change():
    draft, checks = prepared(example_quote())
    decisions = decide(draft, checks, {"kind": "keep_original", "path": "items/0/components/3/storage/capacity"})
    assert badges(draft, checks, decisions).changes == 0


def test_a_draft_with_no_items_is_ready_with_an_empty_description():
    draft, checks = prepared(quote())
    assert what_was_quoted(draft, checks, {}) == ""
    assert badges(draft, checks, {}) == Badges(questions=0, guesses=0, changes=0, ready=True)

