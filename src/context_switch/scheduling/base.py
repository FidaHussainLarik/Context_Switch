from abc import ABC, abstractmethod

from context_switch.domain.models import (
    Process,
    SimulationResult,
    TimelineSegment,
    validate_processes,
)


class Scheduler(ABC):
    name: str

    def run(self, processes: list[Process]) -> SimulationResult:
        validate_processes(processes)
        process_copies = [
            Process(
                process.process_id,
                process.arrival_time,
                process.burst_time,
                process.priority,
            )
            for process in processes
        ]
        return self._run(process_copies)

    @abstractmethod
    def _run(self, processes: list[Process]) -> SimulationResult:
        raise NotImplementedError

    @staticmethod
    def add_segment(
        timeline: list[TimelineSegment],
        start_time: int,
        end_time: int,
        process_id: str | None,
    ) -> None:
        if timeline and timeline[-1].process_id == process_id:
            previous = timeline.pop()
            timeline.append(TimelineSegment(previous.start_time, end_time, process_id))
            return
        timeline.append(TimelineSegment(start_time, end_time, process_id))

    def result(
        self,
        processes: list[Process],
        timeline: list[TimelineSegment],
    ) -> SimulationResult:
        return SimulationResult(self.name, processes, timeline)
