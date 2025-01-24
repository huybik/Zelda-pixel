from entities.creature import Creature
from entities.actions import Action
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from environment.env import Environment
    from entities.creature import Creature


class SimpleAI:
    def __init__(self):
        self.action = Action()
        self.action_dict = self.action.get_actions()

    def chose_action(self, c: "Creature", env: "Environment") -> str:
        return ("move", (3, 1))

    def execute_action(self, c: "Creature", action: str, env: "Environment") -> None:
        action, target = action
        if action == "move":
            return self.action.move(c, target_location=target, env=env)

    def step(self, c: "Creature", env: "Environment"):
        action = self.chose_action(c, env)
        result = self.execute_action(c, action, env)
        return action[0], action[1], result
