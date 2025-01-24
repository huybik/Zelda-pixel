from typing import TYPE_CHECKING, Union
from environment.pathfinder import Pathfinder

if TYPE_CHECKING:
    from ..environment.env import Environment
    from .creature import Creature
    from .resource import Resource


class Move:
    def __init__(self):
        self.pathfinder = Pathfinder()

    