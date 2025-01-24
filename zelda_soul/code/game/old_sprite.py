import pygame
from typing import TYPE_CHECKING, Union

from entities.creature import Creature
from entities.resource import Resource

class Srpite(pygame.sprite.Sprite):
    def __init__(self, entity: Union[Creature, Resource], sprite: pygame.Surface) -> None:
        super().__init__()
        self.entity = entity
        self.sprite = sprite
        self.rect = self.sprite.get_rect()

    def update(self) -> None:
        self.rect.topleft = self.entity.location
        self.image = self.sprite

    def move(
        self,
        target: pygame.math.Vector2,
        speed: int,
        objects: list = None,
        tile_size=64,
    ):
        current = pygame.math.Vector2(self.hitbox.centerx, self.hitbox.centery)

        if target and objects:
            if (
                to_grid(target, tile_size)
                != to_grid(self.old_target_location, tile_size)
                or not self.path
            ):
                self.old_target_location = target
                # Pathfinding: Calculate path if necessary
                self.path = astar_pathfinding(
                    current, target, [obj.hitbox for obj in objects], tile_size
                )
            # Follow the calculated path
            elif self.path:
                next_waypoint = pygame.math.Vector2(self.path[0])
                desired_direction = next_waypoint - current
                distance = desired_direction.magnitude()

                if distance < 3:  # Reached waypoint
                    self.path.pop(0)
                    if not self.path:  # Final waypoint reached\
                        self.direction = pygame.math.Vector2(0, 0)
                        return
                else:
                    desired_direction = desired_direction.normalize()
                    self.direction = desired_direction

        move_delta = self.direction * speed
        # Smooth movement and apply speed
        self.hitbox.x += move_delta.x
        self.collision("horizontal")
        self.hitbox.y += move_delta.y
        self.collision("vertical")
        self.rect.center = self.hitbox.center

    def check_collision(self, test_rect):
        for sprite in self.obstacle_sprites:
            if test_rect.colliderect(sprite.hitbox):
                return True
        return False

    def collision(self, direction):
        if direction == "horizontal":
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.x > 0:  # moving right
                        self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0:  # moving left
                        self.hitbox.left = sprite.hitbox.right

        if direction == "vertical":
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.y > 0:  # moving down
                        self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0:  # moving up
                        self.hitbox.top = sprite.hitbox.bottom
