from typing import TYPE_CHECKING, Union
from environment.pathfinder import Pathfinder

if TYPE_CHECKING:
    from ..environment.env import Environment
    from .creature import Creature
    from .resource import Resource


class Move:
    def __init__(self):
        self.pathfinder = Pathfinder()

    def move_to_target_entity(
        self, c: "Creature", entity: Union["Creature", "Resource"], env: "Environment"
    ) -> bool:

        start = c.location
        goal = entity.location
        path = self.pathfinder(start, goal, env)
        end = path[-1]
        # move to the max range limit by move speed for each step
        if len(path) > c.stats.move_speed:
            end = path[c.stats.move_speed]

        self.pathfinder.relocate(c, end, env)
