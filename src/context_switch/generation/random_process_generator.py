from dataclasses import dataclass
import random
from collections.abc import Iterable

from context_switch.domain.exceptions import ValidationError
from context_switch.domain.models import Process


@dataclass(frozen=True)
class RandomGenerationConfig:
    process_count: int
    arrival_min: int
    arrival_max: int
    burst_min: int
    burst_max: int
    priority_min: int
    priority_max: int
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.process_count <= 0:
            raise ValidationError("Number of processes must be greater than zero.")
        if self.arrival_min < 0:
            raise ValidationError("Minimum arrival time must be non-negative.")
        if self.arrival_min > self.arrival_max:
            raise ValidationError(
                "Minimum arrival time cannot exceed maximum arrival time."
            )
        if self.burst_min <= 0:
            raise ValidationError("Minimum burst time must be greater than zero.")
        if self.burst_min > self.burst_max:
            raise ValidationError(
                "Minimum burst time cannot exceed maximum burst time."
            )
        if self.priority_min <= 0:
            raise ValidationError("Minimum priority must be greater than zero.")
        if self.priority_min > self.priority_max:
            raise ValidationError(
                "Minimum priority cannot exceed maximum priority."
            )


class RandomProcessGenerator:
    def generate(
        self,
        config: RandomGenerationConfig,
        existing_ids: Iterable[str] = (),
    ) -> list[Process]:
        occupied_ids = set(existing_ids)
        generator = random.Random(config.seed)
        processes: list[Process] = []
        next_id = 1

        for _ in range(config.process_count):
            while f"P{next_id}" in occupied_ids:
                next_id += 1
            process_id = f"P{next_id}"
            next_id += 1
            processes.append(
                Process(
                    process_id=process_id,
                    arrival_time=generator.randint(
                        config.arrival_min, config.arrival_max
                    ),
                    burst_time=generator.randint(
                        config.burst_min, config.burst_max
                    ),
                    priority=generator.randint(
                        config.priority_min, config.priority_max
                    ),
                )
            )
            occupied_ids.add(process_id)

        return processes
