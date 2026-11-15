import pytest

from context_switch.domain.exceptions import ValidationError
from context_switch.generation.random_process_generator import (
    RandomGenerationConfig,
    RandomProcessGenerator,
)


def test_generator_creates_processes_within_configured_ranges() -> None:
    config = RandomGenerationConfig(
        process_count=20,
        arrival_min=2,
        arrival_max=4,
        burst_min=3,
        burst_max=6,
        priority_min=1,
        priority_max=3,
        seed=7,
    )

    processes = RandomProcessGenerator().generate(config)

    assert len(processes) == 20
    assert len({process.process_id for process in processes}) == 20
    assert all(2 <= process.arrival_time <= 4 for process in processes)
    assert all(3 <= process.burst_time <= 6 for process in processes)
    assert all(1 <= process.priority <= 3 for process in processes)


def test_generator_avoids_existing_ids() -> None:
    config = RandomGenerationConfig(3, 0, 0, 1, 1, 1, 1)

    processes = RandomProcessGenerator().generate(config, existing_ids={"P1", "P3"})

    assert [process.process_id for process in processes] == ["P2", "P4", "P5"]


def test_generator_seed_is_reproducible() -> None:
    config = RandomGenerationConfig(3, 0, 5, 1, 5, 1, 3, seed=11)
    generator = RandomProcessGenerator()

    first = generator.generate(config)
    second = generator.generate(config)

    assert [
        (process.process_id, process.arrival_time, process.burst_time, process.priority)
        for process in first
    ] == [
        (process.process_id, process.arrival_time, process.burst_time, process.priority)
        for process in second
    ]


@pytest.mark.parametrize(
    "values",
    [
        (0, 0, 1, 1, 1, 1, 1),
        (1, -1, 1, 1, 1, 1, 1),
        (1, 0, 1, 0, 1, 1, 1),
        (1, 0, 1, 1, 1, 0, 1),
        (1, 2, 1, 1, 1, 1, 1),
        (1, 0, 1, 2, 1, 1, 1),
        (1, 0, 1, 1, 1, 2, 1),
    ],
)
def test_generator_rejects_invalid_configuration(
    values: tuple[int, ...],
) -> None:
    with pytest.raises(ValidationError):
        RandomGenerationConfig(*values)
