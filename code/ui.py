import pygame
from player import Player
from settings import *


class UI:
    def __init__(self):

        # general
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)

        # bar setup
        self.health_bar_rect = pygame.Rect(10, 10, HEALTH_BAR_WIDTH, BAR_HEIGHT)
        self.energy_bar_rect = pygame.Rect(10, 34, ENERGY_BAR_WIDTH, BAR_HEIGHT)

        # convert weapon dictionary
        self.weapon_graphics = []
        for weapon in weapon_data.values():
            path = weapon["graphic"]
            self.weapon_graphics.append(pygame.image.load(path).convert_alpha())

        # convert weapon dictionary
        self.magic_graphics = []
        for magic in magic_data.values():
            path = magic["graphic"]
            self.magic_graphics.append(pygame.image.load(path).convert_alpha())

    def show_bar(self, current_amount, max_amount, bg_rect: pygame.Rect, color):
        # draw bg and border
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)

        # draw current rect
        ratio = current_amount / max_amount
        current_width = bg_rect.width * ratio

        current_rect = bg_rect.copy()
        current_rect.width = current_width

        pygame.draw.rect(self.display_surface, color, current_rect)

    def show_exp(self, exp):
        text_surf = self.font.render(str(int(exp)), False, TEXT_COLOR)
        x = self.display_surface.get_size()[0] - 20
        y = self.display_surface.get_size()[1] - 20

        text_rect = text_surf.get_rect(bottomright=(x, y))

        # draw background
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, text_rect.inflate(20, 20))
        # draw border
        pygame.draw.rect(
            self.display_surface, UI_BORDER_COLOR, text_rect.inflate(20, 20), width=3
        )
        # draw text
        self.display_surface.blit(text_surf, text_rect)

    def selection_box(self, left, top, has_switched):
        # when cooldown (can switch / has switch) is on, draw active border, else inactive border
        bg_rect = pygame.Rect(left, top, ITEM_BOX_SIZE, ITEM_BOX_SIZE)
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect)
        if has_switched:
            pygame.draw.rect(self.display_surface, UI_BORDER_COLOR_ACTIVE, bg_rect, 3)
        else:
            pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3)
        return bg_rect

    def weapon_overlay(self, weapon_index, has_switched):
        bg_rect = self.selection_box(10, 630, has_switched)
        weapon_surf = self.weapon_graphics[weapon_index]
        weapon_rect = weapon_surf.get_rect(center=bg_rect.center)

        self.display_surface.blit(weapon_surf, weapon_rect)

    def magic_overlay(self, magic_index, has_switched):
        bg_rect = self.selection_box(95, 630, has_switched)
        magic_surf = self.magic_graphics[magic_index]
        magic_rect = magic_surf.get_rect(center=bg_rect.center)

        self.display_surface.blit(magic_surf, magic_rect)

    def display(self, player: Player):
        self.show_bar(
            player.health, player.stats["health"], self.health_bar_rect, HEALTH_COLOR
        )

        self.show_bar(
            player.energy, player.stats["energy"], self.energy_bar_rect, ENERGY_COLOR
        )
        self.show_exp(player.exp)

        self.weapon_overlay(player.weapon_index, not player.can_switch_weapon)
        self.magic_overlay(player.magic_index, not player.can_switch_magic)
