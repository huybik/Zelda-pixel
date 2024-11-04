from __future__ import annotations

import asyncio
import pygame

# import pygame_asyncio
from level import Level

from settings import WIDTH, HEIGTH, FPS, WATER_COLOR
from debug import debug

from pygame.locals import *


class Game:
    def __init__(self):

        pygame.init()
        # flags = DOUBLEBUF
        self.screen = pygame.display.set_mode((WIDTH, HEIGTH))
        pygame.display.set_caption("Zelda")

        self.clock = pygame.time.Clock()

        self.level = Level()

        # sound
        main_sound = pygame.mixer.Sound("../audio/main.ogg")
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

                self.level.handle_event(event)

            self.screen.fill(WATER_COLOR)
            await self.level.run()
            fps = self.clock.get_fps()
            # debug(f"FPS: {fps:.2f}")

            pygame.display.update()
            self.clock.tick(FPS)


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":
    # Initialize pygame_asyncio
    # pygame_asyncio.init()
    # Run the async game loop
    asyncio.run(main())
