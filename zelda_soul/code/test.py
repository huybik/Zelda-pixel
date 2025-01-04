from environment.env import Environment, EnvironmentConfig
from environment.pathfinder import Pathfinder
from ai.simple_ai import SimpleAI
import random
import numpy as np
from entities.actions import Action


def seed_everything():
    random.seed(0)
    np.random.seed(0)


if __name__ == "__main__":
    # seed_everything()
    config = EnvironmentConfig(size=5, n_creature=2, n_resource=2, resource_amount=100)
    env = Environment(config)
    pathfinder = Pathfinder()

    env.populate()
    env.display()
    print(env.get_entity("c1").stats)
    print()

    ai = SimpleAI()
    a = Action()
    c = env.get_entity("c1")
    action, param = ai.chose_action(c, env)
    ai.execute_action(action, param, c, env)
    env.display()

    c2 = env.get_entity("c2")
    print(f"hp: {c2.stats.hp}")
    print(f"attack: {a.attack(c, c2)}")
    print(f"hp: {c2.stats.hp}")

    print(f"heal result: {a.heal(c, c2)}")
    print(f"hp: {c2.stats.hp}")

    result = a.reproduce(c, c2, env)
    print(f"reproduce result: {result.stats}")

    c.stats.energy = 1
    target = env.get_entity("r1")
    print(f"hp: {c.stats.hp}")
    print(f"hp: {target.stats.amount}")
    print(f"harvest result: {a.harvest(c, target)}")
    print(f"hp: {c.stats.hp}")
    print(f"hp: {target.stats.amount}")

    print(f"energy: {c.stats.energy}")
    print(f"chill: {a.chill(c)}")
    print(f"energy: {c.stats.energy}")

    # test a star path finding
    env.display()
    path = pathfinder.a_star_path_finder(c.location, c2.location, env)
    print(path)
