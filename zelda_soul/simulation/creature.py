import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, List, Dict, Union, Optional, TypeAlias

from edible import Edible

if TYPE_CHECKING:
    from creature import Creature
    from environment import Environment

# Type aliases for better readability
Location: TypeAlias = Tuple[int, int]
GenomeType: TypeAlias = Dict[str, List[int]]
GenomeSums: TypeAlias = Dict[str, int]

# Constants
DEFAULT_LOCATION = (0, 0)
GENOME_KEYS = [
    "hp", "energy", "move_speed", "resistance",
    "attack_speed", "lifespan", "harvest", "chill", "attack",
    "heal", "tendency_to_help", "reproduction_rate", "decay"
]

@dataclass
class CreatureStats:
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
    
    # Resource-based
    lifespan: int
    harvest: int
    chill: int
    
    # Behavioral
    tendency_to_help: float
    reproduction_rate: float
    decay: float

class Creature:
    def __init__(
        self,
        id: str,
        genome: Optional[GenomeType] = None,
        n_bits: int = 8,
        genome_points: int = 4,
        init_stat_point: int = 100,
        location: Location = DEFAULT_LOCATION,
    ) -> None:
        self.id = id
        self.location = location
        self.init_stat_point = init_stat_point
        self.n_bits = n_bits
        
        self.genome = self._initialize_genome(genome, genome_points)
        self.genome_sums = self._calculate_genome_sums()
        
        self.stats = self._calculate_stats()
    
    def _calculate_genome_sums(self) -> GenomeSums:
        return {key: sum(self.genome[key]) for key in GENOME_KEYS}

    def _initialize_genome(
        self, 
        genome: Optional[GenomeType], 
        genome_points: int
    ) -> GenomeType:
        if genome:
            return genome
            
        new_genome = {key: [0] * self.n_bits for key in GENOME_KEYS}
        remaining_points = genome_points
        
        # First, ensure at least 1 point per key
        for key in GENOME_KEYS:
            idx = random.randrange(self.n_bits)
            new_genome[key][idx] = 1
            remaining_points -= 1
            
        # Then distribute remaining points randomly
        if remaining_points > 0:
            available_positions = [
                (key, i) for key in GENOME_KEYS 
                for i in range(self.n_bits)
                if new_genome[key][i] == 0  # Only consider empty positions
            ]
            
            for key, idx in random.sample(available_positions, remaining_points):
                new_genome[key][idx] = 1
            
        return new_genome

    def _calculate_stats(self) -> CreatureStats:
        """Calculate creature stats from genome sums."""
        
        # Normalize genome sums to get stat ratios
        ratios = {
            key: value / self.n_bits 
            for key, value in self.genome_sums.items()
        }
        return CreatureStats(
        # Calculate base stats
        hp = self.init_stat_point,
        energy = self.init_stat_point,
        attack = int(self.init_stat_point*ratios["attack"]),
        heal = int(self.init_stat_point*ratios["heal"]),
        
        # Calculate max stats
        max_hp = int(self.init_stat_point + self.init_stat_point * self.genome_sums["hp"]),
        max_energy = int(self.init_stat_point + self.init_stat_point * self.genome_sums["energy"]),
        
        # Calculate movement and combat stats
        move_speed = self.genome_sums["move_speed"],
        resistance = ratios["resistance"],
        attack_speed = self.genome_sums["attack_speed"],
        
        # Calculate resource-based stats
        lifespan = int(self.init_stat_point * ratios["lifespan"]),
        harvest = int(self.init_stat_point * ratios["harvest"]),
        chill = int(self.init_stat_point * ratios["chill"]),
        
        
        # Calculate ratio stats
        tendency_to_help = ratios["tendency_to_help"],
        reproduction_rate = ratios["reproduction_rate"],
        decay = ratios["decay"]
        )

    def move(self, target_location: Location, env: "Environment") -> bool:
        current_x, current_y = self.location
        target_x, target_y = target_location
        
        if env.grid[target_y][target_x] != "-1":
            return False
            
        distance = abs(target_x - current_x) + abs(target_y - current_y)
        if distance <= self.stats.move_speed:
            return env.move_entity(self.id, target_location)
            
        return False

    def attack(self, target: "Creature") -> bool:
        damage = int(self.stats.attack * self.stats.attack_speed)
        return target.receive_damage(damage)

    def heal(self, target: "Creature") -> bool:
        if target != self:
            if self.stats.energy >= self.stats.heal:
                self.stats.energy -= self.stats.heal
                target.receive_heal(self.stats.heal)
                return True
        return False

    def harvest(self, edible: Edible) -> bool:
        if self.stats.energy >= self.stats.harvest:
            if edible.reduce(self.stats.harvest):
                self.stats.energy -= self.stats.harvest
                self.stats.hp = min(
                    self.stats.hp + self.stats.harvest,
                    self.stats.max_hp
                )
                return True
        return False

    def chill(self) -> None:
        self.stats.energy = min(
            self.stats.energy + self.stats.chill,
            self.stats.max_energy
        )
        return True

    def reproduce(
        self, 
        partner: "Creature", 
        env: "Environment"
    ) -> Optional["Creature"]:
        valid_cells = env.get_valid_adjacent_cell(self.id)
        if not valid_cells:
            return None
            
        if (random.random() < self.stats.reproduction_rate and 
            random.random() < partner.stats.reproduction_rate):
            
            child_genome = self._mix_genomes(partner)
            return env._add_creature(location=valid_cells[0], genome=child_genome)
            
        return None
    
    def _mix_genomes(self, partner: "Creature") -> GenomeType:
        child_genome: GenomeType = {}
        for key in GENOME_KEYS:
            child_genome[key] = []
            for i in range(self.n_bits):
                gene = (self.genome[key][i] 
                       if random.random() < 0.5 
                       else partner.genome[key][i])
                child_genome[key].append(gene)
        return child_genome


    def receive_damage(self, damage: int) -> bool:
        actual_damage = int(damage * (1 - self.stats.resistance))
        if self.stats.hp > actual_damage:
            # print("actutal damage", actual_damage, damage)  
            self.stats.hp = max(self.stats.hp - actual_damage, 0)
            return True
        return False
        
    def receive_heal(self, heal_amount: int) -> None:
        self.stats.hp = int(min(self.stats.hp + heal_amount, self.stats.max_hp))
        
    def decay(self) -> None:
        self.stats.hp -=  int(self.n_bits-self.stats.decay)
    
    def get_all_movable_cells(self, env: "Environment") -> List[Location]:
        movable_cells = []
        x, y = self.location
        move_range = self.stats.move_speed
        
        for dy in range(-move_range, move_range + 1):
            for dx in range(-move_range, move_range + 1):
                new_x = x + dx
                new_y = y + dy
                
                if (0 <= new_x < env.config.size and 
                    0 <= new_y < env.config.size):
                    distance = abs(dx) + abs(dy)
                    if (distance <= move_range and 
                        env.grid[new_y][new_x] == "-1"):
                        movable_cells.append((new_x, new_y))
        
        return movable_cells
    
    def get_all_entities_in_range(self, env: "Environment") -> List[str]:
        """Get all entity IDs within move range of the creature."""
        x, y = self.location
        move_range = self.stats.move_speed
        entities_in_range = []
        
        for dy in range(-move_range, move_range + 1):
            for dx in range(-move_range, move_range + 1):
                new_x = x + dx
                new_y = y + dy
                
                if (0 <= new_x < env.config.size and 
                    0 <= new_y < env.config.size):
                    entity_id = env.grid[new_y][new_x]
                    if entity_id != "-1":
                        entities_in_range.append(entity_id)
        
        return entities_in_range
    
    def get_nearest_empty_location_to_target(self, target_location: Location, env: "Environment") -> Optional[Location]:
        """Find the nearest empty location next to a target that is within move range."""
        x, y = target_location
        move_range = self.stats.move_speed
        current_x, current_y = self.location
        
        # Check adjacent cells to target in order of distance from current location
        adjacent_cells = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                new_x = x + dx
                new_y = y + dy
                
                # Check if within bounds and empty
                if (0 <= new_x < env.config.size and 
                    0 <= new_y < env.config.size and
                    env.grid[new_y][new_x] == "-1"):
                    # Calculate Manhattan distance from current location
                    distance = abs(new_x - current_x) + abs(new_y - current_y)
                    if distance <= move_range:
                        adjacent_cells.append(((new_x, new_y), distance))
        
        # Sort by distance and return the nearest empty location
        if adjacent_cells:
            adjacent_cells.sort(key=lambda x: x[1])
            return adjacent_cells[0][0]
        return None

    def simple_ai(self, env: "Environment") -> Tuple[bool, str, Union[str, Location, None]]:
        """Run simple AI behavior. Choose single action per step.
        
        Returns:
            Tuple[bool, str, Union[str, Location, None]]: (success, action, target)
            target can be entity id or location tuple
        """
        # When low on health, prioritize finding food or friendly creatures
        if self.stats.hp < self.stats.max_hp * 0.3:
            # First check for adjacent edibles
            adjacent_entities = env.get_adjacent_entities(self.location)
            for entity_id in adjacent_entities:
                entity = env.get_entity(entity_id)
                if isinstance(entity, Edible) and self.stats.energy >= self.stats.harvest:
                    success = self.harvest(entity)
                    return success, "harvest", entity_id
                    
            # Then look for edibles in range to move towards
            entities_in_range = self.get_all_entities_in_range(env)
            for entity_id in entities_in_range:
                entity = env.get_entity(entity_id)
                if isinstance(entity, Edible):
                    target_location = self.get_nearest_empty_location_to_target(entity.location, env)
                    if target_location:
                        success = self.move(target_location, env)
                        return success, "move", target_location
                
            # If no edibles, look for friendly creatures nearby
            for entity_id in adjacent_entities:
                entity = env.get_entity(entity_id)
                if isinstance(entity, Creature) and entity.id != self.id:
                    if entity.stats.tendency_to_help > 0.5:
                        target_location = self.get_nearest_empty_location_to_target(entity.location, env)
                        if target_location:
                            success = self.move(target_location, env)
                            return success, "move", target_location
            
        # Check if need energy
        if self.stats.energy < self.stats.max_energy * 0.3:
            success = self.chill()
            return success, "chill", None
            
        # Try to reproduce if healthy and has enough energy
        if (self.stats.hp > self.stats.max_hp * 0.7 and 
            self.stats.energy > self.stats.max_energy * 0.7):
            adjacent_entities = env.get_adjacent_entities(self.location)
            for entity_id in adjacent_entities:
                entity = env.get_entity(entity_id)
                if (isinstance(entity, Creature) and 
                    entity.id != self.id and
                    entity.stats.hp > entity.stats.max_hp * 0.7):
                    success = self.reproduce(entity, env)
                    return success, "reproduce", entity_id
            
            # Look for potential mates in range
            entities_in_range = self.get_all_entities_in_range(env)
            for entity_id in entities_in_range:
                entity = env.get_entity(entity_id)
                if (isinstance(entity, Creature) and 
                    entity.id != self.id and
                    entity.stats.hp > entity.stats.max_hp * 0.7):
                    target_location = self.get_nearest_empty_location_to_target(entity.location, env)
                    if target_location:
                        success = self.move(target_location, env)
                        return success, "move", target_location
            
        # Check adjacent entities for immediate interactions
        adjacent_entities = env.get_adjacent_entities(self.location)
        for entity_id in adjacent_entities:
            entity = env.get_entity(entity_id)
            if isinstance(entity, Edible):
                # Try to harvest if adjacent to edible
                if self.stats.energy >= self.stats.harvest:
                    success = self.harvest(entity)
                    return success, "harvest", entity_id
            elif isinstance(entity, Creature) and entity.id != self.id:
                # Try to heal weak friendly creatures
                if (self.stats.tendency_to_help > 0.5 and 
                    entity.stats.hp < entity.stats.max_hp * 0.5 and
                    self.stats.energy >= self.stats.heal):
                    success = self.heal(entity)
                    return success, "heal", entity_id
                # Attack if not friendly
                elif self.stats.tendency_to_help <= 0.5:
                    success = self.attack(entity)
                    return success, "attack", entity_id
        
        # If no immediate interactions, look for targets to move towards
        # First priority: Find edibles in range
        entities_in_range = self.get_all_entities_in_range(env)
        for entity_id in entities_in_range:
            entity = env.get_entity(entity_id)
            if isinstance(entity, Edible):
                target_location = self.get_nearest_empty_location_to_target(entity.location, env)
                if target_location:
                    success = self.move(target_location, env)
                    return success, "move", target_location
            
        # Second priority: Find creatures to interact with
        for entity_id in entities_in_range:
            entity = env.get_entity(entity_id)
            if isinstance(entity, Creature) and entity.id != self.id:
                target_location = self.get_nearest_empty_location_to_target(entity.location, env)
                if target_location:
                    if self.stats.tendency_to_help > 0.5:
                        # Move towards weak creatures to heal them
                        if entity.stats.hp < entity.stats.max_hp * 0.5:
                            success = self.move(target_location, env)
                            return success, "move", target_location
                    else:
                        # Move towards creatures to attack
                        success = self.move(target_location, env)
                        return success, "move", target_location
        
        # If no targets found, move randomly
        movable_cells = self.get_all_movable_cells(env)
        if movable_cells:
            target = random.choice(movable_cells)
            success = self.move(target, env)
            return success, "move", (target)
            
        return False, "none", None