import pygame
from debug import debug
from support import import_folder
from settings import weapon_data, magic_data
from entity import Entity


class Player(Entity):
    def __init__(
        self, pos, groups: pygame.sprite.Group, obstacle_sprites: pygame.sprite.Group
    ):
        super().__init__(groups)
        self.image = pygame.image.load("../graphics/test/player.png")
        self.rect = self.image.get_rect(topleft=pos)

        self.hitbox = self.rect.inflate(-20, -26)

        # graphics setup˚“
        self.import_player_assets()
        self.status = "down"

        # movement
        self.direction = pygame.math.Vector2()
        self.speed = 5  # move speed
        self.obstacle_sprites = obstacle_sprites

        # equipment general
        self.switch_duration_cooldown = 200

        # weapon
        self.weapon_index = 0
        self.weapon = list(weapon_data.keys())[self.weapon_index]
        self.attack_cooldown = 400
        self.attack_time = pygame.time.get_ticks()
        self.can_switch_weapon = True
        self.weapon_switch_time = None
        self.attacking = False

        # magic
        self.magic_index = 0
        self.magic = list(magic_data.keys())[self.magic_index]
        self.can_switch_magic = True
        self.magic_switch_time = None
        self.casting = False

        # stats
        self.stats = {"health": 100, "energy": 60, "attack": 10, "magic": 4, "speed": 5}
        self.health = self.stats["health"] * 0.5
        self.energy = self.stats["energy"] * 0.8
        self.exp = 123
        self.speed = self.stats["speed"]

    def import_player_assets(self):
        character_path = "../graphics/player/"
        self.animations = {
            "up": [],
            "down": [],
            "left": [],
            "right": [],
            "right_idle": [],
            "left_idle": [],
            "up_idle": [],
            "down_idle": [],
            "right_attack": [],
            "left_attack": [],
            "up_attack": [],
            "down_attack": [],
        }

        for animation in self.animations.keys():
            fullpath = character_path + animation
            self.animations[animation] = import_folder(fullpath)

    def input(self):
        keys = pygame.key.get_pressed()

        # movement
        if keys[pygame.K_RIGHT]:
            self.direction.x = 1
            self.status = "right"
        elif keys[pygame.K_LEFT]:
            self.direction.x = -1
            self.status = "left"
        else:
            self.direction.x = 0

        if keys[pygame.K_DOWN]:
            self.direction.y = 1
            self.status = "down"
        elif keys[pygame.K_UP]:
            self.direction.y = -1
            self.status = "up"
        else:
            self.direction.y = 0

        # attack
        if keys[pygame.K_SPACE] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            print("attack")

        if keys[pygame.K_q] and self.can_switch_weapon:
            self.can_switch_weapon = False
            self.weapon_switch_time = pygame.time.get_ticks()

            if self.weapon_index < len(list(weapon_data.keys())) - 1:
                self.weapon_index += 1
            else:
                self.weapon_index = 0

            self.weapon = list(weapon_data.keys())[self.weapon_index]

        # magic
        if keys[pygame.K_LMETA]:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            style = list(magic_data.keys())[self.magic_index]
            strength = magic_data[style]["strength"] + self.stats["magic"]
            cost = magic_data[style]["cost"]
            print("magic")

        if keys[pygame.K_e] and self.can_switch_magic:
            self.can_switch_magic = False
            self.magic_switch_time = pygame.time.get_ticks()

            if self.magic_index < len(list(magic_data.keys())) - 1:
                self.magic_index += 1
            else:
                self.magic_index = 0

            self.magic = list(magic_data.keys())[self.magic_index]

    def get_status(self):
        if self.direction.x == 0 and self.direction.y == 0:
            if "_idle" not in self.status and "_attack" not in self.status:
                self.status += "_idle"
        if self.attacking:
            if "_attack" not in self.status:
                if "_idle" not in self.status:
                    self.status += "_attack"
                else:
                    self.status = self.status.replace("_idle", "_attack")
        else:
            if "_attack" in self.status:
                self.status = self.status.replace("_attack", "")

    def cooldowns(self):
        current_time = pygame.time.get_ticks()

        if current_time - self.attack_time > self.attack_cooldown:
            self.attacking = False

        if not self.can_switch_weapon:
            if current_time - self.weapon_switch_time >= self.switch_duration_cooldown:
                self.can_switch_weapon = True

        if not self.can_switch_magic:
            if current_time - self.magic_switch_time >= self.switch_duration_cooldown:
                self.can_switch_magic = True

    def update(self):
        self.input()
        self.cooldowns()
        self.get_status()
        self.animate()
        self.move(self.speed)
        debug(f"{self.status} {self.magic}")
