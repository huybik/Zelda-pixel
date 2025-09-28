import pygame
from typing import TYPE_CHECKING

from .settings import GRAPHICS_DIR

if TYPE_CHECKING:
    from .ai_manager import AIManager


class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()

        # general setup
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2

        self.offset = pygame.math.Vector2()

        # creating the floor, must load first before other things
        self.floor_surf = pygame.image.load(str(GRAPHICS_DIR / "tilemap" / "ground.png")).convert()

    def custom_draw(self, player: pygame.sprite.Sprite):
        # offset for camera to middle of player
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # sort which sprite to display first by y axis -> obstacle above player # is drawn first and obstruct player, or is obstructed if player below
        self.display_surface.blit(
            self.floor_surf, -self.offset
        )  # floor texture is anchored at the origin, so offset alone is enough

        # self.sprites are all sprite in current sprite group
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.y):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

    def enemy_update(self, player, entities, objects):
        enemy_sprites = [
            sprite
            for sprite in self.sprites()
            if hasattr(sprite, "sprite_type") and sprite.sprite_type == "enemy"
        ]

        # Run regular updates for all enemies
        for enemy in enemy_sprites:
            enemy.enemy_update(player, entities, objects)
