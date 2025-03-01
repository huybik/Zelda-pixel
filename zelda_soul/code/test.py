from environment.env import Environment, EnvironmentConfig
from environment.pathfinder import Pathfinder
from ai.simple_ai import SimpleAI
import random
import numpy as np
from entities.actions import Action
from stable_baselines3 import PPO

# from ai.ppo_sonet import train, run
from ai.ppo_stablebaseline import train, run


import asyncio
import pygame

from settings import WIDTH, HEIGTH, FPS, WATER_COLOR
from dotenv import load_dotenv

from game.level import Level
from game.debug import debug

# from animation.debug import debug


def seed_everything():
    random.seed(0)
    np.random.seed(0)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGTH))
        pygame.display.set_caption("Zelda")
        self.clock = pygame.time.Clock()
        self.env = Environment(EnvironmentConfig())
        self.level = Level(self.env)

        # # sound
        # main_sound = pygame.mixer.Sound("../audio/main.ogg")
        # main_sound.set_volume(0.5)
        # main_sound.play(loops=-1)

        self.frame_count = 0

    async def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        # self.level.toggle_menu()
                        pass

            self.screen.fill(WATER_COLOR)
            await self.level.run()
            fps = self.clock.get_fps()
            debug(f"FPS: {fps:.2f}")

            pygame.display.update()
            self.clock.tick(FPS)

            # await asyncio.sleep(0.001)


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":

    seed_everything()

    load_dotenv()
    # asyncio.run(main())

    env = Environment()
    pathfinder = Pathfinder()

    env.populate()
    env.render()
    print(env.get_entity("c1").stats)
    print()

    ai = SimpleAI()
    a = Action()
    c = env.get_entity("c1")
    c2 = env.get_entity("c2")
    r2 = env.get_entity("r2")
    r1 = env.get_entity("r1")

    action = ai.chose_action(c, env)
    ai.execute_action(c, action, env)
    env.render()

    c2 = env.get_entity("c2")
    print(f"hp: {c2.stats.hp}")
    print(f"attack: {a.attack(c, c2)}")
    print(f"hp: {c2.stats.hp}")

    print(f"heal result: {a.heal(c, c2)}")
    print(f"hp: {c2.stats.hp}")

    c.stats.energy = 20
    c3 = a.reproduce(c, c2, env)
    print(f"reproduce result: {c3.stats}")

    c.stats.energy = 1
    target = env.get_entity("r1")
    print(f"hp: {c.stats.hp}")
    print(f"hp: {target.stats.hp}")
    print(f"harvest result: {a.harvest(c, target)}")
    print(f"hp: {c.stats.hp}")
    print(f"hp: {target.stats.hp}")

    print(f"energy: {c.stats.energy}")
    print(f"chill: {a.chill(c)}")
    print(f"energy: {c.stats.energy}")

    # test a star path finding
    env.render()
    c.stats.move_speed = 10
    path = pathfinder.a_star_path_finder(c.location, c2.location, env)
    print(path)

    env.set_current_player("c1")
    state, reward, terminated, truncated, _ = env.step(0)
    env.render()

    # attack step
    print(f"hp: {c3.stats.hp}")
    state, reward, terminated, truncated, _ = env.step(4)
    print(f"hp: {c3.stats.hp}")

    # print(f"hp: {r2.stats.hp}")
    # state, reward, terminated, truncated, _ = env.step(6)
    # print(f"hp: {r2.stats.hp}")

    state, _ = env.reset()
    print(state)

    # try:
    #     model = PPO.load("ppo_best_model")
    # except Exception as e:
    #     print(f"{e}, training new model")
    #     model = None
    model = None
    model = train(model, total_timesteps=700000)
    run(model)
