from collections import deque

from context_switch.domain.exceptions import ValidationError
from context_switch.domain.models import Process, SimulationResult
from context_switch.scheduling.base import Scheduler


class RoundRobinScheduler(Scheduler):
    name = "Round Robin"

    def __init__(self, quantum: int) -> None:
        if quantum <= 0:
            raise ValidationError("Round Robin quantum must be greater than zero.")
        self.quantum = quantum

    def _run(self, processes: list[Process]) -> SimulationResult:
        timeline = []
        ready_queue = deque()
        ordered = sorted(
            processes,
            key=lambda item: (item.arrival_time, item.process_id),
        )
        next_index = 0
        current_time = 0
        completed = 0

        while completed < len(processes):
            while next_index < len(ordered) and ordered[next_index].arrival_time <= current_time:
                ready_queue.append(ordered[next_index])
                next_index += 1

            if not ready_queue:
                next_arrival = ordered[next_index].arrival_time
                self.add_segment(timeline, current_time, next_arrival, None)
                current_time = next_arrival
                continue

            process = ready_queue.popleft()
            start_time = current_time
            duration = min(self.quantum, process.remaining_time)
            current_time += duration
            process.remaining_time -= duration
            self.add_segment(timeline, start_time, current_time, process.process_id)

            while next_index < len(ordered) and ordered[next_index].arrival_time <= current_time:
                ready_queue.append(ordered[next_index])
                next_index += 1

            if process.remaining_time:
                ready_queue.append(process)
            else:
                process.completion_time = current_time
                completed += 1

        return self.result(processes, timeline)
