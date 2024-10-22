import pygame
from player import Player
from settings import *


class UI:
    def __init__(self):

        # general
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)

        # bar setup
        self.health_bar_rect = pygame.rect.Rect(10, 10, HEALTH_BAR_WIDTH, BAR_HEIGHT)
        self.energy_bar_rect = pygame.Rect(10, 34, ENERGY_BAR_WIDTH, BAR_HEIGHT)

        # convert weapon dictionary
        self.weapon_graphic = []
        for weapon in weapon_data.values():
            path = weapon["graphic"]
            self.weapon_graphic.append(pygame.image.load(path))

    def show_bar(self, current_amount, max_amount, bg_rect: pygame.Rect, color):
        # draw bg
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        # self.energy_bar_rect = pygame.rect.Rect

        ratio = current_amount / max_amount
        current_width = bg_rect.width * ratio

        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)

        current_rect = bg_rect.copy()
        current_rect.width = current_width

        pygame.draw.rect(self.display_surface, color, current_rect)

    def display(self, player: Player):
        self.show_bar(
            player.health, player.stats["health"], self.health_bar_rect, HEALTH_COLOR
        )

        self.show_bar(
            player.energy, player.stats["energy"], self.energy_bar_rect, ENERGY_COLOR
        )
