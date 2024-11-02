import pygame
from os import walk
from math import sin


class Entity(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)

        self.animation_speed = 0.15
        self.frame_index = 0
        self.animations = {}

        self.main_path = ""

        # movement
        self.direction = pygame.math.Vector2()
        self.facing = pygame.math.Vector2()

        # attack
        self.first_attack = False
        self.vulnerable = True

    def move(self, speed):
        if self.direction.magnitude() != 0:
            if self.direction.magnitude() < 2:  # this to ignore knockback magnitude
                self.direction = self.direction.normalize()

            # detect collision before moving
            self.hitbox.x += self.direction.x * speed
            self.collision("horizontal")
            self.hitbox.y += self.direction.y * speed
            self.collision("vertical")

            self.rect.center = self.hitbox.center

    def hitbox_collide(
        self, sprite1: pygame.sprite.Sprite, sprite2: pygame.sprite.Sprite
    ):
        return sprite1.hitbox.colliderect(sprite2.hitbox)

    def collision(self, direction):

        collided_sprites = pygame.sprite.spritecollide(
            self, self.obstacle_sprites, dokill=False, collided=self.hitbox_collide
        )
        # collided_sprites = [sprite for sprite in collided_sprites if sprite != self]
        if collided_sprites:
            for sprite in collided_sprites:
                if direction == "horizontal":
                    if self.direction.x > 0:  # moving right
                        self.hitbox.right = sprite.hitbox.left - 1
                    if self.direction.x < 0:  # moving left
                        self.hitbox.left = sprite.hitbox.right + 1
                if direction == "vertical":
                    if self.direction.y > 0:  # moving down
                        self.hitbox.bottom = sprite.hitbox.top - 1
                    if self.direction.y < 0:  # moving 33334
                        self.hitbox.top = sprite.hitbox.bottom + 1
                # self.direction.y = 0

    def animate(self):
        animation = self.animations[self.status]  # load animation sequence

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0

        # set the image
        self.image = animation[int(self.frame_index)]

    def import_graphics(self, main_path, name, animations):

        main_path = f"{main_path}/{name}/"
        # get all frames into animation index
        for status in animations.keys():
            surface_list = []
            path = main_path + status
            for _, _, img_files in walk(path):
                for image in img_files:
                    full_path = path + "/" + image
                    image_surf = pygame.image.load(full_path).convert_alpha()
                    surface_list.append(image_surf)

            animations[status] = surface_list

    def wave_value(self):
        value = sin(pygame.time.get_ticks())
        if value >= 0:
            return 255
        else:
            return 0
