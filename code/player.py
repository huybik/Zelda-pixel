import pygame
from debug import debug
from support import import_folder
from settings import weapon_data, magic_data
from entity import Entity
from settings import HITBOX_OFFSET

# from enemy import Enemy


# from level import Level


class Player(Entity):
    def __init__(
        self,
        pos,
        groups: pygame.sprite.Group,
        obstacle_sprites: pygame.sprite.Group,
        create_magic,
    ):
        super().__init__(groups)
        self.image = pygame.image.load("../graphics/test/player.png").convert_alpha()
        self.rect = self.image.get_rect(topleft=pos)

        self.hitbox = self.rect.inflate(-6, HITBOX_OFFSET["player"])
        self.sprite_type = "player"
        self.attack_type = None

        # graphics setup˚“
        self.status = "down"
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
        path = "../graphics/"

        self.create_magic = create_magic
        self.import_graphics(path, "player", self.animations)

        # movement
        self.obstacle_sprites = obstacle_sprites

        # equipment general
        self.switch_duration_cooldown = 200

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
        self.max_stats = {
            "health": 300,
            "energy": 140,
            "attack": 20,
            "magic": 10,
            "speed": 10,
        }
        self.upgrade_cost = {
            "health": 100,
            "energy": 100,
            "attack": 100,
            "magic": 100,
            "speed": 100,
        }
        self.health = self.stats["health"] * 0.5
        self.energy = self.stats["energy"] * 0.8
        self.exp = 500
        # self.speed = self.stats["speed"]
        self.knockback = weapon_data[self.weapon][
            "damage"
        ]  # just use damage as knockback
        self.damage = self.get_full_weapon_damage()

        # vulnerable
        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_cooldown = 2000

        # import sound
        self.weapon_attack_sound = pygame.mixer.Sound("../audio/sword.wav")
        self.weapon_attack_sound.set_volume(0.3)
        self.player_death_sound = pygame.mixer.Sound("../audio/death.wav")

    def input(self):
        keys = pygame.key.get_pressed()

        # movement
        if keys[pygame.K_RIGHT]:
            self.direction.x = 1
            self.status = "right"
        elif keys[pygame.K_LEFT]:
            self.direction.x = -1
            self.status = "left"
        # weapon
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

        if self.direction.magnitude() > 0:
            self.facing = self.direction.normalize()

        # attack
        if keys[pygame.K_SPACE] and not self.attacking:
            self.weapon_attack_sound.play()
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            self.attack_type = "weapon"
            print("attack")

        if keys[pygame.K_q] and self.can_switch_weapon:
            self.can_switch_weapon = False
            self.weapon_switch_time = pygame.time.get_ticks()

            if self.weapon_index < len(list(weapon_data.keys())) - 1:
                self.weapon_index += 1
            else:
                self.weapon_index = 0

            self.weapon = list(weapon_data.keys())[self.weapon_index]
            # set knockback
            self.knockback = weapon_data[self.weapon]["damage"]
            self.damage = self.get_full_weapon_damage()

        # magic
        if keys[pygame.K_r] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            self.attack_type = "magic"
            style = list(magic_data.keys())[self.magic_index]
            strength = self.get_full_magic_damage()
            cost = magic_data[style]["cost"]

            # create magic sprites
            self.create_magic(style, strength, cost)
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

        if (
            current_time - self.attack_time
            > self.attack_cooldown + weapon_data[self.weapon]["cooldown"]
        ):
            self.attacking = False

        if not self.can_switch_weapon:
            if current_time - self.weapon_switch_time >= self.switch_duration_cooldown:
                self.can_switch_weapon = True

        if not self.can_switch_magic:
            if current_time - self.magic_switch_time >= self.switch_duration_cooldown:
                self.can_switch_magic = True
        if current_time - self.vulnerable_time > self.vulnerable_cooldown:
            self.vulnerable = True

    def flickering(self):
        if not self.vulnerable:
            self.image.set_alpha(self.wave_value())
        else:
            self.image.set_alpha(255)

    def get_full_weapon_damage(self):
        base_damage = self.stats["attack"]
        weapon_damage = weapon_data[self.weapon]["damage"]
        return base_damage + weapon_damage

    def get_full_magic_damage(self):
        base_damage = self.stats["magic"]
        spell_damage = magic_data[self.magic]["strength"]
        return base_damage + spell_damage

    def get_value_by_index(self, index):
        return list(self.stats.values())[index]

    def get_cost_by_index(self, index):
        return list(self.upgrade_cost.values())[index]

    def energy_recovery(self):
        if self.energy < self.stats["energy"]:
            self.energy += 0.01 * self.stats["magic"]
        else:
            self.energy = self.stats["energy"]

    def update(self):
        self.input()
        self.cooldowns()
        self.get_status()
        self.animate()
        self.flickering()
        self.move(self.stats["speed"])
        self.energy_recovery()
        # debug(f"{self.status} {self.magic}")
        pass
