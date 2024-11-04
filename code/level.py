import pygame
from player import Player
from tile import Tile
from settings import TILESIZE, weapon_data
from debug import debug
from support import import_csv_layout, import_folder
import random
from weapon import Weapon
from ui import UI
from enemy import Enemy
from entity import Entity
from particles import AnimationPlayer
from magic import MagicPlayer
from upgrade import Upgrade
from game_state import export_game_state  # Import the export function
from persona import API  # Import the API class
from camera import YSortCameraGroup

# import pygame_asyncio  # You'll need to install this package


class Level:
    def __init__(self) -> None:
        # get the display surface
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()
        self.enemies = []

        # persona
        self.chat_api = API()

        # user interface
        self.ui = UI()
        # self.text_bubble = TextBubble()

        # sprite setup
        self.create_map()

        # pause menu
        self.upgrade = Upgrade(self.player)

        # particles
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

        self.export_key = pygame.K_s  # Define the key to export game state

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
                            Tile(
                                (x, y), self.obstacle_sprites, sprite_type="boundary"
                            )  # use default empty surfade
                        elif sprite_type == "grass":
                            surface = random.choice(graphics[sprite_type])
                            Tile(
                                (x, y),
                                [
                                    self.visible_sprites,
                                    self.obstacle_sprites,
                                    self.attackable_sprites,
                                ],
                                sprite_type,
                                surface,
                            )
                        elif sprite_type == "object":
                            surface = graphics[sprite_type][int(col)]
                            Tile(
                                (x, y),
                                [self.visible_sprites, self.obstacle_sprites],
                                sprite_type,
                                surface,
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
                                    monster_name = "bamboo"
                                elif col == "391":
                                    monster_name = "spirit"
                                elif col == "392":
                                    monster_name = "raccoon"
                                else:
                                    monster_name = "squid"

                                self.enemies.append(
                                    Enemy(
                                        monster_name,
                                        (x, y),
                                        [
                                            self.visible_sprites,
                                            # self.obstacle_sprites,
                                            self.attack_sprites,
                                            self.attackable_sprites,
                                        ],
                                        self.obstacle_sprites,
                                        self.trigger_death_particles,
                                        self.add_exp,
                                        self.chat_api,
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

                        elif target_sprite.sprite_type == "enemy":
                            target_sprite: Enemy
                            # check if attack come from player
                            if attack_sprite.sprite_type != "enemy":
                                target_sprite.get_damage(self.player)

                    if target_sprite.sprite_type == "player":
                        attack_sprite: Enemy
                        # attack sprite can be weapon or enemy
                        if attack_sprite.sprite_type == "enemy":

                            damage = attack_sprite.attack()
                            if damage:
                                self.damage_player(
                                    damage,
                                    attack_sprite.attack_type,
                                )

        if not self.player.attacking:
            for attackable_sprite in self.attackable_sprites:
                if attackable_sprite.sprite_type == "enemy":
                    attackable_sprite.first_hit = False

    def damage_player(self, amount, attack_type):
        if self.player.vulnerable:
            self.player.vulnerable = False
            self.player.vulnerable_time = pygame.time.get_ticks()
            self.player.health -= amount

            # particles
            pos = self.player.rect.center
            self.animation_player.create_particles(
                attack_type, pos, [self.visible_sprites]
            )

            if self.player.health < 0:
                self.trigger_death_particles("player", self.player.rect.center)
                self.player.player_death_sound.play()
                # self.player.kill()

    def trigger_death_particles(self, particle_type, pos):

        self.animation_player.create_particles(particle_type, pos, self.visible_sprites)

    def create_magic(self, style, strength, cost):
        if style == "heal":
            self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])
        if style == "flame":
            self.magic_player.flame(
                self.player, strength, cost, [self.visible_sprites, self.attack_sprites]
            )

    def add_exp(self, amount):
        self.player.exp += amount

    def toggle_menu(self):
        self.game_paused = not self.game_paused

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == self.export_key:
                export_game_state(self)

    async def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.update()
            await self.visible_sprites.enemy_update(self.player)
            self.collision()
