from __future__ import annotations

import pytest

from extraction.schema import CpuComponent
from validation.cpu_properties import check_cpu_properties
from validation.properties import PropertyIssue


def _stated(value) -> dict:
    return {"value": value, "basis": "stated"}


def _cpu(**properties) -> CpuComponent:
    return CpuComponent.model_validate({"component_type": "cpu", "cpu": properties})


def _flagged(cpu: CpuComponent) -> list[tuple[PropertyIssue, str]]:
    return [(flag.issue, flag.property) for flag in check_cpu_properties(cpu)]


def test_a_consistent_cpu_has_no_flags():
    cpu = _cpu(
        manufacturer={"value": "AMD", "basis": "inferred", "reason": "Genoa is an AMD code name"},
        model=_stated("9654"),
        physical_cores=_stated(96),
        threads=_stated(192),
        base_clock_ghz=_stated(2.4),
        cache_mb=_stated(384),
        tdp_w=_stated(360),
    )
    assert check_cpu_properties(cpu) == []


def test_a_cpu_with_nothing_identified_has_no_flags():
    assert check_cpu_properties(_cpu()) == []


# --- inferred values must say why ------------------------------------------------


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_an_inferred_value_without_a_reason_is_flagged(reason):
    cpu = _cpu(manufacturer={"value": "AMD", "basis": "inferred", "reason": reason})
    assert _flagged(cpu) == [(PropertyIssue.INFERRED_WITHOUT_REASON, "manufacturer")]


def test_a_stated_value_needs_no_reason():
    assert check_cpu_properties(_cpu(manufacturer=_stated("AMD"))) == []


# --- threads are the cores, or twice the cores -----------------------------------


@pytest.mark.parametrize("threads", [32, 64])
def test_threads_equal_to_or_twice_the_cores_pass(threads):
    assert check_cpu_properties(_cpu(physical_cores=_stated(32), threads=_stated(threads))) == []


@pytest.mark.parametrize("threads", [16, 48, 128])
def test_other_thread_counts_are_flagged(threads):
    cpu = _cpu(physical_cores=_stated(32), threads=_stated(threads))
    assert _flagged(cpu) == [(PropertyIssue.THREADS_DONT_MATCH_CORES, "threads")]


def test_threads_alone_are_not_compared_with_anything():
    assert check_cpu_properties(_cpu(threads=_stated(48))) == []


# --- base clock in GHz -------------------------------------------------------------


@pytest.mark.parametrize("ghz", [1.0, 2.4, 6.0])
def test_a_base_clock_from_1_to_6_ghz_passes(ghz):
    assert check_cpu_properties(_cpu(base_clock_ghz=_stated(ghz))) == []


@pytest.mark.parametrize("ghz", [0.9, 6.1, 3300])
def test_a_base_clock_outside_1_to_6_ghz_is_flagged(ghz):
    # 3300 is the usual slip: MHz written where GHz was asked for.
    assert _flagged(_cpu(base_clock_ghz=_stated(ghz))) == [(PropertyIssue.CLOCK_OUT_OF_RANGE, "base_clock_ghz")]


# --- counts and sizes above zero ---------------------------------------------------


@pytest.mark.parametrize("prop", ["physical_cores", "threads", "cache_mb", "tdp_w"])
@pytest.mark.parametrize("value", [0, -1])
def test_a_count_or_size_of_zero_or_less_is_flagged(prop, value):
    assert _flagged(_cpu(**{prop: _stated(value)})) == [(PropertyIssue.NOT_ABOVE_ZERO, prop)]


def test_zero_cores_are_not_also_reported_as_a_thread_mismatch():
    cpu = _cpu(physical_cores=_stated(0), threads=_stated(64))
    assert _flagged(cpu) == [(PropertyIssue.NOT_ABOVE_ZERO, "physical_cores")]


# --- several problems at once ------------------------------------------------------


def test_every_problem_is_reported_and_every_flag_has_a_message():
    cpu = _cpu(
        product_family={"value": "EPYC", "basis": "inferred"},
        physical_cores=_stated(32),
        threads=_stated(48),
        base_clock_ghz=_stated(2400),
        tdp_w=_stated(0),
    )
    flags = check_cpu_properties(cpu)
    assert sorted((flag.issue.value, flag.property) for flag in flags) == [
        ("clock_out_of_range", "base_clock_ghz"),
        ("inferred_without_reason", "product_family"),
        ("not_above_zero", "tdp_w"),
        ("threads_dont_match_cores", "threads"),
    ]
    assert all(flag.message for flag in flags)
