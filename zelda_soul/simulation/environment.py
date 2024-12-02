from dataclasses import dataclass
import random
from typing import Dict, List, Tuple, Optional, Union, TypeAlias, Any

from creature import Creature
from edible import Edible

GridType: TypeAlias = List[List[str]]
Location: TypeAlias = Tuple[int, int]

@dataclass
class EnvironmentConfig:
    size: int
    n_bits: int
    genome_points: int
    init_stat_point: int

class Environment:
    def __init__(self, config: EnvironmentConfig) -> None:
        self.config = config
        self.grid: GridType = [["-1"] * config.size for _ in range(config.size)]
        self.creatures: Dict[str, Creature] = {}
        self.edibles: Dict[str, Edible] = {}
        self.creature_counter = 0
        self.edible_counter = 0
        self.action_history = []

    def _generate_creature_id(self) -> str:
        self.creature_counter += 1
        return f"c{self.creature_counter}"
        
    def _generate_edible_id(self) -> str:
        self.edible_counter += 1
        return f"e{self.edible_counter}"

    def _add_creature(
        self, 
        location: Optional[Location] = None,
        genome: Optional[Dict[str, List[int]]] = None
    ) -> Optional[Creature]:
        if location is None:
            location = self.get_random_empty_location()
            if not location:
                return None

        entity_id = self._generate_creature_id()
        creature = Creature(
            id=entity_id,
            genome=genome,
            n_bits=self.config.n_bits,
            genome_points=self.config.genome_points,
            init_stat_point=self.config.init_stat_point,
            location=location
        )
        
        self.creatures[entity_id] = creature
        x, y = location
        self.grid[y][x] = entity_id
        return creature

    def _add_edible(
        self, 
        location: Optional[Location] = None,
        amount: Optional[int] = None
    ) -> Optional[Edible]:
        if location is None:
            location = self.get_random_empty_location()
            if not location:
                return None

        entity_id = self._generate_edible_id()
        edible = Edible(
            id=entity_id,
            location=location,
            initial_amount=amount if amount is not None else random.randint(50, 150)
        )
        
        self.edibles[entity_id] = edible
        x, y = location
        self.grid[y][x] = entity_id
        return edible

    def get_random_empty_location(self) -> Optional[Location]:
        """Get a random empty cell in the grid."""
        empty_cells = []
        for y in range(self.config.size):
            for x in range(self.config.size):
                if self.grid[y][x] == "-1":
                    empty_cells.append((x, y))
                    
        if empty_cells:
            location = random.choice(empty_cells)
            # Mark as used immediately to prevent duplicates
            x, y = location
            self.grid[y][x] = "temp"  # Temporary marker
            return location
        return None

    def _display_grid(self) -> None:
        for row in self.grid:
            print(" ".join([str(cell) for cell in row]))
            
    def get_entity(self, entity_id: str) -> Optional[Union[Creature, Edible]]:
        return self.creatures.get(entity_id) or self.edibles.get(entity_id)

    def get_edible(self, edible_id: str) -> Optional[Edible]:
        return self.edibles.get(edible_id)

    def get_creature(self, creature_id: str) -> Optional[Creature]:
        return self.creatures.get(creature_id)

    def get_location(self, entity_id: str) -> Optional[Location]:
        entity = self.get_entity(entity_id)
        if entity:
            return entity.location
        return None

    def get_adjacent_entities(self, location: Location) -> List[str]:
        x, y = location
        adjacent_entities = []
        
        # Check all adjacent cells (including diagonals)
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                    
                new_x = x + dx
                new_y = y + dy
                
                # Check if within bounds
                if (0 <= new_x < self.config.size and 
                    0 <= new_y < self.config.size):
                    entity_id = self.grid[new_y][new_x]
                    if entity_id != "-1":
                        adjacent_entities.append(entity_id)
        
        return adjacent_entities

    def get_valid_adjacent_cell(self, entity_id: str) -> List[Location]:
        entity_location = self.get_location(entity_id)
        if not entity_location:
            return []
            
        x, y = entity_location
        valid_cells = []
        
        # Check all adjacent cells (including diagonals)
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                    
                new_x = x + dx
                new_y = y + dy
                
                # Check if within bounds and empty
                if (0 <= new_x < self.config.size and 
                    0 <= new_y < self.config.size and 
                    self.grid[new_y][new_x] == "-1"):
                    valid_cells.append((new_x, new_y))
        
        return valid_cells

    def move_entity(self, entity_id: str, new_location: Location) -> bool:
        entity = self.creatures.get(entity_id)
        if not entity:
            return False
            
        old_x, old_y = entity.location
        new_x, new_y = new_location
        
        # Check if new location is within bounds and empty
        if (0 <= new_x < self.config.size and 
            0 <= new_y < self.config.size and 
            self.grid[new_y][new_x] == "-1"):
            
            # Update grid
            self.grid[old_y][old_x] = "-1"
            self.grid[new_y][new_x] = entity_id
            
            # Update entity location
            entity.location = new_location
            return True
            
        return False

    def remove_entity(self, entity_id: str) -> bool:
        entity = self.get_entity(entity_id)
        if entity:
            print(entity)
            x, y = entity.location
            self.grid[y][x] = "-1"
            if isinstance(entity, Edible):
                del self.edibles[entity_id]
            else:
                del self.creatures[entity_id]
            return True
        return False

    def populate(
        self,
        n_creatures: int,
        n_edibles: int,
        edible_amount: Optional[int] = None
    ) -> None:
        # Add creatures
        for _ in range(n_creatures):
            self._add_creature()
            
        # Add edibles
        for _ in range(n_edibles):
            self._add_edible(amount=edible_amount)

    def step(self) -> None:
        
        
        # Process all entities
        for entity_id, entity in list(self.creatures.items()):
            if isinstance(entity, Creature):
                # Apply decay
                entity.decay()
                
                # Remove if dead
                if entity.stats.hp <= 0:
                    self.remove_entity(entity_id)
                    continue
                    
                # Run AI
                success, action, target_id = entity.simple_ai(self)
                print(entity_id, action, target_id, success)
                self.action_history.append((entity_id, action, target_id, success))
                    
            elif isinstance(entity, Edible):
                # Remove if depleted
                if entity.stats.amount <= 0:
                    self.remove_entity(entity_id)
        

    def get_stats(self) -> Dict[str, Any]:
        n_creatures = sum(1 for entity in self.creatures.values() 
                         if isinstance(entity, Creature))
        n_edibles = sum(1 for entity in self.creatures.values() 
                       if isinstance(entity, Edible))
        total_edible_amount = sum(entity.stats.amount for entity in self.creatures.values() 
                                if isinstance(entity, Edible))
        
        return {
            "n_creatures": n_creatures,
            "n_edibles": n_edibles,
            "total_edible_amount": total_edible_amount
        }