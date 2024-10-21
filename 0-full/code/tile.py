import pygame
from settings import TILESIZE

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprite_type, surface = pygame.Surface((TILESIZE, TILESIZE))):
        super().__init__(groups)
        # define image for sprite
        self.sprite_type = sprite_type
        self.image = surface
        # define rect position for sprite
        if sprite_type == 'object':
            # minus object size
            self.rect = self.image.get_rect(topleft = (pos[0], pos[1] - TILESIZE)) 
        else:
            self.rect = self.image.get_rect(topleft = pos)
        
        # define hitbox 
        self.hitbox = self.rect.inflate(0,-40)
        