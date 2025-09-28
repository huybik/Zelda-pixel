from __future__ import annotations

import pygame
from dotenv import load_dotenv

from .debug import debug
from .level import Level
from .resources import load_sound
from .settings import AUDIO_DIR, FPS, HEIGHT, WATER_COLOR, WIDTH


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Zelda Soul")
        self.clock = pygame.time.Clock()
        self.level = Level()

        main_sound = load_sound(AUDIO_DIR / "main.ogg")
        main_sound.set_volume(0.5)
        main_sound.play(loops=-1)

    def run(self):
        """Main synchronous game loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    self.level.toggle_menu()

            self.screen.fill(WATER_COLOR)
            self.level.run()

            fps = self.clock.get_fps()
            debug(f"FPS: {fps:.2f}")

            pygame.display.update()
            self.clock.tick(FPS)

        self.level.shutdown()
        pygame.quit()


def main() -> None:
    load_dotenv()
    Game().run()


if __name__ == "__main__":
    main()
