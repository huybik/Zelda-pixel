from __future__ import annotations
import pygame
from abc import ABC, abstractmethod
from .support import get_distance_direction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .enemy import Enemy
    from .player import Player
    from .entity import Entity
    from .tile import Tile

class Behavior(ABC):
    """Abstract base class for all AI behaviors."""
    @abstractmethod
    def update(self, enemy: Enemy, player: Player, entities: list[Entity], objects: list[Tile]):
        """The core logic for the behavior, called every frame."""
        pass

class AggressiveBehavior(Behavior):
    """A behavior for aggressive enemies that prioritize attacking the player."""
    def update(self, enemy: Enemy, player: Player, entities: list[Entity], objects: list[Tile]):
        distance_to_player, _ = get_distance_direction(enemy, player)
        
        if distance_to_player <= enemy.notice_radius:
            enemy.interaction(player, entities, objects)
        else:
            enemy.wander()

class FriendlyBehavior(Behavior):
    """A behavior for friendly NPCs that might help the player or other allies."""
    def update(self, enemy: Enemy, player: Player, entities: list[Entity], objects: list[Tile]):
        # Example: Heal the player if they are nearby and injured
        distance_to_player, _ = get_distance_direction(enemy, player)
        
        if distance_to_player <= enemy.notice_radius and player.health < player.max_health:
            enemy.target_name = player.full_name
            enemy.action = "heal"
            enemy.interaction(player, entities, objects)
        else:
            enemy.wander()

class NeutralBehavior(Behavior):
    """A behavior for neutral or passive entities."""
    def update(self, enemy: Enemy, player: Player, entities: list[Entity], objects: list[Tile]):
        # Neutral entities will just wander around
        enemy.wander()