import pygame
from .settings import TILESIZE, HITBOX_OFFSET


class Tile(pygame.sprite.Sprite):
    def __init__(
        self,
        pos,
        full_name,
        groups,
        sprite_type,
        surface=pygame.Surface((TILESIZE, TILESIZE)),
    ):
        super().__init__(groups)
        self.full_name = full_name
        # define image for sprite
        self.sprite_type = sprite_type
        self.image = surface
        # define rect position for sprite
        if sprite_type == "object":
            # minus object size
            self.rect = self.image.get_rect(
                topleft=(pos[0] - TILESIZE, pos[1] - TILESIZE)
            )
            self.hitbox = self.rect.inflate(0, HITBOX_OFFSET["object"])
        else:  # invisible and grass
            self.rect = self.image.get_rect(topleft=pos)
            self.hitbox = self.rect.inflate(0, HITBOX_OFFSET[sprite_type])
