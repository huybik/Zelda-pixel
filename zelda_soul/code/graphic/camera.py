import pygame
import asyncio


class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()

        # general setup
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2

        self.offset = pygame.math.Vector2()

        # creating the floor, must load first before other things
        self.floor_surf = pygame.image.load("../graphics/tilemap/ground.jpg").convert()
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

    def custom_draw(self, player: pygame.sprite.Sprite):
        # offset for camera to middle of player
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # sort which sprite to display first by y axis -> obstacle above player # is drawn first and obstruct player, or is obstructed if player below
        self.display_surface.blit(
            self.floor_surf, -self.offset
        )  # because floor rect already at 0 0, dont need floor rect - offset

        # self.sprites are all sprite in current sprite group
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.y):
            offset_pos = sprite.rect.topleft - self.offset
            # offset_pos = sprite.rect.topleft

            self.display_surface.blit(sprite.image, offset_pos)

    def enemy_update(self, player, entities, objects):
        enemy_sprites = [
            sprite
            for sprite in self.sprites()
            if hasattr(sprite, "sprite_type") and sprite.sprite_type == "enemy"
        ]

        # Run regular updates
        for enemy in enemy_sprites:
            enemy.enemy_update(player, entities, objects)

        # Run AI decisions concurrently with timeout
        # Create tasks for all enemies

        # await asyncio.gather(
        #     *(
        #         enemy.enemy_decision(player, entities, objects)
        #         for enemy in enemy_sprites
        #     )
        # )
