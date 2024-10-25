import pygame
from entity import Entity
from support import import_folder


class Enemy(Entity):
    def __init__(self, monster_name, pos, groups, obstacle_sprite):
        super().__init__(groups)

        # graphic setup
        self.import_graphics(monster_name)
        self.status = "idle"
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)
        self.animations = {"idle": [], "move": [], "attack": []}

    def update(self):
        pass

    # self.move
