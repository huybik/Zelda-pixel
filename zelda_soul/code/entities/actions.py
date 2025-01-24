from typing import TYPE_CHECKING, Tuple, List, Dict, Union, Optional, TypeAlias
import random
from environment.pathfinder import Pathfinder

if TYPE_CHECKING:
    from ..environment.env import Environment
    from .creature import Creature
    from .resource import Resource

Location: TypeAlias = Tuple[int, int]


class Action:
    def __init__(self) -> None:
        self.pathfinder = Pathfinder()

    def move(
        self, c: "Creature", target_location: Location, env: "Environment"
    ) -> Tuple[bool, int]:
        current_x, current_y = c.location
        target_x, target_y = target_location
        # check out of bounds
        if (
            0 <= target_x < env.config.size
            and 0 <= target_y < env.config.size
            and env.grid[target_y][target_x] == "-1"
            and c.stats.energy > 0
        ):
            # check distance
            distance = abs(target_x - current_x) + abs(target_y - current_y)
            if distance <= c.stats.move_speed:
                result = self.pathfinder.relocate(c, target_location, env)
                c.stats.energy -= 1
                if result:
                    c.status.move += 1
                    return True
        return False
    
    def chill(self, c: "Creature", target = None, env = None) -> None:
        c.stats.energy = min(c.stats.energy + c.stats.chill, c.stats.max_energy)
        c.status.chill += 1
        return True
    
    def attack(self, c: "Creature", target: "Creature", env = None) -> Tuple[bool, int]:
        if not target or c.stats.energy <= 0:
            return False
        damage = int(c.stats.attack * c.stats.attack_speed)
        self.receive_damage(target, damage)
        c.stats.energy -= 1
        c.status.attack += 1
        
        if target.stats.hp == 0:
            c.status.killed += 1
            return True
        return True

    def heal(self, c: "Creature", target: Optional["Creature"] = None, env = None) -> Tuple[bool, int]:
        if c.stats.energy <= 0:
            return False
        heal_amount = c.stats.heal
        # c.stats.energy = max(c.stats.energy - heal_amount, 0)
        if target == "self":
            c.stats.hp = min(c.stats.hp + heal_amount, c.stats.max_hp)
        else:
            if not target:
                return False
            target.stats.hp = min(target.stats.hp + heal_amount, target.stats.max_hp)
        c.stats.energy -= 1
        c.status.heal += 1
        return True

    def harvest(self, c: "Creature", r: "Resource", env = None) -> Tuple[bool, int]:
        if not r or c.stats.energy <= 0:
            return False
        harvest_amount = c.stats.harvest
        c.stats.energy -= 1
        c.stats.hp = min(c.stats.hp + harvest_amount, c.stats.max_hp)
        c.stats.energy = min(c.stats.energy + harvest_amount, c.stats.max_energy)
        if r.stats.hp > 0:
            r.stats.hp = max(r.stats.hp - harvest_amount, 0)
            c.status.harvest += 1
            if r.stats.hp == 0:
                c.status.collected += 1
                return True
            return True

    def reproduce(
        self, c: "Creature", partner: "Creature", env: "Environment"
    ) -> Tuple[Optional["Creature"], int]:  # Optional["Creature"]:
        valid_cells = self.pathfinder.get_valid_adjacent_cell(c.location, env)
        if not valid_cells or not partner or c.stats.energy < c.stats.max_energy/2:
            return False
        child_genome = self._mix_genomes(c, partner)
        child = env._create_creature(location=valid_cells[0], genome=child_genome)
        c.stats.energy = 0  # reset energy
        c.status.reproduced += 1
        return child

    # def decay(self, creature: "Creature") -> None:
    #     creature.stats.stats.hp -= int((self.n_bits - self.stats.decay))

    def get_actions(self) -> Dict[str, str]:
        return {
            "move_up": "move to a new location",
            "move"
            "attack": "attack another creature",
            "heal": "heal self or another creature",
            "harvest": "harvest a target resource",
            "chill": "rest and recover energy",
            "reproduce": "reproduce with another creature",
        }


    def _mix_genomes(self, a: "Creature", b: "Creature"):
        child_genome = {}
        a_genome = a.genome
        b_genome = b.genome
        for key in a_genome.keys():
            child_genome[key] = []
            for i in range(len(a_genome[key])):
                gene = a_genome[key][i] if random.random() < 0.5 else b_genome[key][i]
                child_genome[key].append(gene)
        return child_genome

    def receive_damage(self, c: "Creature", damage: int) -> bool:
        actual_damage = max(damage - c.stats.resistance, 0)
        c.stats.hp = max(c.stats.hp - actual_damage, 0)
        return True
    
    def set_action(self, action: str, c: "Creature", target: Union["Creature", "Resource"], env: "Environment"):
        reward = -1
        result = None

        # Define movement actions
        movement_actions = {
            "move_up": (0, -1),
            "move_down": (0, 1),
            "move_left": (-1, 0),
            "move_right": (1, 0),
        }

        if action in movement_actions:
            dx, dy = movement_actions[action]
            target_location = (c.location[0] + dx, c.location[1] + dy)
            move_result = self.move(c, target_location, env)
            reward = 1 if move_result else -1
            return move_result, reward

        # Define other actions
        action_methods = {
            "attack": lambda c, target, env:  self.attack(c, target, None),
            "heal_other": lambda c, target, env: self.heal(c, target, None),
            "harvest": lambda c, target, env: self.harvest(c, target, None),
            
        }

        if action in action_methods:
            result = action_methods[action](c, target, env)
            reward = 1 if result else -1
        
        if action == "heal_self":
            result =  self.heal(c, target="self", env=None),
            reward = -1 if result else -2
        
        if action == "chill":
            self.chill(c, None, None)
            reward = -1

        if action == "reproduce":
            result = self.reproduce(c, target, env)
            reward = 20 if result else -1

        return result, reward
    