import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.gcreature import GameCreature


def keyboard_move(
    c: "GameCreature", direction: pygame.Vector2, group: pygame.sprite.Group
):
    if direction.magnitude() != 0:
        direction = direction.normalize()  # this to normalize diagonal move speed
        # detect collision before moving
        c.rect.x += direction.x * c.creature.stats.move_speed
        collision(c, "horizontal", direction, group)
        c.rect.y += direction.y * c.creature.stats.move_speed
        collision(c, "vertical", direction, group)


def collision(
    c: "GameCreature", side: str, direction: pygame.Vector2, group: pygame.sprite.Group
):
    sprites = [x for x in group if x != c]
    for sprite in sprites:
        if sprite.rect.colliderect(c.rect):
            if side == "horizontal":
                if direction.x > 0:  # moving right
                    c.rect.right = sprite.rect.left
                if direction.x < 0:  # moving left
                    c.rect.left = sprite.rect.right
            if side == "vertical":
                if direction.y > 0:  # moving down
                    c.rect.bottom = sprite.rect.top
                if c.direction.y < 0:  # moving up
                    c.rect.top = sprite.rect.bottom
