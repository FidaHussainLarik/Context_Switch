from context_switch.domain.models import Process, SimulationResult
from context_switch.scheduling.base import Scheduler


class PriorityScheduler(Scheduler):
    name = "Priority"

    def _run(self, processes: list[Process]) -> SimulationResult:
        timeline = []
        current_time = 0
        completed = 0
        while completed < len(processes):
            ready = [
                process
                for process in processes
                if process.completion_time is None
                and process.arrival_time <= current_time
            ]
            if not ready:
                next_arrival = min(
                    process.arrival_time
                    for process in processes
                    if process.completion_time is None
                )
                self.add_segment(timeline, current_time, next_arrival, None)
                current_time = next_arrival
                continue

            process = min(
                ready,
                key=lambda item: (
                    item.priority,
                    item.arrival_time,
                    item.process_id,
                ),
            )
            start_time = current_time
            current_time += process.remaining_time
            process.remaining_time = 0
            process.completion_time = current_time
            self.add_segment(timeline, start_time, current_time, process.process_id)
            completed += 1

        return self.result(processes, timeline)


class PreemptivePriorityScheduler(Scheduler):
    name = "Priority (Preemptive)"

    def _run(self, processes: list[Process]) -> SimulationResult:
        timeline = []
        current_time = 0
        completed = 0

        while completed < len(processes):
            ready = [
                process
                for process in processes
                if process.completion_time is None
                and process.arrival_time <= current_time
                and process.remaining_time > 0
            ]
            if not ready:
                next_arrival = min(
                    process.arrival_time
                    for process in processes
                    if process.completion_time is None
                )
                self.add_segment(timeline, current_time, next_arrival, None)
                current_time = next_arrival
                continue

            process = min(
                ready,
                key=lambda item: (
                    item.priority,
                    item.arrival_time,
                    item.process_id,
                ),
            )
            next_higher_priority_arrival = min(
                (
                    item.arrival_time
                    for item in processes
                    if item.completion_time is None
                    and item.arrival_time > current_time
                    and item.priority < process.priority
                ),
                default=None,
            )
            completion_time = current_time + process.remaining_time
            end_time = (
                min(completion_time, next_higher_priority_arrival)
                if next_higher_priority_arrival is not None
                else completion_time
            )
            process.remaining_time -= end_time - current_time
            self.add_segment(timeline, current_time, end_time, process.process_id)
            current_time = end_time

            if process.remaining_time == 0:
                process.completion_time = current_time
                completed += 1

        return self.result(processes, timeline)
