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


class Level:
    def __init__(self) -> None:
        # get the display surface
        self.display_surface = pygame.display.get_surface()

        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()

        self.create_map()

        self.ui = UI()

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
                                (x, y), self.obstacle_sprites, sprite_type
                            )  # use default empty surfade
                        if sprite_type == "grass":
                            surface = random.choice(graphics[sprite_type])
                            Tile(
                                (x, y),
                                [self.visible_sprites, self.obstacle_sprites],
                                sprite_type,
                                surface,
                            )
                        if sprite_type == "object":
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
                                    [self.visible_sprites],
                                    self.obstacle_sprites,
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

                                Enemy(
                                    monster_name,
                                    (x, y),
                                    [self.visible_sprites],
                                    self.obstacle_sprites,
                                )

        # 1st approach to draw sprite
        # self.visible_sprites.add(Player((64,64)))

        # 2nd approach
        # Player((64,64), [self.visible_sprites])

        self.weapon = Weapon(self.player, [self.visible_sprites])
        # self.magic =

    def run(self):
        # update and draw the game
        self.visible_sprites.custom_draw(self.player)
        self.visible_sprites.update()
        self.visible_sprites.enemy_update(self.player)
        self.ui.display(self.player)


class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()

        # general setup
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2

        self.offset = pygame.math.Vector2()

        # creating the floor, must load first before other things
        self.floor_surf = pygame.image.load("../graphics/tilemap/ground.png").convert()
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

    def custom_draw(self, player: pygame.sprite.Sprite):
        # offset for camera to middle of player
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # sort which sprite to display first by y axis -> obstacle above player # is drawn first and obstruct player, or is obstructed if player below
        self.display_surface.blit(
            self.floor_surf, -self.offset
        )  # because floor rect already at 0 0, dont need floor rect - offset

        # self.sprites are all sprite in current sprite group
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.y):
            offset_pos = sprite.rect.topleft - self.offset

            self.display_surface.blit(sprite.image, offset_pos)

    def enemy_update(self, player):
        enemy_sprites = [
            sprite
            for sprite in self.sprites()
            if hasattr(sprite, "sprite_type") and sprite.sprite_type == "enemy"
        ]

        for enemy in enemy_sprites:
            enemy.enemy_update(player)
