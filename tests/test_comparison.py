from context_switch.domain.models import Process
from context_switch.metrics.calculator import MetricsSummary
from context_switch.simulation.comparison import analyze_metrics, compare_processes


def test_comparison_runs_all_algorithms_from_same_input() -> None:
    processes = [
        Process("P1", 0, 5, 2),
        Process("P2", 1, 2, 1),
        Process("P3", 2, 1, 3),
    ]

    comparison = compare_processes(processes, quantum=2)

    assert set(comparison.results) == {
        "FCFS",
        "SJF",
        "Priority",
        "Priority (Preemptive)",
        "Round Robin",
        "SRTN",
    }
    assert set(comparison.metrics) == set(comparison.results)
    assert comparison.analysis.overall_winners
    assert set(comparison.analysis.metric_winners) == {
        "average_waiting_time",
        "average_turnaround_time",
        "average_weighted_turnaround_time",
        "cpu_utilization",
    }
    assert all(
        process.completion_time is not None
        for result in comparison.results.values()
        for process in result.processes
    )
    assert all(process.completion_time is None for process in processes)


def test_comparison_produces_independent_process_results() -> None:
    comparison = compare_processes([Process("P1", 0, 4, 1)], quantum=1)

    fcfs_process = comparison.results["FCFS"].processes[0]
    round_robin_process = comparison.results["Round Robin"].processes[0]
    round_robin_process.waiting_time = 99

    assert fcfs_process.waiting_time != 99


def test_analysis_ranks_metrics_and_finds_metric_winners() -> None:
    metrics = {
        "A": MetricsSummary(1, 2, 1.0, 80),
        "B": MetricsSummary(2, 3, 1.5, 90),
        "C": MetricsSummary(3, 4, 2.0, 70),
    }

    analysis = analyze_metrics(metrics)

    assert analysis.rankings["A"]["average_waiting_time"] == 1
    assert analysis.rankings["A"]["average_turnaround_time"] == 1
    assert analysis.metric_winners["cpu_utilization"] == ("B",)
    assert analysis.overall_winners == ("A",)


def test_analysis_reports_joint_winner_after_tie_breakers() -> None:
    metrics = {
        "A": MetricsSummary(1, 2, 1, 80),
        "B": MetricsSummary(1, 2, 1, 80),
    }

    analysis = analyze_metrics(metrics)

    assert analysis.overall_winners == ("A", "B")
