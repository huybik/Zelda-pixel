import pygame
from entity import Entity
from support import import_folder
from settings import monster_data, HITBOX_OFFSET
from debug import debug
from player import Player


class Enemy(Entity):

    def __init__(
        self,
        monster_name,
        pos,
        groups,
        obstacle_sprites,
        trigger_death_particles,
        add_exp,
    ):

        # general setup
        super().__init__(groups)
        self.sprite_type = "enemy"
        self.trigger_death_particles = trigger_death_particles
        self.add_exp = add_exp

        # graphic setup
        path = "../graphics/monsters/"
        self.animations = {"idle": [], "move": [], "attack": []}
        self.import_graphics(path, monster_name, self.animations)

        self.status = "idle"
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)

        # movement
        # self.hitbox = self.rect.inflate(0, HITBOX_OFFSET["enemy"])
        self.hitbox = self.rect
        self.obstacle_sprites = obstacle_sprites

        # stats
        self.monster_name = monster_name
        monster_info = monster_data[self.monster_name]
        self.health = monster_info["health"]
        self.exp = monster_info["exp"]
        self.speed = monster_info["speed"]
        self.attack_damage = monster_info["damage"]
        self.resistance = monster_info["resistance"]
        self.attack_radius = monster_info["attack_radius"]
        self.notice_radius = monster_info["notice_radius"]
        self.attack_type = monster_info["attack_type"]
        # self.attack_sound = monster_info["attack_sound"]

        # player interaction
        self.attack_time = 0
        self.attack_cooldown = 400
        self.can_attack = True

        # invincibility timer
        self.first_hit = False

        # sounds
        self.death_sound = pygame.mixer.Sound("../audio/death.wav")
        self.hit_sound = pygame.mixer.Sound("../audio/hit.wav")
        self.attack_sound = pygame.mixer.Sound(monster_info["attack_sound"])
        self.death_sound.set_volume(0.6)
        self.hit_sound.set_volume(0.6)
        self.attack_sound.set_volume(0.6)

        # self.invincibility_duration = 300

    def get_player_distance_direction(self, player):
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(player.rect.center)

        distance = (player_vec - enemy_vec).magnitude()
        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()

        return distance, direction

    def get_status(self, player):
        distance, _ = self.get_player_distance_direction(player)

        if distance <= self.attack_radius and self.can_attack:
            if self.status != "attack":
                self.frame_index = 0
                self.attack_sound.play()
            self.status = "attack"
        elif distance > self.attack_radius and distance <= self.notice_radius:
            self.status = "move"
        else:
            self.status = "idle"

    def actions(self, player):
        if self.status == "attack":
            self.attack_time = pygame.time.get_ticks()
        elif self.status == "move":
            _, self.direction = self.get_player_distance_direction(player)
        else:  # idle
            self.direction = pygame.math.Vector2()

    def cooldown(self):
        if not self.can_attack:
            current_time = pygame.time.get_ticks()
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True
                print("can attack")

    def animate(self):
        animation = self.animations[self.status]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.status == "attack":
                self.can_attack = False
            self.frame_index = 0
        self.image = animation[int(self.frame_index)]

    def get_damage(self, player: Player, attack_type):
        self.hit_sound.play()
        if attack_type == "weapon" and not self.first_hit:
            self.health -= player.get_full_weapon_damage()
        elif attack_type == "magic" and not self.first_hit:
            self.health -= player.get_full_magic_damage()
            # magic damage
        self.first_hit = True

    def check_death(self):  # this should be inside enemy
        if self.health <= 0:

            self.kill()
            self.trigger_death_particles(self.monster_name, self.rect.center)
            self.add_exp(self.exp)
            self.death_sound.play()

    # def hit_reaction(self, player: Player):
    #     if self.first_hit:
    #         self.direction *= -(player.knockback - self.resistance)

    def update(self):
        if self.status == "move":  # prevent enemy from moving when attacking
            self.move(self.speed)

        self.animate()
        self.cooldown()
        self.check_death()
        # debug(f"{self.speed} {self.status}")
        pass

    def enemy_update(self, player: Player):
        # knockback
        if self.first_hit:  # first hit timer depends on weapon cool down here
            # move oposit direction
            _, self.direction = self.get_player_distance_direction(player)
            # increase direction magnitude
            self.direction *= -(player.knockback - self.resistance) / 5
            self.move(self.speed)
        # self.hit_reaction(player)
        self.get_status(player)
        self.actions(player)
        # debug(f"{self.direction}")

    # self.move
