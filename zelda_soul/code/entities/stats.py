import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, List, Dict, Union, Optional, TypeAlias

Genome: TypeAlias = Dict[str, List[int]]

GENOME_BITS = 10


@dataclass
class Stats:
    # Base stats
    hp: int
    energy: int
    attack: int
    heal: int

    # Max stats
    max_hp: int
    max_energy: int

    # Movement and combat
    move_speed: int
    resistance: float
    attack_speed: float
    attack_range: int
    notice_range: int

    # Resource-based
    lifespan: int
    harvest: int
    chill: int

    # Behavioral
    tendency_to_help: float
    reproduction_rate: float


@dataclass
class Status:
    # achivement
    lifespan: int = 0  # how many steps before die
    killed: int = 0  # how many creatures killed
    collected: int = 0  # how many edible harvested
    reproduced: int = 0  # how many creatures reproduced
    # acction count
    attack: int = 0  # how many times attack
    heal: int = 0  # how many times heal
    move: int = 0  # how many times move
    harvest: int = 0  # how many times harvest
    chill: int = 0  # how many times chill


GENOME_KEYS = [
    "max_hp",
    "max_energy",
    "move_speed",
    "resistance",
    "attack_speed",
    "attack_range",
    "notice_range",
    "lifespan",
    "harvest",
    "chill",
    "attack",
    "heal",
    "tendency_to_help",
    "reproduction_rate",
]


class CreatureStat:
    def __init__(self, genome: Optional[Genome] = None):
        self.genome = genome if genome else self._initialize_genome(GENOME_BITS)
        self.stats = self._calculate_stats(self.genome)
        self.status = Status()

    def get_stats(self) -> Stats:
        return self.stats

    def get_genome(self) -> Genome:
        return self.genome

    def get_status(self) -> Status:
        return self.status

    def _calculate_stats(self, genome: Genome) -> Stats:
        """Calculate creature stats from genome sums."""
        genome_sums = {key: sum(genome[key]) + 1 for key in GENOME_KEYS}
        genome_sums["hp"] = 1
        genome_sums["energy"] = 1
        stats = Stats(**genome_sums)

        return stats

    def _initialize_genome(self, n_bits) -> Genome:
        new_genome = {key: [0] * n_bits for key in GENOME_KEYS}
        remaining_points = len(GENOME_KEYS)

        # Then distribute remaining points randomly
        if remaining_points > 0:
            available_positions = [
                (key, i) for key in GENOME_KEYS for i in range(n_bits)
            ]

            for key, idx in random.sample(available_positions, remaining_points):
                new_genome[key][idx] = 1

        return new_genome


if __name__ == "__main__":
    stats = CreatureStat()
    print(stats.genome)
    print(stats.stats)
    print(stats.status)
