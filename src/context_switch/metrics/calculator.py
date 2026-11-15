from dataclasses import dataclass

from context_switch.domain.exceptions import ValidationError
from context_switch.domain.models import Process, SimulationResult


@dataclass(frozen=True)
class MetricsSummary:
    average_waiting_time: float
    average_turnaround_time: float
    average_weighted_turnaround_time: float
    cpu_utilization: float


def calculate_metrics(result: SimulationResult) -> MetricsSummary:
    if not result.processes or not result.timeline:
        raise ValidationError("A completed simulation is required.")

    for process in result.processes:
        if process.completion_time is None:
            raise ValidationError("All processes must be complete before calculating metrics.")
        process.turnaround_time = process.completion_time - process.arrival_time
        process.waiting_time = process.turnaround_time - process.burst_time
        process.weighted_turnaround_time = process.turnaround_time / process.burst_time

    process_count = len(result.processes)
    busy_time = sum(
        segment.end_time - segment.start_time
        for segment in result.timeline
        if segment.process_id is not None
    )
    elapsed_time = result.timeline[-1].end_time

    return MetricsSummary(
        average_waiting_time=sum(
            process.waiting_time for process in result.processes
        )
        / process_count,
        average_turnaround_time=sum(
            process.turnaround_time for process in result.processes
        )
        / process_count,
        average_weighted_turnaround_time=sum(
            process.weighted_turnaround_time for process in result.processes
        )
        / process_count,
        cpu_utilization=(busy_time / elapsed_time * 100) if elapsed_time else 0.0,
    )
