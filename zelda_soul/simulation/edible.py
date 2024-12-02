from dataclasses import dataclass
from typing import Tuple, Dict

@dataclass
class EdibleStats:
    amount: int

class Edible:
    
    def __init__(
        self, 
        id: str, 
        initial_amount: int, 
        location: Tuple[int, int] = (0, 0)
    ) -> None:
        self.id = id
        self.location = location
        self.stats = EdibleStats(
            amount=initial_amount
        )
        
    def reduce(self, amount: int) -> bool:
        
        if self.stats.amount > 0:
            self.stats.amount = max(self.stats.amount - amount, 0)
            return True
        return False