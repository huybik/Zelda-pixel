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
    "hp",
    "energy",
    "move_speed",
    "resistance",
    "attack_speed",
    "attack_range",
    "lifespan",
    "harvest",
    "chill",
    "attack",
    "heal",
    "tendency_to_help",
    "reproduction_rate",
    "decay",
]
ACTION_KEYS = ["attack", "heal", "reproduce", "harvest", "chill", "move"]


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
    attack_range: int

    # Resource-based
    lifespan: int
    harvest: int
    chill: int

    # Behavioral
    tendency_to_help: float
    reproduction_rate: float
    decay: float


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
        self.status = Status()

    
    

    def move(self, target_location: Location, env: "Environment") -> bool:
        current_x, current_y = self.location
        target_x, target_y = target_location

        if env.grid[target_y][target_x] != "-1":
            return False

        distance = abs(target_x - current_x) + abs(target_y - current_y)
        if distance <= self.stats.move_speed:
            result = env.move_entity(self.id, target_location)
            if result:
                self.status.move += 1
                return True
        return False

    def attack(self, target: "Creature") -> bool:
        if target != self:
            damage = int(self.stats.attack * self.stats.attack_speed)
            target.receive_damage(damage)
            if target.stats.hp == 0:
                self.status.killed += 1
            self.status.attack += 1
            return True
        return False

    def heal(self, target: "Creature") -> bool:
        if target != self:
            if self.stats.energy >= self.stats.heal:
                self.stats.energy -= self.stats.heal
                target.receive_heal(self.stats.heal)
                self.status.heal += 1
                return True
        return False

    def harvest(self, edible: Edible) -> bool:
        if self.stats.energy >= self.stats.harvest:
            if edible.reduce(self.stats.harvest):
                self.stats.energy -= self.stats.harvest
                self.stats.hp = min(
                    self.stats.hp + self.stats.harvest, self.stats.max_hp
                )
                self.status.harvest += 1
                if edible.stats.amount == 0:
                    self.status.collected += 1
                return True
        return False

    def chill(self) -> None:
        self.stats.energy = min(
            self.stats.energy + self.stats.chill, self.stats.max_energy
        )
        self.status.chill += 1
        return True

    def reproduce(
        self, partner: "Creature", env: "Environment"
    ) -> Optional["Creature"]:
        valid_cells = env.get_valid_adjacent_cell(self.id)
        if not valid_cells:
            return None

        if (
            random.random() < self.stats.reproduction_rate
            and random.random() < partner.stats.reproduction_rate
        ):

            child_genome = self._mix_genomes(partner)
            env._add_creature(location=valid_cells[0], genome=child_genome)
            self.stats.energy = 0  # reset energy
            self.status.reproduced += 1
            return True

        return None

    def _mix_genomes(self, partner: "Creature") -> GenomeType:
        child_genome: GenomeType = {}
        for key in GENOME_KEYS:
            child_genome[key] = []
            for i in range(self.n_bits):
                gene = (
                    self.genome[key][i]
                    if random.random() < 0.5
                    else partner.genome[key][i]
                )
                child_genome[key].append(gene)
        return child_genome

    def receive_damage(self, damage: int) -> bool:
        actual_damage = int(damage * (1 - self.stats.resistance))
        self.stats.hp = max(self.stats.hp - actual_damage, 0)
        return True

    def receive_heal(self, heal_amount: int) -> None:
        self.stats.hp = int(min(self.stats.hp + heal_amount, self.stats.max_hp))
        return True

    def decay(self) -> None:
        self.stats.hp -= int((self.n_bits - self.stats.decay))

    def get_all_movable_cells(self, env: "Environment") -> List[Location]:
        movable_cells = []
        x, y = self.location
        move_range = self.stats.move_speed

        for dy in range(-move_range, move_range + 1):
            for dx in range(-move_range, move_range + 1):
                new_x = x + dx
                new_y = y + dy

                if 0 <= new_x < env.config.size and 0 <= new_y < env.config.size:
                    distance = abs(dx) + abs(dy)
                    if distance <= move_range and env.grid[new_y][new_x] == "-1":
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

                if 0 <= new_x < env.config.size and 0 <= new_y < env.config.size:
                    entity_id = env.grid[new_y][new_x]
                    if entity_id != "-1":
                        entities_in_range.append(entity_id)

        return entities_in_range

    def get_nearest_empty_location_to_target(
        self, target_location: Location, env: "Environment"
    ) -> Optional[Location]:
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
                if (
                    0 <= new_x < env.config.size
                    and 0 <= new_y < env.config.size
                    and env.grid[new_y][new_x] == "-1"
                ):
                    # Calculate Manhattan distance from current location
                    distance = abs(new_x - current_x) + abs(new_y - current_y)
                    if distance <= move_range:
                        adjacent_cells.append(((new_x, new_y), distance))

        # Sort by distance and return the nearest empty location
        if adjacent_cells:
            adjacent_cells.sort(key=lambda x: x[1])
            return adjacent_cells[0][0]
        return None

    def simple_ai(
        self, env: "Environment"
    ) -> Tuple[bool, str, Union[str, Location, None]]:
        """Run simple AI behavior. Choose single action per step.

        Returns:
            Tuple[bool, str, Union[str, Location, None]]: (success, action, target)
            target can be entity id or location tuple
        """
        # Cache frequently used values
        hp_ratio = self.stats.hp / self.stats.max_hp
        energy_ratio = self.stats.energy / self.stats.max_energy
        adjacent_entities = env.get_adjacent_entities(self.location)

        # Energy management first - need energy for actions
        if energy_ratio < 0.2:
            success = self.chill()
            return success, "chill", None

        # Check adjacent entities for immediate interactions first
        for entity_id in adjacent_entities:
            entity = env.get_entity(entity_id)

            # Attack if enemy is weak and we have energy
            if (
                isinstance(entity, Creature)
                and entity.id != self.id
                and self.stats.tendency_to_help < 0.5  # Aggressive
                and entity.stats.hp < entity.stats.max_hp * 0.5
            ):  # Target weak creatures
                success = self.attack(entity)
                if success:
                    return True, "attack", entity_id

            if (
                isinstance(entity, Creature)
                and entity.id != self.id
                and self.stats.tendency_to_help > 0.5  # Aggressive
                and entity.stats.hp < entity.stats.max_hp * 0.5
            ):  # Target weak creatures
                success = self.heal(entity)
                if success:
                    return True, "heal", entity_id

            # # Try reproduction if both creatures are healthy
            # if (isinstance(entity, Creature) and
            #     entity.id != self.id and
            #     hp_ratio > 0.1 and  # Higher threshold for reproduction
            #     energy_ratio > 0.1 and
            #     entity.stats.hp > entity.stats.max_hp * 0.1):
            #     success = self.reproduce(entity, env)
            #     if success:
            #         return True, "reproduce", entity_id

            # Harvest food if we need health/energy
            if isinstance(entity, Edible) and self.stats.energy >= self.stats.harvest:
                success = self.harvest(entity)
                return success, "harvest", entity_id

        # Critical health behavior - look for food or help
        if hp_ratio < 0.3:
            entities_in_range = self.get_all_entities_in_range(env)
            for entity_id in entities_in_range:
                entity = env.get_entity(entity_id)
                target_location = self.get_nearest_empty_location_to_target(
                    entity.location, env
                )

                if not target_location:
                    continue

                if isinstance(entity, Edible):
                    success = self.move(target_location, env)
                    return success, "move", target_location

                if (
                    isinstance(entity, Creature)
                    and entity.id != self.id
                    and entity.stats.tendency_to_help > 0.8
                ):
                    success = self.move(target_location, env)
                    return success, "move", target_location

        # Search for targets to attack
        entities_in_range = self.get_all_entities_in_range(env)
        for entity_id in entities_in_range:
            entity = env.get_entity(entity_id)
            if (
                isinstance(entity, Creature)
                and entity.id != self.id
                and self.stats.tendency_to_help < 0.9  # Aggressive
                and entity.stats.hp < entity.stats.max_hp * 0.7
            ):  # Target weaker creatures
                target_location = self.get_nearest_empty_location_to_target(
                    entity.location, env
                )
                if target_location:
                    success = self.move(target_location, env)
                    return success, "move", target_location

        # Look for potential mates
        if hp_ratio > 0.5 and energy_ratio > 0.5:  # Only look for mates when healthy
            for entity_id in entities_in_range:
                entity = env.get_entity(entity_id)
                if (
                    isinstance(entity, Creature)
                    and entity.id != self.id
                    and entity.stats.hp > entity.stats.max_hp * 0.5
                ):
                    target_location = self.get_nearest_empty_location_to_target(
                        entity.location, env
                    )
                    if target_location:
                        success = self.move(target_location, env)
                        return success, "move", target_location

        # General exploration for food
        for entity_id in entities_in_range:
            entity = env.get_entity(entity_id)
            if isinstance(entity, Edible):
                target_location = self.get_nearest_empty_location_to_target(
                    entity.location, env
                )
                if target_location:
                    success = self.move(target_location, env)
                    return success, "move", target_location

        # Random movement as last resort
        movable_cells = self.get_all_movable_cells(env)
        if movable_cells:
            target = random.choice(movable_cells)
            success = self.move(target, env)
            return success, "move", target

        return False, "none", None
