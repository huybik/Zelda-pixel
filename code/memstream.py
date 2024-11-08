import os
import time


class MemoryStream:

    def write_memory(self, memory_entry, monster_id, threshold=200):
        os.makedirs("../memory", exist_ok=True)

        memories_file = f"../memory/stream_{monster_id}.txt"
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

    def parse_data(self, entity, player):
        # Create memory directory if it doesn't exist
        """Logs the enemy's memory to a text file with timestamp, location, status, and observations."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        location = f"{entity.rect.centerx},{entity.rect.centery}"
        health = (entity.health / entity.max_health) * 100
        player_health = (player.health / int(player.stats["health"])) * 100

        # Get observations about nearby entities (currently just player)
        distance, _ = entity.get_player_distance_direction(player)
        player_observation = (
            f"player_location:({player.rect.centerx},{player.rect.centery}),"
            f"player_distance:{distance:.1f},"
            f"player_health:{player_health:.1f}%,"
            f"player_status:{player.status},"
        )  # Combine all information
        memory_entry = (
            f"{timestamp},your_location:({location}),"
            f"your_status:{entity.status},"
            f"your_health:{health:.1f}%,"
            f"{player_observation}\n"
        )
        if entity.target:
            memory_entry += (
                f"your_moving_to:({int(entity.target.x)},{int(entity.target.y)})"
            )

        return memory_entry

        # Keep only last 100 lines

    def get_observation(self, monster_id):
        """Gets the most recent observation from memory file."""
        try:
            with open(f"../memory/stream_{monster_id}.txt", "r") as f:
                lines = f.readlines()
                if lines:
                    return lines[-1].strip()
                return "No memories found."
        except FileNotFoundError:
            return "No memories found."

    def log_memory(self, entity, player):
        memory_entry = self.parse_data(entity, player)
        self.write_memory(memory_entry, entity.monster_id)

    def write_data(self, data, prefix, monster_id):
        """Saves the AI's decision to a decision file."""
        os.makedirs("../memory", exist_ok=True)
        with open(f"../memory/{prefix}_{monster_id}.txt", "w") as f:
            f.write(data)

    def read_data(self, prefix, monster_id):
        """Reads the data from file."""
        try:
            with open(f"../memory/{prefix}_{monster_id}.txt", "r") as f:
                return f.read()
        except FileNotFoundError:
            return None
