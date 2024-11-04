import pygame
from entity import Entity
from settings import monster_data
from debug import debug
import time
import asyncio


class Enemy(Entity):

    def __init__(
        self,
        monster_name,
        pos,
        groups,
        obstacle_sprites,
        trigger_death_particles,
        add_exp,
        chat_api,
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
        self.max_health = monster_info["health"]
        self.exp = monster_info["exp"]
        self.speed = monster_info["speed"]
        self.attack_damage = monster_info["damage"]
        self.resistance = monster_info["resistance"]
        self.attack_radius = monster_info["attack_radius"]
        self.notice_radius = monster_info["notice_radius"]
        self.attack_type = monster_info["attack_type"]
        self.hostile = monster_info["hostile"]
        # self.attack_sound = monster_info["attack_sound"]

        # player interaction
        self.attack_time = 0
        self.attack_cooldown = 3000
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

        # ChatGPT API
        self.chat_api = chat_api
        self.last_chat_time = 0
        self.chat_interval = 3  # seconds

        self.movement_task = None
        self.current_direction = pygame.math.Vector2()

        self.attackable = "False"

    def get_player_distance_direction(self, player):
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(player.rect.center)

        distance = (player_vec - enemy_vec).magnitude()
        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()

        return distance, direction

    def cooldown(self):
        if not self.can_attack:
            current_time = pygame.time.get_ticks()
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

    def animate(self):
        animation = self.animations[self.status]

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
        self.image = animation[int(self.frame_index)]

    def attack(self):
        # Execute attack if decided
        if self.status == "attack" and self.can_attack:
            self.attack_time = pygame.time.get_ticks()
            self.attack_sound.play()
            self.can_attack = False

    def get_damage(self, player):
        if not self.first_hit:
            self.hit_sound.play()
            attack_type = player.attack_type
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

    async def fetch_decision(self, player):
        distance, direction = self.get_player_distance_direction(player)
        prompt = (
            # f"Entity '{self.monster_name}' has {self.health}/{self.max_health} health. "
            f"Entity is at position {self.rect.center} and player is at {player.rect.center}."
            f"Entity distance and direction to player: {distance}, {direction}."
            f"Entity can attack if distance less than {self.attack_radius}. "
            f"Entity is hostile:{self.hostile}. "
            'Respond next move for the entity with either "attack": "yes/no" to attack or "move: "x,y" where x,y is the direction vector to move. Example response: {"attack": "yes"} or {"move": "134,-23"}'
        )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self.chat_api.get_response, user_input=prompt),
                timeout=5.0,  # 1 second timeout
            )
            print(f"response: {response}")

            self.parse_decision_response(response)

        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error getting movement decision: {e}")
            # Keep the current direction on error

    def parse_decision_response(self, response):
        try:
            import json

            data = json.loads(response)

            # Check for attack decision
            if "attack" in data:
                # Expect format: {'attack': 'yes'} or {'attack': 'no'}
                if data["attack"].lower() == "yes":
                    self.status = "attack"

            # Check for move decision
            elif "move" in data:
                # Expect format: {'move': '123,145'}
                coords = data["move"].split(",")
                if len(coords) != 2:
                    raise ValueError("Move coordinates must be in format 'x,y'")

                x = float(coords[0].strip())
                y = float(coords[1].strip())

                vector = pygame.math.Vector2(x, y)
                if vector.magnitude() > 0:
                    vector = vector.normalize()
                self.direction = vector
                self.status = "move"
            else:
                print(
                    "Invalid response format - must contain 'attack' or 'move' or 'idle'"
                )

        except (json.JSONDecodeError, ValueError, AttributeError, KeyError) as e:
            print(f"Error parsing decision response: {e}")

    def update(self):

        if self.status == "move":  # prevent enemy from moving when attacking
            self.move(self.speed)

        self.attack()
        self.animate()
        self.cooldown()
        self.check_death()
        # debug(f"{self.speed} {self.status}")

    def enemy_update(self, player):
        # self.get_status(player)

        # knockback
        if self.first_hit:
            _, self.direction = self.get_player_distance_direction(player)
            self.direction *= -(player.knockback - self.resistance) / 5
            self.move(self.speed)

    async def enemy_decision(self, player):
        # Get current state
        distance, _ = self.get_player_distance_direction(player)
        current_time = time.time()

        # If enemy is outside notice radius, return to idle
        if distance > self.notice_radius:
            self.status = "idle"
            self.direction = pygame.math.Vector2()
            return

        # Update attackable status
        else:
            # Check if it's time for a new decision
            if current_time - self.last_chat_time >= self.chat_interval:
                if self.movement_task is None or self.movement_task.done():
                    self.movement_task = asyncio.create_task(
                        self.fetch_decision(player)
                    )
                self.last_chat_time = current_time

        debug(f"{self.direction, self.status, self.attackable}")
