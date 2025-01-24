import pygame
from settings import TILESIZE, HITBOX_OFFSET
from entities.resource import Resource
from utils.support import to_world


class GameResource(pygame.sprite.Sprite):
    def __init__(
        self,
        resource: Resource,
        surface: pygame.Surface,
        groups: pygame.sprite.Group,
        # surface=pygame.Surface((TILESIZE, TILESIZE)),
    ):
        super().__init__(groups)

        self.entity = resource
        # self.hitbox = self.rect

        self.id = self.entity.id
        self.location = to_world(resource.location)

        self.image = surface
        self.rect = self.image.get_rect(center=self.location)
