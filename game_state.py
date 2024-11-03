import json
import pygame
from typing import Dict, List, Any


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


def extract_enemy_data(enemy) -> Dict:
    return {
        "type": enemy.monster_name,
        "position": {"x": enemy.rect.centerx, "y": enemy.rect.centery},
        "status": enemy.status,
        "direction": {"x": enemy.direction.x, "y": enemy.direction.y},
        "stats": {
            "health": enemy.health,
            "exp": enemy.exp,
            "speed": enemy.speed,
            "damage": enemy.damage,
            "resistance": enemy.resistance,
            "attack_radius": enemy.attack_radius,
            "notice_radius": enemy.notice_radius,
        },
        "can_attack": enemy.can_attack,
    }


def extract_player_data(player) -> Dict:
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


def export_game_state(level) -> None:
    game_state = {
        "tiles": {"obstacle": [], "grass": [], "object": []},
        "player": None,
        "enemies": [],
    }

    # Extract tiles
    for sprite in level.obstacle_sprites:
        if hasattr(sprite, "sprite_type"):
            tile_data = extract_tile_data(sprite)
            game_state["tiles"][sprite.sprite_type].append(tile_data)

    # Extract player
    if level.player:
        game_state["player"] = extract_player_data(level.player)

    # Extract enemies
    for enemy in level.enemies:
        enemy_data = extract_enemy_data(enemy)
        game_state["enemies"].append(enemy_data)

    # Export to JSON file
    with open("game_state.json", "w") as f:
        json.dump(game_state, f, indent=2)
