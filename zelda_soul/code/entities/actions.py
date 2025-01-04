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
        self.helper = ActionHelper()

    def move(
        self, c: "Creature", target_location: Location, env: "Environment"
    ) -> bool:
        current_x, current_y = c.location
        target_x, target_y = target_location

        distance = abs(target_x - current_x) + abs(target_y - current_y)
        if distance <= c.stats.move_speed:
            result = self.pathfinder.relocate(c, target_location, env)
            if result:
                c.status.move += 1
                return True
        return False

    def attack(self, c: "Creature", target: "Creature") -> bool:
        damage = int(c.stats.attack * c.stats.attack_speed)
        self.helper.receive_damage(target, damage)
        if target.stats.hp == 0:
            c.status.killed += 1
        c.status.attack += 1
        return True

    def heal(self, c: "Creature", target: "Creature") -> bool:
        if c.stats.energy > 0:
            heal_amount = c.stats.heal
            c.stats.energy = max(c.stats.energy - heal_amount, 0)
            target.stats.hp = min(target.stats.hp + heal_amount, target.stats.max_hp)
            c.status.heal += 1
            return True
        return False

    def chill(self, c: "Creature") -> None:
        c.stats.energy = min(c.stats.energy + c.stats.chill, c.stats.max_energy)
        c.status.chill += 1
        return True

    def harvest(self, c: "Creature", r: "Resource") -> bool:
        if c.stats.energy > 0:
            harvest_amount = c.stats.harvest
            c.stats.energy = max(c.stats.energy - harvest_amount, 0)
            c.stats.hp = min(c.stats.hp + harvest_amount, c.stats.max_hp)
            if r.stats.amount > 0:
                r.stats.amount = max(r.stats.amount - harvest_amount, 0)
                c.status.harvest += 1
                if r.stats.amount == 0:
                    c.status.collected += 1
                return True
        return False

    def reproduce(
        self, c: "Creature", partner: "Creature", env: "Environment"
    ) -> Optional["Creature"]:
        valid_cells = self.pathfinder.get_valid_adjacent_cell(c.location, env)
        if not valid_cells:
            return False

        child_genome = self.helper._mix_genomes(c, partner)
        child = env._add_creature(location=valid_cells[0], genome=child_genome)
        c.stats.energy = 0  # reset energy
        c.status.reproduced += 1
        return child

    # def decay(self, creature: "Creature") -> None:
    #     creature.stats.stats.hp -= int((self.n_bits - self.stats.decay))

    def get_actions(self) -> List[str]:
        return [
            ("move", "move to a new location"),
            ("attack", "attack another creature"),
            ("heal", "heal self or another creature"),
            ("harvest", "harvest a target resource"),
            ("chill", "rest and recover energy"),
            ("reproduce", "reproduce with another creature"),
        ]


class ActionHelper:
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
