from context_switch.domain.models import Process
from context_switch.scheduling.fcfs import FCFSScheduler
from context_switch.scheduling.priority import PriorityScheduler
from context_switch.scheduling.priority import PreemptivePriorityScheduler
from context_switch.scheduling.round_robin import RoundRobinScheduler
from context_switch.scheduling.sjf import SJFScheduler
from context_switch.scheduling.srtn import SRTNScheduler


def process_map(result):
    return {process.process_id: process for process in result.processes}


def test_fcfs_handles_idle_time_and_arrival_order() -> None:
    result = FCFSScheduler().run(
        [Process("P1", 2, 3, 1), Process("P2", 0, 2, 1)]
    )

    assert [(segment.process_id, segment.start_time, segment.end_time) for segment in result.timeline] == [
        ("P2", 0, 2),
        ("P1", 2, 5),
    ]
    assert process_map(result)["P1"].completion_time == 5


def test_priority_is_non_preemptive_and_lower_number_has_priority() -> None:
    result = PriorityScheduler().run(
        [Process("P1", 0, 4, 2), Process("P2", 1, 1, 1)]
    )

    assert [segment.process_id for segment in result.timeline] == ["P1", "P2"]
    assert process_map(result)["P2"].completion_time == 5


def test_round_robin_requeues_unfinished_processes() -> None:
    result = RoundRobinScheduler(2).run(
        [Process("P1", 0, 5, 1), Process("P2", 0, 3, 1)]
    )

    assert [
        (segment.process_id, segment.start_time, segment.end_time)
        for segment in result.timeline
    ] == [
        ("P1", 0, 2),
        ("P2", 2, 4),
        ("P1", 4, 6),
        ("P2", 6, 7),
        ("P1", 7, 8),
    ]


def test_srtn_preempts_when_shorter_process_arrives() -> None:
    result = SRTNScheduler().run(
        [Process("P1", 0, 6, 1), Process("P2", 2, 2, 1)]
    )

    assert [
        (segment.process_id, segment.start_time, segment.end_time)
        for segment in result.timeline
    ] == [
        ("P1", 0, 2),
        ("P2", 2, 4),
        ("P1", 4, 8),
    ]


def test_sjf_does_not_preempt_and_uses_original_burst_time() -> None:
    result = SJFScheduler().run(
        [Process("P1", 0, 5, 1), Process("P2", 1, 2, 1)]
    )

    assert [segment.process_id for segment in result.timeline] == ["P1", "P2"]
    assert process_map(result)["P1"].completion_time == 5


def test_preemptive_priority_interrupts_only_for_strictly_higher_priority() -> None:
    result = PreemptivePriorityScheduler().run(
        [
            Process("P1", 0, 6, 2),
            Process("P2", 2, 2, 1),
            Process("P3", 3, 1, 2),
        ]
    )

    assert [
        (segment.process_id, segment.start_time, segment.end_time)
        for segment in result.timeline
    ] == [
        ("P1", 0, 2),
        ("P2", 2, 4),
        ("P1", 4, 8),
        ("P3", 8, 9),
    ]


def test_ties_use_arrival_time_then_process_id() -> None:
    result = SJFScheduler().run(
        [Process("P2", 0, 2, 1), Process("P1", 0, 2, 1)]
    )

    assert [segment.process_id for segment in result.timeline] == ["P1", "P2"]


def test_scheduler_does_not_mutate_input_processes() -> None:
    process = Process("P1", 0, 2, 1)

    FCFSScheduler().run([process])

    assert process.remaining_time == 2
    assert process.completion_time is None
