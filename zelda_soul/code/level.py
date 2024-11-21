import pygame
from player import Player
from tile import Tile
from settings import TILESIZE, INFERENCE_MODE
from debug import debug
from support import import_csv_layout, import_folder
import random
from weapon import Weapon
from ui import UI
from enemy import Enemy
from entity import Entity
from particles import AnimationPlayer

from upgrade import Upgrade
from camera import YSortCameraGroup
from magic import MagicPlayer
from persona import API
# from queue import PriorityQueue
import asyncio
from priorityqueue import PriorityQueueWithUpdate


class Level:
    def __init__(self) -> None:
        # get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.entities = []
        self.objects = []
        self.global_queue = PriorityQueueWithUpdate()
        self.decision_task = None

        # user interface
        self.ui = UI()
        self.api = API(mode=INFERENCE_MODE)
        # self.text_bubble = TextBubble()

        # sprite setup
        self.create_map()

        # pause menu
        self.upgrade = Upgrade(self.player)

        # particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)
        
        # global task queue for chat

    def create_map(self):
        layouts = {
            "boundary": import_csv_layout("../map/map_FloorBlocks.csv"),
            "grass": import_csv_layout("../map/map_Grass.csv"),
            "object": import_csv_layout("../map/map_Objects.csv"),
            "entities": import_csv_layout("../map/map_Entities.csv"),
        }
        graphics = {
            "grass": import_folder("../graphics/Grass"),
            "object": import_folder("../graphics/objects"),
        }

        for sprite_type, layout in layouts.items():
            for row_index, row in enumerate(layout):
                for col_index, col in enumerate(row):
                    # col is value of map plan
                    if col != "-1":
                        x = col_index * TILESIZE
                        y = row_index * TILESIZE
                        if sprite_type == "boundary":
                            full_name = "boundary"
                            Tile(
                                (x, y),
                                full_name,
                                self.obstacle_sprites,
                                sprite_type="boundary",
                            )  # use default empty surfade
                        elif sprite_type == "grass":
                            surface = random.choice(graphics[sprite_type])
                            full_name = "grass"
                            Tile(
                                (x, y),
                                full_name,
                                [
                                    self.visible_sprites,
                                    # self.obstacle_sprites,
                                    self.attackable_sprites,
                                ],
                                sprite_type,
                                surface,
                            )
                        elif sprite_type == "object":
                            surface = graphics[sprite_type][int(col)]
                            if int(col) <= 4 and int(col) > 1:
                                full_name = "resource"
                            elif int(col) > 14 and int(col) < 21:
                                full_name = "resource"
                            else:
                                full_name = "object"

                            full_name += f"{col_index}{row_index}"
                            self.objects.append(
                                Tile(
                                    (x, y),
                                    full_name,
                                    [self.visible_sprites, self.obstacle_sprites],
                                    sprite_type,
                                    surface,
                                )
                            )
                        if sprite_type == "entities":
                            if col == "394":  # 394 is player value on map plan
                                self.player = Player(
                                    (x, y),
                                    [self.visible_sprites, self.attackable_sprites],
                                    self.obstacle_sprites,
                                    self.create_magic,
                                )
                            else:
                                if col == "390":
                                    name = "bamboo"
                                elif col == "391":
                                    name = "spirit"
                                elif col == "392":
                                    name = "raccoon"
                                elif col == "393":
                                    name = "squid"
                                full_name = f"{name}{col_index}{row_index}"
                                self.entities.append(
                                    Enemy(
                                        name,
                                        full_name,
                                        (x, y),
                                        [
                                            self.visible_sprites,
                                            self.attack_sprites,
                                            self.attackable_sprites,
                                        ],
                                        self.obstacle_sprites,
                                        self.visible_sprites,
                                        self.api,
                                        self.global_queue
                                    )
                                )

        # 1st approach to draw sprite
        # self.visible_sprites.add(Player((64,64)))

        # 2nd approach
        # Player((64,64), [self.visible_sprites])

        self.weapon = Weapon(self.player, [self.visible_sprites, self.attack_sprites])
        # self.magic =

    def collision(self):

        # TODO: refactor this to not handle the logic
        for attack_sprite in self.attack_sprites:
            collision_sprites: list[Entity] = pygame.sprite.spritecollide(
                attack_sprite, self.attackable_sprites, dokill=False
            )
            if collision_sprites:
                for target_sprite in collision_sprites:
                    if target_sprite != attack_sprite:
                        if self.player.attacking:
                            if target_sprite.sprite_type == "grass":
                                target_sprite.kill()

                                # particles
                                pos = target_sprite.rect.center
                                offset = pygame.math.Vector2((0, 50))
                                for leaf in range(random.randint(2, 5)):
                                    self.animation_player.create_grass_particles(
                                        pos - offset, [self.visible_sprites]
                                    )

                            # player attack

                            elif target_sprite.sprite_type == "enemy":
                                if (
                                    attack_sprite.sprite_type == "magic"
                                    or attack_sprite.sprite_type == "weapon"
                                ):
                                    target_sprite.get_damage(self.player)

    def create_magic(self, entity: "Entity", style, strength, cost):
        if style == "heal":
            self.magic_player.heal(entity, strength, cost, [self.visible_sprites])
        if style == "flame":
            self.magic_player.flame(
                entity, strength, cost, [self.visible_sprites, self.attack_sprites]
            )

    def toggle_menu(self):
        self.game_paused = not self.game_paused

    async def run(self):

        # debugging
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.update()
            self.visible_sprites.enemy_update(
                self.player, self.entities, self.objects
            )
            self.collision()

           
            if not self.global_queue.empty():
                if self.decision_task is None or self.decision_task.done():
                    priority, task = self.global_queue.get()

                    self.decision_task = asyncio.create_task(
                        asyncio.wait_for(
                            task,
                            timeout=20.0,
                        )
                    )
                
            # Give control back to event loop to process background tasks
            await asyncio.sleep(0)
            
            # # Check if task failed
            # if self.decision_task is not None and self.decision_task.done():
            #     try:
            #         self.decision_task.result()
            #     except Exception as e:
            #         print(f"Task failed: {e}")


