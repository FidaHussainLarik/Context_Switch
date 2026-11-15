from dataclasses import dataclass
from math import isclose

from context_switch.domain.models import Process, SimulationResult
from context_switch.metrics.calculator import MetricsSummary, calculate_metrics
from context_switch.scheduling.base import Scheduler
from context_switch.scheduling.fcfs import FCFSScheduler
from context_switch.scheduling.priority import (
    PreemptivePriorityScheduler,
    PriorityScheduler,
)
from context_switch.scheduling.round_robin import RoundRobinScheduler
from context_switch.scheduling.sjf import SJFScheduler
from context_switch.scheduling.srtn import SRTNScheduler


@dataclass(frozen=True)
class ComparisonResult:
    results: dict[str, SimulationResult]
    metrics: dict[str, MetricsSummary]
    analysis: "ComparisonAnalysis"


@dataclass(frozen=True)
class ComparisonAnalysis:
    rankings: dict[str, dict[str, int]]
    overall_scores: dict[str, float]
    overall_winners: tuple[str, ...]
    metric_winners: dict[str, tuple[str, ...]]


_RANKED_METRICS = (
    "average_waiting_time",
    "average_turnaround_time",
    "average_weighted_turnaround_time",
)
_ALL_METRICS = (*_RANKED_METRICS, "cpu_utilization")


def analyze_metrics(metrics: dict[str, MetricsSummary]) -> ComparisonAnalysis:
    if not metrics:
        raise ValueError("At least one algorithm result is required.")

    rankings: dict[str, dict[str, int]] = {
        algorithm: {} for algorithm in metrics
    }
    metric_winners: dict[str, tuple[str, ...]] = {}
    for metric_name in _ALL_METRICS:
        values = {
            algorithm: getattr(summary, metric_name)
            for algorithm, summary in metrics.items()
        }
        higher_is_better = metric_name == "cpu_utilization"
        best_value = (
            max(values.values()) if higher_is_better else min(values.values())
        )
        metric_winners[metric_name] = tuple(
            algorithm
            for algorithm, value in values.items()
            if isclose(value, best_value, rel_tol=1e-9, abs_tol=1e-9)
        )
        for algorithm, value in values.items():
            better_count = sum(
                (
                    candidate > value
                    if higher_is_better
                    else candidate < value
                )
                and not isclose(
                    candidate,
                    value,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
                for candidate in values.values()
            )
            rankings[algorithm][metric_name] = better_count + 1

    overall_scores = {
        algorithm: sum(
            rankings[algorithm][metric_name] for metric_name in _RANKED_METRICS
        )
        / len(_RANKED_METRICS)
        for algorithm in metrics
    }
    lowest_score = min(overall_scores.values())
    score_winners = [
        algorithm
        for algorithm, score in overall_scores.items()
        if isclose(score, lowest_score, rel_tol=1e-9, abs_tol=1e-9)
    ]
    lowest_waiting = min(
        metrics[algorithm].average_waiting_time for algorithm in score_winners
    )
    waiting_winners = [
        algorithm
        for algorithm in score_winners
        if isclose(
            metrics[algorithm].average_waiting_time,
            lowest_waiting,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    ]
    lowest_turnaround = min(
        metrics[algorithm].average_turnaround_time for algorithm in waiting_winners
    )
    overall_winners = tuple(
        algorithm
        for algorithm in waiting_winners
        if isclose(
            metrics[algorithm].average_turnaround_time,
            lowest_turnaround,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    )

    return ComparisonAnalysis(
        rankings=rankings,
        overall_scores=overall_scores,
        overall_winners=overall_winners,
        metric_winners=metric_winners,
    )


def compare_processes(processes: list[Process], quantum: int) -> ComparisonResult:
    schedulers: list[Scheduler] = [
        FCFSScheduler(),
        SJFScheduler(),
        PriorityScheduler(),
        PreemptivePriorityScheduler(),
        RoundRobinScheduler(quantum),
        SRTNScheduler(),
    ]
    results: dict[str, SimulationResult] = {}
    metrics: dict[str, MetricsSummary] = {}

    for scheduler in schedulers:
        result = scheduler.run(processes)
        results[scheduler.name] = result
        metrics[scheduler.name] = calculate_metrics(result)

    return ComparisonResult(results, metrics, analyze_metrics(metrics))
