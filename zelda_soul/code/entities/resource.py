from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class ResourceStat:
    hp: int


class ResourceStatus:
    deleted: bool = False  # resource depleted


class Resource:

    def __init__(
        self,
        id: str,
        location: Tuple[int, int],
        type: str,
        hp: int = 100,
    ) -> None:
        self.id = id
        self.type = type
        self.location = location
        self.stats = ResourceStat(hp=hp)
        self.status = ResourceStatus()

    def reduce(self, hp: int) -> bool:

        if self.stats.hp > 0:
            self.stats.hp = max(self.stats.hp - hp, 0)
            return True
        return False
