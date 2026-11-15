from context_switch.domain.models import Process, SimulationResult
from context_switch.scheduling.base import Scheduler


class FCFSScheduler(Scheduler):
    name = "FCFS"

    def _run(self, processes: list[Process]) -> SimulationResult:
        ordered = sorted(
            processes,
            key=lambda item: (item.arrival_time, item.process_id),
        )
        timeline = []
        current_time = 0

        for process in ordered:
            if current_time < process.arrival_time:
                self.add_segment(timeline, current_time, process.arrival_time, None)
                current_time = process.arrival_time
            start_time = current_time
            current_time += process.remaining_time
            process.remaining_time = 0
            process.completion_time = current_time
            self.add_segment(timeline, start_time, current_time, process.process_id)

        return self.result(processes, timeline)
