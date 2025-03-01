from math import inf
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from dataclasses import asdict, dataclass
import random
import copy
from typing import Dict, List, Tuple, Optional, Union, TypeAlias, Any


from entities.creature import Creature
from entities.resource import Resource
from environment.pathfinder import Pathfinder
from ai.simple_ai import SimpleAI
from entities.actions import Action
from settings import MAX_STEP_COUNT

GridType: TypeAlias = List[List[str]]
Location: TypeAlias = Tuple[int, int]


@dataclass
class EnvironmentConfig:
    size: int = 8
    n_creature: int = 4
    n_resource: int = 8
    resource_hp: int = 20


class Environment(gym.Env):
    metadata = {"render_modes": ["console"]}

    def __init__(
        self,
        render_mode: str = "console",
    ) -> None:
        super(Environment, self).__init__()
        self.config = EnvironmentConfig()
        self.n_types = 4  # 0 for empty, 1 for player, 2 for creature, 3 for resource

        self.render_mode = render_mode
        self.int_to_action = {
            0: "move_up",
            1: "move_down",
            2: "move_left",
            3: "move_right",
            4: "attack",
            5: "heal_self",
            6: "heal_other",
            7: "harvest",
            8: "reproduce",
        }

        # self.int_to_action = {
        #     0: "move_up",
        #     1: "move_down",
        #     2: "move_left",
        #     3: "move_right",
        #     4: "attack",
        #     5: "harvest",
        # }

        self.action_space = spaces.Discrete(len(self.int_to_action))

        self.grid: GridType = [
            ["-1"] * self.config.size for _ in range(self.config.size)
        ]
        self.pathfinder = Pathfinder()
        self.ai = SimpleAI()

        self.entities: Dict[str, Union[Creature, Resource]] = {}
        self.action_history = []
        self.actions = Action()

        self.resource_counter = 0
        self.creature_counter = 0

        self.state = None
        self.reward = None
        self.terminated = None
        self.truncated = None
        self.step_count = 0

        self.populate()

        onehot = spaces.MultiBinary(
            self.config.size * self.config.size * self.n_types + len(self.int_to_action)
        )

        continuous = spaces.Box(
            low=0,
            high=inf,
            shape=(len(self.player.status.__dataclass_fields__) + 2,),
            dtype=np.int32,
        )

        self.observation_space = spaces.Dict(
            {
                "onehot": onehot,
                "continuous": continuous,
            }
        )

    def observation(self, action_int=0):
        def convert_string(s):
            if s.startswith("c"):
                return 2
            elif s.startswith("r"):
                return 3
            else:
                return 0

        contiuous_list = []
        one_hot_list = []
        self.output_grid = copy.deepcopy(self.grid)
        for y, row in enumerate(self.grid):
            for x, s in enumerate(row):
                if s == self.player.id:
                    self.output_grid[y][x] = 1
                else:
                    self.output_grid[y][x] = convert_string(s)
                onehot = [0, 0, 0, 0]
                onehot[int(self.output_grid[y][x])] = 1
                one_hot_list.extend(onehot)

        one_hot_action = [0] * len(self.int_to_action)
        one_hot_action[action_int] = 1
        one_hot_list.extend(one_hot_action)
        # add stats

        for key, value in asdict(self.player.status).items():
            contiuous_list.append(value)

        contiuous_list.append(self.player.stats.hp)
        contiuous_list.append(self.player.stats.energy)

        return {
            "onehot": np.array(one_hot_list, dtype=np.int8),
            "continuous": np.array(contiuous_list, dtype=np.int32),
        }

    def add_creatures(self, creatures: List[Creature]) -> bool:
        for creature in creatures:
            creature = self._create_creature(creature=creature)
        return creature

    def add_resources(self, resources: List[Resource]) -> bool:
        for resource in resources:
            resource = self._create_resource(hp=resource.hp)
        return resource

    def populate(
        self,
    ) -> None:
        # Add creatures
        for _ in range(self.config.n_creature):
            self._create_creature()

        # Add resources
        for _ in range(self.config.n_resource):
            self._create_resource(hp=self.config.resource_hp)

        self.player = self.entities["c1"]  # set default player

    def _generate_creature_id(self) -> str:
        self.creature_counter += 1
        return f"c{self.creature_counter}"

    def _generate_resource_id(self) -> str:
        self.resource_counter += 1
        return f"r{self.resource_counter}"

    def _create_creature(
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

        self.entities[id] = creature
        x, y = creature.location
        self.grid[y][x] = id
        return creature

    def _create_resource(
        self,
        location: Optional[Location] = None,
        hp: Optional[int] = None,
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
                hp=hp if hp else random.randint(50, 150),
            )

        self.entities[id] = resource
        x, y = location
        self.grid[y][x] = id
        return resource

    def get_entity(self, entity_id: str) -> Optional[Union[Creature, Resource]]:
        return self.entities.get(entity_id)

    def render(self) -> None:
        # Print column numbers
        self.observation()
        if self.render_mode == "console":
            # print("" + " ".join([f"{i:2}" for i in range(self.config.size)]))
            for idx, row in enumerate(self.output_grid):
                # Print row number and row content
                print(" ".join([str(cell) for cell in row]))
                # print(f"{idx:2} " + " ".join([str(cell) for cell in row]))

    def mark_delete(self, entity_id: str):
        entity = self.get_entity(entity_id)
        entity.status.deleted = True

    def remove_deleted(self, deleted_ids) -> bool:
        for id in deleted_ids:
            x, y = self.entities[id].location
            self.grid[y][x] = "-1"
            del self.entities[id]
        return True

    def env_step(self) -> None:
        # Process all entities
        for entity_id, entity in list(self.entities.items()):
            # Apply decay
            if isinstance(entity, Creature):
                # entity.stats.hp -= 1
                pass
            # Remove if dead
            if entity.stats.hp <= 0:
                self.mark_delete(entity_id)
                continue

            # Run AI
            if isinstance(entity, Creature):
                action, target_id, success = self.ai.step(entity, self)
                self.action_history.append((entity_id, action, target_id, success))

    def set_current_player(self, id):
        self.player = self.entities[id]

    def reset(self, seed=None, options=None):
        self.grid = [["-1"] * self.config.size for _ in range(self.config.size)]
        self.entities = {}
        self.creature_counter = 0
        self.resource_counter = 0
        self.step_count = 0
        self.action_history = []

        self.populate()

        # [ value for all location]
        return self.observation(), {"info": "Environement reset"}

    def step(self, action) -> (Any, Any, Any, Any, Any):

        terminated = False
        truncated = False
        target = None
        next_state = None
        reward = 0
        info = None
        action_int = action

        if self.player.stats.hp <= 0:
            self.mark_delete(self.player.id)
            terminated = True
            reward = -200
        else:
            action = self.int_to_action[int(action)]
            target_ids = self.pathfinder.get_adjacent_entities(
                self.player.location, self
            )

            entities = [self.get_entity(id) for id in target_ids]
            creatures = [entity for entity in entities if isinstance(entity, Creature)]
            resources = [entity for entity in entities if isinstance(entity, Resource)]

            if action == "attack" or action == "heal" or action == "reproduce":
                # find target creature
                if creatures:
                    target = creatures[0]
                else:
                    target = None

            elif action == "harvest":
                # find target resource
                if resources:
                    target = resources[0]
                else:
                    target = None

            info, reward = self.actions.set_action(
                action, c=self.player, target=target, env=self
            )

            # remove entity from environement
            deleted = [
                id for id, entity in self.entities.items() if entity.stats.hp <= 0
            ]
            if deleted:
                self.remove_deleted(deleted)

        # decay
        self.player.stats.hp -= 1
        next_state = self.observation(action_int)
        self.step_count += 1
        if self.step_count >= MAX_STEP_COUNT:
            truncated = True

        return next_state, reward, terminated, truncated, {}

    def close(self):
        pass
