import pygame
import random
from .animation import AnimationPlayer
from entities.actions import Action
from entities.creature import Creature
from entities.resource import Resource
from environment.env import Environment
from environment.pathfinder import Pathfinder
from game.animation import AnimationPlayer, Animate
from utils.support import to_world, to_grid


class GameCreature(pygame.sprite.Sprite):
    def __init__(self, creature: Creature, groups: pygame.sprite.Group):
        super().__init__(groups)
        self.actions = Action()
        self.pathfinder = Pathfinder()
        self.animations = AnimationPlayer()
        self.entity = creature
        self.group = groups

        # creature attributes
        self.id = self.entity.id
        self.location = to_world(self.entity.location)
        self.action = "chill"
        self.type = "bamboo"

        # animation
        self.animations: Animate = AnimationPlayer().create_animations(self.type)
        self.image = self.animations.animate(self.action)
        self.rect = self.image.get_rect(center=self.location)

        self.direction = pygame.Vector2()

        # stats

    def update(self):
        # self.location = to_world(self.creature.location)
        self.image = self.animations.animate(self.action)
