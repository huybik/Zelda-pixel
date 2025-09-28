from __future__ import annotations
import pygame
from level import Level
from settings import WIDTH, HEIGTH
from debug import debug
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Set working directory to the script's root
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGTH))
        pygame.display.set_caption("Zelda Soul")
        self.clock = pygame.time.Clock()
        self.level = Level()

        # Sound
        main_sound = pygame.mixer.Sound("../audio/main.ogg")
        main_sound.set_volume(0.5)
        main_sound.play(loops=-1)

    def run(self):
        """Main synchronous game loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        self.level.toggle_menu()

            self.screen.fill("#71ddee")  # WATER_COLOR
            self.level.run()
            
            fps = self.clock.get_fps()
            debug(f"FPS: {fps:.2f}")

            pygame.display.update()
            self.clock.tick(60)
        
        # Shutdown gracefully
        self.level.shutdown()
        pygame.quit()
        sys.exit()

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    load_dotenv()
    main()
