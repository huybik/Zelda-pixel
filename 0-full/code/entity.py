import pygame
from os import walk


class Entity(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)

        self.animation_speed = 0.15
        self.frame_index = 0

    def move(self, speed):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()

        # detect collision before moving
        self.hitbox.x += self.direction.x * speed
        self.collision("horizontal")
        self.hitbox.y += self.direction.y * speed
        self.collision("vertical")

        self.rect.center = self.hitbox.center

        # weapon move

    def hitbox_collide(
        self, sprite1: pygame.sprite.Sprite, sprite2: pygame.sprite.Sprite
    ):
        return sprite1.hitbox.colliderect(sprite2.hitbox)

    def collision(self, direction):

        collided_sprites = pygame.sprite.spritecollide(
            self, self.obstacle_sprites, dokill=False, collided=self.hitbox_collide
        )
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
        self.image = animation[int(self.frame_index)]  # normalize the float

    def import_graphics(self, name):

        main_path = f"../graphics/monsters/{name}/"
        # get all frames into animation index
        for status in self.animations.keys():
            surface_list = []
            path = main_path + status
            for _, _, img_files in walk(path):
                for image in img_files:
                    full_path = path + "/" + image
                    image_surf = pygame.image.load(full_path)
                    surface_list.append(image_surf)

            self.animations[status] = surface_list
