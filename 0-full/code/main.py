import pygame
import sys
from level import Level

from settings import WIDTH, HEIGTH, TILESIZE, FPS
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

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.screen.fill("black")

            self.level.run()
            fps = self.clock.get_fps()
            # debug(f"FPS: {fps:.2f}")

            pygame.display.update()
            self.clock.tick(60)


if __name__ == "__main__":
    game = Game()
    game.run()
