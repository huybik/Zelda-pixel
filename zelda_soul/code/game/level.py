import pygame
from settings import TILESIZE, INFERENCE_MODE
from utils.support import import_folder, import_csv_layout
import random

from entities.resource import Resource
from entities.creature import Creature
from environment.env import Environment, EnvironmentConfig
from ai.simple_ai import SimpleAI
from .movement import keyboard_move
from .gresource import GameResource
from .gcreature import GameCreature
from .camera import YSortCameraGroup
from utils.support import to_grid, to_world

import asyncio

from typing import List, Dict, Union, TYPE_CHECKING


class Level:
    def __init__(self, env: Environment) -> None:

        self.display_surface = pygame.display.get_surface()
        self.visible_sprites = YSortCameraGroup()
        # self.obstacle_sprites = pygame.sprite.Group()

        self.env = env
        self.ai = SimpleAI()
        self.sprites: Dict[str, Union[GameCreature, GameResource]] = {}

        self.create_map()

        self.frame_count = 0

    def create_map(self):
        graphics = {
            "grass": import_folder("graphics/Grass"),
        }
        layout = import_csv_layout("map/map.csv")

        self.floor_surf = pygame.image.load("graphics/tilemap/ground.jpg").convert()
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

        for y, row in enumerate(layout):
            for x, cell in enumerate(row):

                if cell == "1":
                    resource = self.env._create_resource((x, y))

                    surface = random.choice(graphics["grass"])
                    self.sprites[resource.id] = GameResource(
                        resource,
                        surface,
                        self.visible_sprites,
                    )

                elif cell == "2":
                    creature = self.env._create_creature((x, y))
                    self.player = GameCreature(
                        creature,
                        self.visible_sprites,
                    )
                    self.sprites[creature.id] = self.player

                elif cell == "3":
                    creature = self.env._create_creature((x, y))
                    self.sprites[creature.id] = GameCreature(
                        creature,
                        self.visible_sprites,
                    )

    def move_input(self):
        direction = pygame.Vector2()
        keys = pygame.key.get_pressed()
        # movement
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            direction.x = 1
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            direction.x = -1
        # weapon
        else:
            direction.x = 0

        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            direction.y = 1
        elif keys[pygame.K_w] or keys[pygame.K_UP]:
            direction.y = -1
        else:
            direction.y = 0

        return direction

    def sync_env(self):
        # remove all dead creatures and resources f
        # remove sprite
        deleted = [
            id
            for id, entity in self.env.entities.items()
            if entity.status.deleted is True
        ]
        if deleted:
            for id in deleted:
                self.sprites[id].kill()
                # remove entity from environement
            self.env.remove_deleted(deleted)

        # move remain creatures to new env location
        # TODO: move smoothly
        for k, sprite in self.sprites.items():
            new_location = to_world(sprite.entity.location)
            if sprite.location != new_location:
                sprite.location = new_location
                sprite.rect.center = new_location
                

    async def run(self):
        self.frame_count += 1
        # trigger env step
        if self.frame_count >= 64:
            self.env.env_step()
            self.sync_env()
            self.frame_count = 0

        # keyboard move
        direction = self.move_input()
        if direction.magnitude() > 0:
            keyboard_move(self.player, direction, self.visible_sprites)

        self.visible_sprites.custom_draw(self.player)
        self.visible_sprites.update()
        await asyncio.sleep(0.01)
