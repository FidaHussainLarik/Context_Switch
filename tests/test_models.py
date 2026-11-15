import pytest

from context_switch.domain.exceptions import ValidationError
from context_switch.domain.models import Process, TimelineSegment, validate_processes


def test_process_initializes_remaining_time() -> None:
    process = Process("P1", 2, 5, 1)

    assert process.remaining_time == 5
    assert process.completion_time is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("process_id", ""),
        ("arrival_time", -1),
        ("burst_time", 0),
    ],
)
def test_process_rejects_invalid_values(field: str, value: object) -> None:
    values = {
        "process_id": "P1",
        "arrival_time": 0,
        "burst_time": 1,
        "priority": 1,
    }
    values[field] = value

    with pytest.raises(ValidationError):
        Process(**values)


def test_reset_runtime_restores_initial_state() -> None:
    process = Process("P1", 0, 4, 1)
    process.remaining_time = 1
    process.completion_time = 5
    process.waiting_time = 1

    process.reset_runtime()

    assert process.remaining_time == 4
    assert process.completion_time is None
    assert process.waiting_time is None


def test_processes_require_unique_ids() -> None:
    processes = [Process("P1", 0, 1, 1), Process("P1", 1, 1, 2)]

    with pytest.raises(ValidationError):
        validate_processes(processes)


def test_timeline_segment_requires_positive_duration() -> None:
    with pytest.raises(ValidationError):
        TimelineSegment(2, 2, "P1")


def test_numeric_process_ids_remain_strings() -> None:
    process = Process("1", 0, 1, 1)

    assert process.process_id == "1"
