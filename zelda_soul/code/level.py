import pygame
from .player import Player
from .tile import Tile
from .settings import GRAPHICS_DIR, MAP_DIR, TILESIZE
from .support import import_csv_layout, import_folder
import random
from typing import Dict
from .weapon import Weapon
from .ui import UI
from .enemy import Enemy
from .particles import AnimationPlayer
from .upgrade import Upgrade
from .camera import YSortCameraGroup
from .magic import MagicPlayer
from .ai_manager import AIManager
from .compute_manager import ComputeManager

class Level:
    def __init__(self) -> None:
        self.display_surface = pygame.display.get_surface()
        self.game_paused = False

        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.attack_sprites = pygame.sprite.Group()
        self.attackable_sprites = pygame.sprite.Group()

        self.entities = []
        self.objects = []
        
        # AI Manager setup
        self.ai_manager = AIManager()
        self.ai_manager.start()

        # Compute Manager setup
        self.compute_manager = ComputeManager()
        self.compute_manager.start()

        self.ui = UI()
        self.create_map()
        self.upgrade = Upgrade(self.player)
        self.animation_player = AnimationPlayer()
        self.magic_player = MagicPlayer(self.animation_player)

    def create_map(self):
        layouts: Dict[str, list[list[str]]] = {
            "boundary": import_csv_layout(MAP_DIR / "map_FloorBlocks.csv"),
            "grass": import_csv_layout(MAP_DIR / "map_Grass.csv"),
            "object": import_csv_layout(MAP_DIR / "map_Objects.csv"),
            "entities": import_csv_layout(MAP_DIR / "map_Entities.csv"),
        }
        graphics = {
            "grass": import_folder(GRAPHICS_DIR / "Grass"),
            "object": import_folder(GRAPHICS_DIR / "objects"),
        }
        enemy_id_map = {"390": "bamboo", "391": "spirit", "392": "raccoon", "393": "squid"}

        for sprite_type, layout in layouts.items():
            for row_index, row in enumerate(layout):
                for col_index, col in enumerate(row):
                    if col != "-1":
                        x, y = col_index * TILESIZE, row_index * TILESIZE
                        if sprite_type == "boundary":
                            Tile((x, y), "boundary", self.obstacle_sprites, sprite_type="boundary")
                        elif sprite_type == "grass":
                            surface = random.choice(graphics[sprite_type])
                            Tile((x, y), "grass", [self.visible_sprites, self.attackable_sprites], sprite_type, surface)
                        elif sprite_type == "object":
                            surface = graphics[sprite_type][int(col)]
                            name = "resource" if 2 <= int(col) <= 4 or 14 < int(col) < 21 else "object"
                            full_name = f"{name}{col_index}{row_index}"
                            self.objects.append(
                                Tile((x, y), full_name, [self.visible_sprites, self.obstacle_sprites], sprite_type, surface)
                            )
                        elif sprite_type == "entities":
                            if col == "394":
                                self.player = Player((x, y), [self.visible_sprites, self.attackable_sprites], self.obstacle_sprites, self.create_magic)
                            elif col in enemy_id_map:
                                name = enemy_id_map[col]
                                full_name = f"{name}{col_index}{row_index}"
                                self.entities.append(
                                    Enemy(
                                        name, full_name, (x, y),
                                        [self.visible_sprites, self.attack_sprites, self.attackable_sprites],
                                        self.obstacle_sprites, self.visible_sprites, self.ai_manager,
                                        self.compute_manager
                                    )
                                )
        self.weapon = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

    def collision(self):
        for attack_sprite in self.attack_sprites:
            collision_sprites = pygame.sprite.spritecollide(attack_sprite, self.attackable_sprites, dokill=False)
            if collision_sprites:
                for target_sprite in collision_sprites:
                    if target_sprite != attack_sprite and self.player.attacking:
                        if target_sprite.sprite_type == "grass":
                            target_sprite.kill()
                            pos = target_sprite.rect.center
                            offset = pygame.math.Vector2((0, 50))
                            for _ in range(random.randint(2, 5)):
                                self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])
                        elif target_sprite.sprite_type == "enemy":
                            if attack_sprite.sprite_type in ["magic", "weapon"]:
                                target_sprite.get_damage(self.player)

    def create_magic(self, entity, style, strength, cost):
        if style == "heal":
            self.magic_player.heal(entity, strength, cost, [self.visible_sprites])
        if style == "flame":
            self.magic_player.flame(entity, strength, cost, [self.visible_sprites, self.attack_sprites])

    def toggle_menu(self):
        self.game_paused = not self.game_paused

    def run(self):
        self.visible_sprites.custom_draw(self.player)
        self.ui.display(self.player)

        if self.game_paused:
            self.upgrade.display()
        else:
            self.visible_sprites.update()
            self.visible_sprites.enemy_update(self.player, self.entities, self.objects)
            self.collision()

    def shutdown(self):
        """Gracefully stops manager threads."""
        print("Shutting down level...")
        self.ai_manager.stop()
        self.compute_manager.stop()