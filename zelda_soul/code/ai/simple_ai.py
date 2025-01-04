from entities.creature import Creature
from environment.env import Environment
from entities.actions import Action
import random


class SimpleAI:
    def __init__(self):
        self.action = Action()
        self.action_dict = self.action.get_actions()

    def chose_action(self, c: Creature, env: Environment) -> str:
        return "move", (1, 2)

    def execute_action(self, action: str, param, c: Creature, env: Environment) -> None:
        if action == "move":
            self.action.move(c, target_location=param, env=env)
