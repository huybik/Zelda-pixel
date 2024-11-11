import pygame
from player import Player
from settings import (
    UI_FONT,
    UI_FONT_SIZE,
    UI_BG_COLOR,
    UPGRADE_BG_COLOR_SELECTED,
    UI_BORDER_COLOR_ACTIVE,
    UI_BORDER_COLOR,
    TEXT_COLOR,
    TEXT_COLOR_SELECTED,
    BAR_COLOR,
    BAR_COLOR_SELECTED,
)


class Upgrade:
    def __init__(self, player: Player):
        # general setup
        self.display_surface = pygame.display.get_surface()
        self.player = player
        self.attribute_nr = len(player.stats)
        self.attribute_names = list(player.stats.keys())
        self.max_values = list(player.max_stats.values())
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)

        # item creation
        self.width = self.display_surface.get_size()[0] // 6
        self.height = self.display_surface.get_size()[1] * 0.8
        self.create_items()

        # selection system
        self.selection_index = 0
        self.selection_time = None
        self.can_move = True

    def input(self):
        keys = pygame.key.get_pressed()
        if self.can_move:
            if keys[pygame.K_RIGHT] and self.selection_index < self.attribute_nr - 1:
                self.selection_index += 1
                self.selection_time = pygame.time.get_ticks()
                self.can_move = False
            elif keys[pygame.K_LEFT] and self.selection_index >= 1:
                self.selection_index -= 1
                self.selection_time = pygame.time.get_ticks()
                self.can_move = False
            elif keys[pygame.K_SPACE]:
                item: Item = self.item_list[self.selection_index]
                item.trigger(self.player)
                self.selection_time = pygame.time.get_ticks()
                self.can_move = False

    def selection_cooldown(self):
        if not self.can_move:
            current_time = pygame.time.get_ticks()
            if current_time - self.selection_time >= 100:
                self.can_move = True

    def create_items(self):
        self.item_list = []

        for index, item in enumerate(range(self.attribute_nr)): 
            # horizontal position
            full_width = self.display_surface.get_size()[0]
            increment = full_width // self.attribute_nr
            left = (item * increment) + (increment - self.width) // 2

            # vertical position
            top = self.display_surface.get_size()[1] * 0.1

            # create object
            item = Item(left, top, self.width, self.height, index, self.font)
            self.item_list.append(item)

    def display(self):
        self.input()
        self.selection_cooldown()

        for index, item in enumerate(self.item_list):
            name = self.attribute_names[index]
            value = self.player.get_value_by_index(index)
            max_value = self.max_values[index]
            cost = self.player.get_cost_by_index(index)
            item.display(
                self.display_surface, self.selection_index, name, value, max_value, cost
            )


class Item:
    def __init__(self, l, t, w, h, index, font: pygame.font.Font):
        self.rect = pygame.Rect(l, t, w, h)
        self.index = index
        self.font = font

    def display_text(self, surface, name, cost, selected):
        # title
        color = TEXT_COLOR_SELECTED if selected else TEXT_COLOR
        title_surf = self.font.render(name, False, color)
        title_rect = title_surf.get_rect(
            midtop=self.rect.midtop + pygame.math.Vector2(0, 20)
        )
        # cost
        cost_surf = self.font.render(f"{int(cost)}", False, color)
        cost_rect = cost_surf.get_rect(
            midbottom=self.rect.midbottom - pygame.math.Vector2(0, 20)
        )

        # draw
        surface.blit(title_surf, title_rect)
        surface.blit(cost_surf, cost_rect)

    def display_bar(self, surface, value, max_value, selected):

        # drawing setup
        top = self.rect.midtop + pygame.math.Vector2(0, 60)
        bottom = self.rect.midbottom - pygame.math.Vector2(0, 60)
        color = BAR_COLOR_SELECTED if selected else BAR_COLOR

        full_height = bottom.y - top.y
        relative_number = pygame.math.Vector2(0, (value / max_value) * full_height)
        value_rect = pygame.Rect(top.x - 15, bottom.y - relative_number.y, 30, 10)

        pygame.draw.line(surface, color, top, bottom, 5)
        pygame.draw.rect(surface, color, value_rect)

    def trigger(self, player):
        upgrade_attribute = list(player.stats.keys())[self.index]

        if (
            player.exp >= player.upgrade_cost[upgrade_attribute]
            and player.stats[upgrade_attribute] < player.max_stats[upgrade_attribute]
        ):
            player.exp -= player.upgrade_cost[upgrade_attribute]
            player.stats[upgrade_attribute] += 0.1 * player.max_stats[upgrade_attribute]
            player.upgrade_cost[upgrade_attribute] *= 1.4

        if player.stats[upgrade_attribute] > player.max_stats[upgrade_attribute]:
            player.stats[upgrade_attribute] = player.max_stats[upgrade_attribute]

    def display(self, surface, selection_num, name, value, max_value, cost):

        if self.index == selection_num:
            pygame.draw.rect(surface, UPGRADE_BG_COLOR_SELECTED, self.rect)
            pygame.draw.rect(surface, UI_BORDER_COLOR_ACTIVE, self.rect, 4)
            selected = True
        else:
            pygame.draw.rect(surface, UI_BG_COLOR, self.rect)
            pygame.draw.rect(surface, UI_BORDER_COLOR, self.rect, 4)
            selected = False

        self.display_text(surface, name, cost, selected)
        self.display_bar(surface, value, max_value, selected)
