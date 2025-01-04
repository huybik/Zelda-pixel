from dataclasses import dataclass
import random
from typing import Dict, List, Tuple, Optional, Union, TypeAlias, Any

from entities.creature import Creature
from entities.resource import Resource
from environment.pathfinder import Pathfinder

GridType: TypeAlias = List[List[str]]
Location: TypeAlias = Tuple[int, int]


@dataclass
class EnvironmentConfig:
    size: int
    n_creature: int
    n_resource: int
    resource_amount: int


class Environment:
    def __init__(self, config: EnvironmentConfig) -> None:
        self.config = config

        self.grid: GridType = [["-1"] * config.size for _ in range(config.size)]
        self.pathfinder = Pathfinder()
        self.creatures: Dict[str, Creature] = {}
        self.resources: Dict[str, Resource] = {}

        self.creature_counter = 0
        self.resource_counter = 0
        self.action_history = []

    def add_creatures(self, creatures: List[Creature]) -> bool:
        for creature in creatures:
            self._add_creature(creature=creature)
        return True

    def add_resources(self, resources: List[Resource]) -> bool:
        for resource in resources:
            self._add_resource(amount=resource.amount)
        return True

    def populate(
        self,
    ) -> None:
        # Add creatures
        for _ in range(self.config.n_creature):
            self._add_creature()

        # Add resources
        for _ in range(self.config.n_resource):
            self._add_resource(amount=self.config.resource_amount)

    def _generate_creature_id(self) -> str:
        self.creature_counter += 1
        return f"c{self.creature_counter}"

    def _generate_resource_id(self) -> str:
        self.resource_counter += 1
        return f"r{self.resource_counter}"

    def _add_creature(
        self,
        location: Optional[Location] = None,
        genome: Optional[Dict[str, List[int]]] = None,
        creature: Optional[Creature] = None,
    ) -> Optional[Creature]:
        if not location:
            location = self.pathfinder.get_random_empty_location(self)
            if not location:
                return None

        id = self._generate_creature_id()
        if not creature:
            creature = Creature(
                id=id,
                location=location,
                type="creature",
                genome=genome,
            )

        self.creatures[id] = creature
        x, y = creature.location
        self.grid[y][x] = id
        return creature

    def _add_resource(
        self,
        location: Optional[Location] = None,
        amount: Optional[int] = None,
        resource: Optional[Resource] = None,
    ) -> Optional[Resource]:
        if location is None:
            location = self.pathfinder.get_random_empty_location(self)
            if not location:
                return None

        id = self._generate_resource_id()
        if not resource:
            resource = Resource(
                id=id,
                location=location,
                type="edible",
                amount=amount if amount is not None else random.randint(50, 150),
            )

        self.resources[id] = resource
        x, y = location
        self.grid[y][x] = id
        return resource

    def get_entity(self, entity_id: str) -> Optional[Union[Creature, Resource]]:
        return self.creatures.get(entity_id) or self.resources.get(entity_id)

    def display(self) -> None:
        # Print column numbers
        print("   " + " ".join([f"{i:2}" for i in range(self.config.size)]))
        for idx, row in enumerate(self.grid):
            # Print row number and row content
            print(f"{idx:2} " + " ".join([str(cell) for cell in row]))

    def reset(self):
        self.grid = [["-1"] * self.config.size for _ in range(self.config.size)]
        self.creatures = {}
        self.resources = {}
        self.creature_counter = 0
        self.resource_counter = 0

    def remove_entity(self, entity_id: str) -> bool:
        entity = self.get_entity(entity_id)
        if entity:
            # print(entity)
            x, y = entity.location
            self.grid[y][x] = "-1"
            if isinstance(entity, Resource):
                del self.resources[entity_id]
            else:
                del self.creatures[entity_id]
            return True
        return False

    def step(self) -> None:
        # Process all entities
        for entity_id, entity in list(self.creatures.items()):
            # Apply decay
            entity.stats.hp -= 1

            # Remove if dead
            if entity.stats.hp <= 0:
                self.remove_entity(entity_id)
                continue

            # Run AI
            success, action, target_id = entity.simple_ai(self)
            # print(entity_id, action, target_id, success)
            self.action_history.append((entity_id, action, target_id, success))
        for entity_id, entity in list(self.resources.items()):
            # Remove if depleted
            if entity.stats.amount <= 0:

                self.remove_entity(entity_id)
