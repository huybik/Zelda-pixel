import json
from typing import Dict, List, Any
import pygame
from enemy import Enemy
from player import Player


def extract_tile_data(tile) -> Dict:
    return {
        "type": tile.sprite_type,
        "position": {"x": tile.rect.x, "y": tile.rect.y},
        "hitbox": {
            "x": tile.hitbox.x,
            "y": tile.hitbox.y,
            "width": tile.hitbox.width,
            "height": tile.hitbox.height,
        },
    }


def extract_enemy_data(enemy: Enemy) -> Dict:
    return {
        "type": enemy.monster_name,
        "position": {"x": enemy.rect.centerx, "y": enemy.rect.centery},
        "status": enemy.status,
        "direction": {"x": enemy.direction.x, "y": enemy.direction.y},
        "stats": {
            "health": enemy.health,
            "exp": enemy.exp,
            "speed": enemy.speed,
            "damage": enemy.attack_damage,
            "resistance": enemy.resistance,
            "attack_radius": enemy.attack_radius,
            "notice_radius": enemy.notice_radius,
        },
        "can_attack": enemy.can_attack,
    }


def extract_player_data(player: Player) -> Dict:
    return {
        "position": {"x": player.rect.centerx, "y": player.rect.centery},
        "status": player.status,
        "direction": {"x": player.direction.x, "y": player.direction.y},
        "stats": player.stats,
        "weapon": player.weapon,
        "magic": player.magic,
        "health": player.health,
        "energy": player.energy,
        "exp": player.exp,
    }


class GameStateExporter:
    def __init__(self, level):
        self.level = level

    def get_player_view_rect(self) -> pygame.Rect:
        """Returns the rectangle representing the player's current viewport."""
        player = self.level.player
        if not player:
            return pygame.Rect(0, 0, self.level.display_surface.get_width(), self.level.display_surface.get_height())
        camera_offset = self.level.visible_sprites.offset
        view_rect = pygame.Rect(
            camera_offset.x,
            camera_offset.y,
            self.level.display_surface.get_width(),
            self.level.display_surface.get_height()
        )
        return view_rect

    def is_within_radius(self, pos1: pygame.math.Vector2, pos2: pygame.math.Vector2, radius: float) -> bool:
        """Checks if pos2 is within the radius from pos1."""
        distance = pos1.distance_to(pos2)
        return distance <= radius

    def extract_tiles_player_view(self, view_rect: pygame.Rect) -> List[Dict]:
        """Extracts tiles within the player's view."""
        visible_tiles = []
        for sprite in self.level.obstacle_sprites:
            if hasattr(sprite, "sprite_type"):
                if view_rect.colliderect(sprite.rect):
                    tile_info = extract_tile_data(sprite)
                    visible_tiles.append(tile_info)
        return visible_tiles

    def extract_tiles_enemy_view(self, enemy: Enemy) -> List[Dict]:
        """Extracts tiles within an enemy's notice radius."""
        enemy_pos = pygame.math.Vector2(enemy.rect.centerx, enemy.rect.centery)
        noticed_tiles = []
        for sprite in self.level.obstacle_sprites:
            if hasattr(sprite, "sprite_type"):
                tile_pos = pygame.math.Vector2(sprite.rect.centerx, sprite.rect.centery)
                if self.is_within_radius(enemy_pos, tile_pos, enemy.notice_radius):
                    tile_info = extract_tile_data(sprite)
                    noticed_tiles.append(tile_info)
        return noticed_tiles

    def extract_entities_player_view(self, view_rect: pygame.Rect) -> Dict[str, Any]:
        """Extracts player view entities: player and enemies within view."""
        entities = {
            "player": None,
            "enemies": []
        }
        # Extract player data if within view
        if self.level.player and view_rect.colliderect(self.level.player.rect):
            entities["player"] = extract_player_data(self.level.player)

        # Extract enemies within view
        for enemy in self.level.enemies:
            if view_rect.colliderect(enemy.rect):
                entities["enemies"].append(extract_enemy_data(enemy))

        return entities

    def extract_entities_enemy_view(self) -> Dict[int, Dict[str, Any]]:
        """Extracts entities within each enemy's notice radius."""
        enemy_views = {}
        for idx, enemy in enumerate(self.level.enemies):
            enemy_view = {
                "tiles": self.extract_tiles_enemy_view(enemy),
                "player": None,
                "enemies": []
            }
            enemy_pos = pygame.math.Vector2(enemy.rect.centerx, enemy.rect.centery)
            # Check if player is within radius
            if self.level.player:
                player_pos = pygame.math.Vector2(self.level.player.rect.centerx, self.level.player.rect.centery)
                if self.is_within_radius(enemy_pos, player_pos, enemy.notice_radius):
                    enemy_view["player"] = extract_player_data(self.level.player)
            # Check other enemies within radius
            for other_enemy in self.level.enemies:
                if other_enemy == enemy:
                    continue
                other_pos = pygame.math.Vector2(other_enemy.rect.centerx, other_enemy.rect.centery)
                if self.is_within_radius(enemy_pos, other_pos, enemy.notice_radius):
                    enemy_view["enemies"].append(extract_enemy_data(other_enemy))
            enemy_views[idx] = enemy_view
        return enemy_views

    def export_to_json(self, file_path: str = "game_state.json") -> None:
        view_rect = self.get_player_view_rect()
        game_state = {
            "player_view": {
                "tiles": self.extract_tiles_player_view(view_rect),
                "entities": self.extract_entities_player_view(view_rect),
            },
            "enemies_view": self.extract_entities_enemy_view(),
        }

        with open(file_path, "w") as f:
            json.dump(game_state, f, indent=2)
        print(f"Game state exported to {file_path}")


def export_game_state(level) -> None:
    exporter = GameStateExporter(level)
    exporter.export_to_json()
