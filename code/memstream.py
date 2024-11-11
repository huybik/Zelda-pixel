import os
import time
from typing import TYPE_CHECKING
import pygame
from support import get_distance_direction

if TYPE_CHECKING:
    from entity import Entity
    from tile import Tile
    from player import Player
    from enemy import Enemy


class MemoryStream:

    def write_memory(self, memory_entry, entity: "Enemy", threshold=200):
        os.makedirs("../memory", exist_ok=True)

        memories_file = f"../memory/stream_{entity.full_name}.txt"
        try:
            with open(memories_file, "r") as f:
                lines = f.readlines()
            if len(lines) >= threshold:
                lines = lines[-(threshold - 1) :]  # Keep last 99 lines to add new one
                with open(memories_file, "w") as f:
                    f.writelines(lines)
        except FileNotFoundError:
            pass

        # Append new memory
        with open(memories_file, "a") as f:
            f.write(memory_entry)

    def save_observation(
        self,
        entity: "Enemy",
        player: "Player",
        entities: list["Enemy"],
        objects: list["Tile"],
    ):
        """Logs the enemy's memory including nearby entities and objects within notice radius."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        location = f"{entity.rect.centerx},{entity.rect.centery}"
        health = (entity.health / entity.max_health) * 100
        player_health = (player.health / int(player.stats["health"])) * 100

        # Get player observations
        player_distance, _ = get_distance_direction(entity, player)
        player_observation = (
            f"player_location:{player.rect.centerx},{player.rect.centery},"
            f"player_distance:{player_distance:.1f},"
            f"player_health:{player_health:.1f}%,"
            f"player_action:{player.status},"
            f"player_weapon:{player.weapon},"
        )

        # Get nearby entities within notice radius
        nearby_entities = []
        if entities:
            for other_entity in entities:
                if other_entity != entity:  # Don't include self
                    distance, _ = get_distance_direction(entity, other_entity)
                    if distance <= entity.notice_radius:
                        nearby_entities.append(
                            f"(entity_{other_entity.full_name}:("
                            f"location:{other_entity.rect.centerx},{other_entity.rect.centery},"
                            f"moving_to:{int(other_entity.target_location.x)},{int(other_entity.target_location.y)},"
                            f"distance:{distance:.1f},"
                            f"health:{(other_entity.health / other_entity.max_health) * 100:.1f}%,"
                            f"action:{other_entity.status})"
                            f"status:{other_entity.event_status})"
                        )

        # Get nearby objects within notice radius
        nearby_objects = []
        if objects:
            for obj in objects:
                distance = pygame.math.Vector2(
                    obj.rect.centerx - entity.rect.centerx,
                    obj.rect.centery - entity.rect.centery,
                ).magnitude()
                if distance <= entity.notice_radius:
                    nearby_objects.append(
                        f"(object_{obj.sprite_type}"
                        f"object_location:{obj.rect.centerx},{obj.rect.centery},"
                        f"object_distance:{distance:.1f})"
                    )

        # Combine all information
        memory_entry = (
            f"time:{timestamp},"
            f"your_location:{location},"
            f"your_action:{entity.status},"
            f"your_status:{entity.event_status},"
            f"your_health:{health:.1f}%,"
            f"{player_observation}"
        )

        if entity.target_location:
            memory_entry += f"your_moving_to:{int(entity.target_location.x)},{int(entity.target_location.y)},"

        if nearby_entities:
            memory_entry += f"nearby_entities:({','.join(nearby_entities)}),"

        # if nearby_objects:
        #     memory_entry += f"nearby_objects:({','.join(nearby_objects)}),"

        memory_entry += "\n"

        self.write_memory(memory_entry, entity)
        return memory_entry

        # Keep only last 100 lines

    def write_data(self, data, filename):
        """Saves the AI's decision to a decision file."""
        os.makedirs("../memory", exist_ok=True)
        with open(f"../memory/{filename}.txt", "w") as f:
            f.write(data)

    def read_data(self, filename):
        """Reads the data from file."""
        try:
            with open(f"../memory/{filename}.txt", "r") as f:
                return f.read()
        except FileNotFoundError:
            return None
