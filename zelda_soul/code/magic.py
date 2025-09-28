import pygame
from random import randint
from typing import TYPE_CHECKING

from .particles import AnimationPlayer
from .resources import load_sound
from .settings import AUDIO_DIR, TILESIZE

if TYPE_CHECKING:
    from .entity import Entity
    from .tile import Tile
    from .player import Player


class MagicPlayer:
    def __init__(self, animation_player: AnimationPlayer):
        self.animation_player = animation_player
        self.sounds = {
            "heal": load_sound(AUDIO_DIR / "heal.wav"),
            "flame": load_sound(AUDIO_DIR / "Fire.wav"),
        }

    def heal(self, player: "Player", strength, cost, groups):
        if player.energy >= cost:
            self.sounds["heal"].play()
            player.health += strength
            player.energy -= cost
            if player.health >= player.stats["health"]:
                player.health = player.stats["health"]
            self.animation_player.create_particles("aura", player.rect.center, groups)
            self.animation_player.create_particles("heal", player.rect.center, groups)

    def flame(self, player: "Player", strength, cost, groups):
        if player.energy >= cost:
            player.energy -= cost

            # create 6 flames
            self.sounds["flame"].play()
            for i in range(1, 12):
                # direction dictate  where player looking e.g. (0,1) for /right
                offset = i * randint(0, TILESIZE)
                pos = (
                    player.rect.centerx + player.facing.x * offset,
                    player.rect.centery + player.facing.y * offset,
                )

                self.animation_player.create_particles("flame", pos, groups)
