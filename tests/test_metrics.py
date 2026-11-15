import pytest

from context_switch.domain.models import Process
from context_switch.metrics.calculator import calculate_metrics
from context_switch.scheduling.fcfs import FCFSScheduler


def test_metrics_calculate_process_and_average_values() -> None:
    result = FCFSScheduler().run(
        [Process("P1", 0, 3, 1), Process("P2", 5, 2, 1)]
    )

    summary = calculate_metrics(result)
    processes = {process.process_id: process for process in result.processes}

    assert processes["P1"].turnaround_time == 3
    assert processes["P1"].waiting_time == 0
    assert processes["P2"].turnaround_time == 2
    assert processes["P2"].waiting_time == 0
    assert summary.average_waiting_time == 0
    assert summary.average_turnaround_time == 2.5
    assert summary.cpu_utilization == pytest.approx(5 / 7 * 100)


def test_weighted_turnaround_time_is_calculated_per_process() -> None:
    result = FCFSScheduler().run([Process("P1", 0, 4, 1)])

    summary = calculate_metrics(result)

    assert result.processes[0].weighted_turnaround_time == 1
    assert summary.average_weighted_turnaround_time == 1


def test_metrics_use_authoritative_completion_times_for_preemptive_results() -> None:
    result = FCFSScheduler().run(
        [Process("P1", 0, 3, 1), Process("P2", 1, 2, 1)]
    )

    summary = calculate_metrics(result)
    processes = {process.process_id: process for process in result.processes}

    assert processes["P1"].completion_time == 3
    assert processes["P1"].turnaround_time == 3
    assert processes["P1"].waiting_time == 0
    assert processes["P1"].weighted_turnaround_time == 1
    assert processes["P2"].completion_time == 5
    assert processes["P2"].turnaround_time == 4
    assert processes["P2"].waiting_time == 2
    assert processes["P2"].weighted_turnaround_time == 2
    assert summary.average_turnaround_time == 3.5
    assert summary.average_waiting_time == 1
    assert summary.average_weighted_turnaround_time == 1.5
