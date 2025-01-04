from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class ResourceStat:
    amount: int


class Resource:

    def __init__(
        self,
        id: str,
        location: Tuple[int, int],
        type: str,
        amount: int = 100,
    ) -> None:
        self.id = id
        self.type = type
        self.location = location
        self.stats = ResourceStat(amount=amount)

    def reduce(self, amount: int) -> bool:

        if self.stats.amount > 0:
            self.stats.amount = max(self.stats.amount - amount, 0)
            return True
        return False
