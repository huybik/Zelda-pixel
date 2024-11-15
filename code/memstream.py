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

    def write_memory(self, memory_entry, entity: "Enemy", threshold=100):
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

    def observation_template(self, entity: "Entity", distance):

        if entity.full_name == "player":
            health = (entity.health / entity.stats["health"]) * 100
        else:
            health = (entity.health / entity.max_health) * 100

        observation = (
            f"name:{entity.full_name},"
            f"new_event:{entity.event_status},"
            f"\location:{entity.rect.centerx},{entity.rect.centery},"
            f"previous_health:{health:.1f}%,"
            f"previous_action:{entity.action},"
            f"previous_reason:{entity.reason},"
        )
        if entity.target_location:
            target_location = (
                f"{int(entity.target_location.x)},{int(entity.target_location.y)},"
            )
            observation += f"previous_moving_to:{target_location},"
        if entity.target_name:
            observation += f"previous_target_name:{entity.target_name},"
        if distance:
            observation += f"distance: {distance},"

        return f"({observation})"

    def save_observation(
        self,
        entity: "Enemy",
        player: "Player",
        entities: list["Enemy"],
        objects: list["Tile"],
    ):
        """Logs the enemy's memory including nearby entities and objects within notice radius."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Get nearby entities within notice radius
        nearby_entities = []
        if entities:
            for other_entity in entities:
                if other_entity != entity:  # Don't include self
                    distance, _ = get_distance_direction(entity, other_entity)
                    if distance <= entity.notice_radius:
                        nearby_entities.append(
                            self.observation_template(other_entity, distance)
                        )

        # Get nearby objects within notice radius
        nearby_objects = []
        if objects:
            for obj in objects:
                distance, _ = get_distance_direction(entity, obj)
                if distance <= entity.notice_radius:
                    nearby_objects.append(
                        f"(name:{obj.full_name},"
                        f"location:{obj.rect.centerx},{obj.rect.centery},"
                        f"distance:{distance:.1f})"
                    )

        # Combine all information
        memory_entry = timestamp + ","
        memory_entry += (
            f"yourself:({self.observation_template(entity, distance=None)}),"
        )
        distance, _ = get_distance_direction(entity, player)
        memory_entry += f"player:({self.observation_template(player, distance)}),"

        if nearby_entities:
            memory_entry += f"nearby_entities:({','.join(nearby_entities)}),"

        if nearby_objects:
            memory_entry += f"nearby_objects:({','.join(nearby_objects)})"

        memory_entry += "\n"

        self.write_memory(memory_entry, entity)
        return memory_entry

        # Keep only last 100 lines

    def read_last_observation(self, entity: "Entity"):
        data = self.read_data(f"stream_{entity.full_name}")
        if data:
            lines = data.splitlines()
            if lines:
                return lines[-1]
        return None

    def write_data(self, filename, data):
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

    def read_memory(self, entity: "Entity"):
        return self.read_data(f"stream_{entity.full_name}")

    def read_summary(self, entity: "Entity"):
        return self.read_data(f"summary_{entity.full_name}")
