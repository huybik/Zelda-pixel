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

        self.text_bubble = TextBubble()

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


class TextBubble:
    def __init__(self, font_size=16):
        self.display_surface = pygame.display.get_surface()
        self.font = pygame.font.Font(UI_FONT, font_size)
        self.padding = 10
        self.border_width = 2
        self.tail_height = 10
        self.max_width = 200  # Maximum width before text wrapping

    def _wrap_text(self, text, max_width):
        """Split text into lines that fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            test_surface = self.font.render(test_line, True, TEXT_COLOR)

            if test_surface.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def draw(self, text, target_rect, offset_y=30):
        # Wrap text if needed
        lines = self._wrap_text(text, self.max_width)

        # Calculate bubble dimensions
        line_surfaces = [self.font.render(line, True, TEXT_COLOR) for line in lines]
        line_heights = [surf.get_height() for surf in line_surfaces]
        max_line_width = max(surf.get_width() for surf in line_surfaces)

        # Calculate bubble size
        bubble_width = max_line_width + (self.padding * 2)
        bubble_height = sum(line_heights) + (self.padding * 2)

        # Calculate bubble position (centered above target)
        bubble_x = target_rect.centerx - (bubble_width // 2)
        bubble_y = target_rect.top - bubble_height - self.tail_height - offset_y

        # Draw bubble background
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
        pygame.draw.rect(
            self.display_surface, UI_BG_COLOR, bubble_rect, border_radius=8
        )
        pygame.draw.rect(
            self.display_surface,
            UI_BORDER_COLOR,
            bubble_rect,
            width=self.border_width,
            border_radius=8,
        )

        # Draw tail
        tail_points = [
            (target_rect.centerx, bubble_rect.bottom),
            (target_rect.centerx - 10, bubble_rect.bottom - self.tail_height),
            (target_rect.centerx + 10, bubble_rect.bottom - self.tail_height),
        ]
        pygame.draw.polygon(self.display_surface, UI_BG_COLOR, tail_points)
        pygame.draw.polygon(
            self.display_surface, UI_BORDER_COLOR, tail_points, width=self.border_width
        )

        # Draw text
        current_y = bubble_y + self.padding
        for surface in line_surfaces:
            text_rect = surface.get_rect(centerx=bubble_rect.centerx, top=current_y)
            self.display_surface.blit(surface, text_rect)
            current_y += surface.get_height()
