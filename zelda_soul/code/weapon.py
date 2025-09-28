import pygame
from .player import Player
from .settings import GRAPHICS_DIR, weapon_data


class Weapon(pygame.sprite.Sprite):
    def __init__(self, player: Player, groups):
        super().__init__(groups)  # init group so it get drawn
        self.direction = player.action.split("_")[0]
        self.player = player
        self.sprite_type = "weapon"
        # self.name = self.player.weapon
        # init weapon
        self.allign()

    def allign(self):
        weapon_path = GRAPHICS_DIR / "weapons"

        self.direction = self.player.action.split("_")[0]

        if self.player.attacking and self.player.attack_type == "weapon":
            # set weapon surf attack align with player
            weapon_image = weapon_path / self.player.weapon / f"{self.direction}.png"
            self.image = pygame.image.load(str(weapon_image)).convert_alpha()

            if self.direction == "right":
                self.rect = self.image.get_rect(
                    midleft=self.player.rect.midright + pygame.math.Vector2(0, 16)
                )
            elif self.direction == "left":
                self.rect = self.image.get_rect(
                    midright=self.player.rect.midleft + pygame.math.Vector2(0, 16)
                )
            elif self.direction == "down":
                self.rect = self.image.get_rect(
                    midtop=self.player.rect.midbottom + pygame.math.Vector2(-10, 0)
                )
            else:
                self.rect = self.image.get_rect(
                    midbottom=self.player.rect.midtop + pygame.math.Vector2(-10, 0)
                )
        else:
            # weapon move with player
            # self.image = pygame.image.load(f'{weapon_path}/{self.player.weapon}/full.png')
            self.image = pygame.image.load(
                weapon_data[self.player.weapon]["graphic"]
            ).convert_alpha()

            if self.direction == "left":
                self.rect = self.image.get_rect(
                    topleft=self.player.rect.topleft + pygame.math.Vector2(40, -1)
                )
            elif self.direction == "right":
                self.rect = self.image.get_rect(
                    topleft=self.player.rect.topleft + pygame.math.Vector2(0, -1)
                )

            elif self.direction == "up":
                self.rect = self.image.get_rect(
                    topleft=self.player.rect.topleft + pygame.math.Vector2(20, 1)
                )
            elif self.direction == "down":
                self.rect = self.image.get_rect(
                    topleft=self.player.rect.topleft + pygame.math.Vector2(20, -1)
                )

    def update(self):
        self.allign()
        pass
