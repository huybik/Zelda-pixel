from typing import TYPE_CHECKING, Tuple, List, Dict, Union, Optional, TypeAlias
from .stats import Stats, Genome, CreatureStat, Status
from .actions import Action


class Creature:

    def __init__(
        self,
        id: str,
        location: Tuple[int, int],
        type: str,
        genome: Optional[Genome] = None,
    ):
        self.id = id
        self.location = location

        stats = CreatureStat(genome)
        self.genome: Genome = stats.get_genome()
        self.stats: Stats = stats.get_stats()
        self.status: Status = stats.get_status()



if __name__ == "__main__":
    creature = Creature(id="c1")
    print(creature.stats)
    print(creature.genome)
    print(creature.status)
