from dataclasses import dataclass, field

from .exceptions import ValidationError


@dataclass
class Process:
    process_id: str
    arrival_time: int
    burst_time: int
    priority: int
    remaining_time: int = field(init=False)
    completion_time: int | None = None
    waiting_time: int | None = None
    turnaround_time: int | None = None
    weighted_turnaround_time: float | None = None

    def __post_init__(self) -> None:
        if not self.process_id.strip():
            raise ValidationError("Process ID must not be empty.")
        if self.arrival_time < 0:
            raise ValidationError("Arrival time must be non-negative.")
        if self.burst_time <= 0:
            raise ValidationError("Burst time must be greater than zero.")
        self.remaining_time = self.burst_time

    def reset_runtime(self) -> None:
        self.remaining_time = self.burst_time
        self.completion_time = None
        self.waiting_time = None
        self.turnaround_time = None
        self.weighted_turnaround_time = None


@dataclass(frozen=True)
class TimelineSegment:
    start_time: int
    end_time: int
    process_id: str | None

    def __post_init__(self) -> None:
        if self.start_time < 0:
            raise ValidationError("Segment start time must be non-negative.")
        if self.end_time <= self.start_time:
            raise ValidationError("Segment end time must be greater than start time.")


@dataclass
class SimulationResult:
    algorithm: str
    processes: list[Process]
    timeline: list[TimelineSegment]


def validate_processes(processes: list[Process]) -> None:
    if not processes:
        raise ValidationError("At least one process is required.")
    process_ids = [process.process_id for process in processes]
    if len(process_ids) != len(set(process_ids)):
        raise ValidationError("Process IDs must be unique.")
