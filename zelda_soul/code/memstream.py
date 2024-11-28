import os
import time
import json
from typing import TYPE_CHECKING
import pygame
from support import get_distance_direction
from settings import MEMORY_SIZE
if TYPE_CHECKING:
    from entity import Entity
    from tile import Tile
    from player import Player
    from enemy import Enemy


class MemoryStream:

    def write_memory(self, memory_entry,  filename, threshold):
        os.makedirs("../memory", exist_ok=True)
        memories_file = f"../memory/{filename}"
        
        try:
            with open(memories_file, "r") as f:
                try:
                    memories = json.load(f)
                except json.JSONDecodeError:
                    memories = []
            
            if len(memories) >= threshold:
                memories = memories[-(threshold - 1):]  # Keep last 99 entries to add new one
        except FileNotFoundError:
            memories = []

        # Append new memory
        memories.append(memory_entry)
        
        # Write updated memories
        with open(memories_file, "w") as file:
                json.dump(memories, file, indent=2)
                
    
    def read_last_n_records(self, filename,n=None ):
        try:
            with open(f"../memory/{filename}", "r") as f:
                try:
                    records = json.load(f)
                    if n:
                        if len(records) >= n:
                            return records[-n:]
                except json.JSONDecodeError:
                    records = []
            return records
        except FileNotFoundError:
            return None

    
    
    

    
    
    
    