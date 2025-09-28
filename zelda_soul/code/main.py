from __future__ import annotations

import asyncio
import os
from pathlib import Path
import pygame

from game.level import Level
from settings import WIDTH, HEIGTH, FPS, WATER_COLOR
from game.debug import debug
from dotenv import load_dotenv
import environment.env as env


BASE_DIR = Path(__file__).resolve().parent.parent
if Path.cwd() != BASE_DIR:
    os.chdir(BASE_DIR)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGTH))
        pygame.display.set_caption("Zelda")
        self.clock = pygame.time.Clock()

        self.env = env.Environment()
        self.level = Level(self.env)

        # sound
        main_sound = pygame.mixer.Sound("audio/main.ogg")
        main_sound.set_volume(0.5)
        main_sound.play(loops=-1)

    async def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        self.level.toggle_menu()

            self.screen.fill(WATER_COLOR)
            await self.level.run()
            fps = self.clock.get_fps()
            debug(f"FPS: {fps:.2f}")

            pygame.display.update()
            self.clock.tick(60)
            # await asyncio.sleep(0.001)


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
