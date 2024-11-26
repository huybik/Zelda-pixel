import pygame
from os import walk
from math import sin
from particles import AnimationPlayer
from magic import MagicPlayer
from tooltips import StatusBars
from support import get_distance_direction


class Entity(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)
        self.groups = groups
        # init class
        self.animation_player = AnimationPlayer()

        # params
        self.animation_speed = 0.15
        self.frame_index = 0
        self.animations = {}
        self.sprite_type = None

        self.main_path = ""

        # movement
        self.direction = pygame.math.Vector2()
        self.facing = pygame.math.Vector2()

        # attack
        self.first_attack = False
        self.vulnerable = True
        self.attack_type = None

        # status
        self.name = None  # expected to be set by subclass
        self.full_name = None  # expected to be set by subclass
        self.target_location = None
        self.target_name = None

        self.outside_event = None
        self.reason = None

        # stats
        self.health = None
        self.max_health = None
        self.energy = None
        self.max_energy = None
        self.lvl = 1
        self.attack_damage = 0
        self.speed = 0
        self.exp = 0

        # sounds
        self.death_sound = pygame.mixer.Sound("../audio/death.wav")
        self.hit_sound = pygame.mixer.Sound("../audio/hit.wav")

        self.death_sound.set_volume(0.6)
        self.hit_sound.set_volume(0.6)

        # cosmetic
        self.text_bubble = None
        self.status_bars = None

        # others
        self.animate_sequence = "idle"

        # observation
        self.can_save_observation = False
        self.observation_count = 0
        
        self.internal_event = None
        self.old_internal_event = None
        self.outside_event = None
        self.old_outside_event = None
        self.observed_event = None
        self.old_observed_event = None
        
        self.first_observation = False
        
    def hitbox_collide(
        self, sprite1: pygame.sprite.Sprite, sprite2: pygame.sprite.Sprite
    ):
        return sprite1.hitbox.colliderect(sprite2.hitbox)

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

    def animate(self):
        animation = self.animations[self.animate_sequence]  # load animation sequence

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

    def get_damage(self, attacker: "Entity"):

        if self.vulnerable:
            # save attacked event
            self.outside_event = f"attacked by {attacker.full_name}"
            self.vulnerable = False
            self.hit_sound.play()
            self.vulnerable_time = pygame.time.get_ticks()
            # save observation

            attack_type = attacker.attack_type
            if attacker.sprite_type == "player":
                attack_type = attacker.attack_type
                if attack_type == "weapon":
                    self.health -= attacker.get_full_weapon_damage()
                elif attack_type == "magic":
                    self.health -= attacker.get_full_magic_damage()

            else:
                self.health -= attacker.attack_damage

            # knockback

            # particles
            pos = self.rect.center
            if attack_type:
                self.animation_player.create_particles(
                    attack_type, pos, [self.groups[0]]
                )

            # knockback
            _, direction = get_distance_direction(self, attacker)
            # Set target location based on knockback direction
            knockback_distance = 200  # pixels to push back
            knockback_speed = 5
            self.target_location = pygame.math.Vector2(self.hitbox.center) - (
                direction * knockback_distance
                if direction.magnitude() != 0
                else pygame.math.Vector2()
            )
            self.move(self.target_location, knockback_speed)

            if self.health <= 0:
                # self.action = "dead"
                self.outside_event = "dead, killed by " + attacker.full_name
                attacker.outside_event = f"killed {self.full_name}"
                # save dead event

                self.animation_player.create_particles(
                    self.name, self.rect.center, [self.groups[0]]
                )

            
                self.death_sound.play()
                self.add_exp(attacker, self.exp)
            
                # if self.status_bars:
                #     self.status_bars.kill()
                # if self.text_bubble:
                #     self.text_bubble.kill()

                
            
            # self.can_save_observation = True



    def get_heal(self, healer: "Entity"):
        self.health += healer.attack_damage
        if self.health > self.max_health:
            self.outside_event = f"fully healed by {healer.full_name}"
            healer.outside_event = f"healed {self.full_name}"
            self.health = self.max_health

        self.animation_player.create_particles(
            "heal", self.hitbox.center, [self.groups[0]]
        )

        self.outside_event = f"healed by {healer.full_name}"
        # self.can_save_observation = True

    def add_exp(self, entity: "Entity", amount):
        entity.exp += amount

    def respawn(self):
        pass
