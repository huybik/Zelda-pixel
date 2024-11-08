import pygame
from entity import Entity
from settings import monster_data
from debug import debug
import time
from boubble import TextBubble
import json
import asyncio
from persona import Persona
from memstream import MemoryStream
from support import get_distance_direction, wave_value

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity
    from tile import Tile
    from player import Player

# from ui import UI


class Enemy(Entity):

    def __init__(
        self,
        monster_name,
        pos,
        groups,
        obstacle_sprites,
        trigger_death_particles,
        add_exp,
        monster_id,
        damage_player,
    ):

        # general setup
        super().__init__(groups)
        self.sprite_type = "enemy"
        self.trigger_death_particles = trigger_death_particles
        self.add_exp = add_exp
        self.damage_player = damage_player
        self.groups = groups
        self.memory = MemoryStream()
        self.persona = Persona()

        # graphic setup
        path = "../graphics/monsters/"
        self.animations = {"idle": [], "move": [], "attack": []}
        self.import_graphics(path, monster_name, self.animations)
        self.text_bubble = None

        self.status = "idle"
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)

        # movement
        self.hitbox = self.rect
        self.obstacle_sprites = obstacle_sprites
        self.target = pygame.math.Vector2()

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
        self.characteristic = monster_info["characteristic"]
        self.monster_id = monster_id

        self.want_to_attack = False

        # sounds
        self.death_sound = pygame.mixer.Sound("../audio/death.wav")
        self.hit_sound = pygame.mixer.Sound("../audio/hit.wav")
        self.attack_sound = pygame.mixer.Sound(monster_info["attack_sound"])
        self.death_sound.set_volume(0.6)
        self.hit_sound.set_volume(0.6)
        self.attack_sound.set_volume(0.6)

        # ChatGPT API params
        self.last_chat_time = 0
        self.last_summary_time = 0

        self.chat_interval = 3  # seconds
        self.summary_interval = 10  # seconds
        self.reason = None

        self.decision_task = None
        self.summary_task = None

        self.current_decision = None

        # cooldowns
        self.observation_time = 0
        self.observation_cooldown = 1000
        self.can_save_observation = True

        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_duration = 400

        self.attack_time = 0
        self.attack_cooldown = 2000
        self.can_attack = True

    def cooldown(self):
        # this cooldown to prevent attack animation spam
        current_time = pygame.time.get_ticks()

        if not self.can_attack:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True
        if current_time - self.observation_time >= self.observation_cooldown:
            self.can_save_observation = True
        if current_time - self.vulnerable_time >= self.vulnerable_duration:
            self.vulnerable = True

    def animate(self):
        animation = self.animations[self.status]

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
            if self.status == "attack":
                self.can_attack = False
                self.status = "move"
        self.image = animation[int(self.frame_index)]

    def get_damage(self, player):
        # log memory

        if self.vulnerable:
            self.hit_sound.play()
            attack_type = player.attack_type
            if attack_type == "weapon":
                self.health -= player.get_full_weapon_damage()
            elif attack_type == "magic":
                self.health -= player.get_full_magic_damage()
                # magic damage

            # set vulnerable to false
            self.vulnerable = False
            self.vulnerable_time = pygame.time.get_ticks()

        if self.health <= 0:
            self.status = "death"
            # save death event

            self.kill()
            self.text_bubble.kill()
            self.trigger_death_particles(self.monster_name, self.rect.center)
            self.add_exp(self.exp)
            self.death_sound.play()

        # save attacked event
        self.can_save_observation = True

    def parse_decision(self, response):
        try:
            data = json.loads(response)

            coords = data["move"].split(",")
            if len(coords) != 2:
                raise ValueError("Move coordinates must be in format 'x,y'")

            x = float(coords[0].strip())
            y = float(coords[1].strip())

            self.target = pygame.math.Vector2(x, y)

            self.reason = self.monster_id + ":" + data["reason"]
            self.want_to_attack = data["attack"].lower() == "yes"

        except (json.JSONDecodeError, ValueError, AttributeError, KeyError) as e:
            print(f"Error parsing decision response: {e}")

    def move(self, target: pygame.math.Vector2, speed: int):
        # Calculate direction vector to target location
        current = pygame.math.Vector2(self.hitbox.centerx, self.hitbox.centery)

        if target:
            self.direction = target - current
            distance = self.direction.magnitude()
            if distance != 0:
                self.direction = self.direction.normalize()
            if distance < 3:
                return

            # Look ahead several steps to find best path
            best_direction = self.direction
            least_collisions = float("inf")
            prediction_steps = 5  # Number of steps to look ahead

            # Test main direction and alternates
            possible_directions = [
                self.direction,
                pygame.math.Vector2(self.direction.y, -self.direction.x),
                pygame.math.Vector2(-self.direction.y, self.direction.x),
                pygame.math.Vector2(-self.direction.y, -self.direction.x),
            ]

            for test_direction in possible_directions:
                collisions = 0
                test_rect = self.hitbox.copy()

                # Predict multiple steps ahead
                for step in range(prediction_steps):
                    next_pos = pygame.math.Vector2(test_rect.centerx, test_rect.centery)
                    next_pos.x += test_direction.x * speed
                    next_pos.y += test_direction.y * speed
                    test_rect.center = next_pos

                    if self.check_collision(test_rect):
                        collisions += 1
                        break

                # Choose direction with least predicted collisions
                if collisions < least_collisions:
                    least_collisions = collisions
                    best_direction = test_direction

            # Use the best found direction
            self.direction = best_direction

            self.rect.center = self.hitbox.center

        # Apply movement
        self.hitbox.x += self.direction.x * speed
        self.collision("horizontal")
        self.hitbox.y += self.direction.y * speed
        self.collision("vertical")

    def check_collision(self, test_rect):
        for sprite in self.obstacle_sprites:
            if test_rect.colliderect(sprite.hitbox):
                return True
        return False

    def attack(self):
        # Execute attack if decided
        # can attack will end after attack animation
        # can attack will be set to true after cooldow
        if self.can_attack:
            self.status = "attack"
            self.attack_time = pygame.time.get_ticks()
            self.attack_sound.play()
            self.damage_player(self.attack_damage, self.attack_type)
            self.can_save_observation = True

    def flickering(self):
        if not self.vulnerable:
            self.image.set_alpha(wave_value())
        else:
            self.image.set_alpha(255)

    def interaction(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):

        if not self.text_bubble:
            self.text_bubble = TextBubble([self.groups[0]])

        if self.reason:
            self.text_bubble.update_text(self.reason, self.rect)

        if self.persona.decision != self.current_decision:
            self.current_decision = self.persona.decision
            self.parse_decision(self.current_decision)

        distance, _ = get_distance_direction(self, player)
        if distance <= self.attack_radius and self.want_to_attack:
            self.attack()
        else:
            self.status = "move"

        any_key_pressed = any(pygame.key.get_pressed())
        if self.can_save_observation and any_key_pressed:
            self.memory.save_observation(self, player, entities, objects)
            self.observation_time = pygame.time.get_ticks()
            self.can_save_observation = False

    def update(self):
        # main update for sprite
        # if self.status == "move":
        self.move(self.target, self.speed)

        self.animate()
        self.cooldown()
        self.flickering()

    def enemy_update(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):
        distance, _ = get_distance_direction(self, player)
        # knockback
        if not self.vulnerable:
            _, self.direction = get_distance_direction(self, player)
            self.direction *= -(player.knockback - self.resistance) / 5
            self.move(None, self.speed)
        if distance > self.notice_radius:
            self.status = "idle"
            self.direction = pygame.math.Vector2()

            if self.text_bubble:
                self.text_bubble.kill()
                self.text_bubble = None

        else:
            self.interaction(player, entities, objects)

    async def enemy_decision(self, player, entities, objects):
        try:
            distance, _ = get_distance_direction(self, player)
            current_time = time.time()

            if distance <= self.notice_radius:
                if current_time - self.last_chat_time >= self.chat_interval:
                    # Add timeout to prevent hanging
                    if self.decision_task is None or self.decision_task.done():
                        self.decision_task = asyncio.create_task(
                            asyncio.wait_for(
                                self.persona.fetch_decision(
                                    self, player, entities, objects
                                ),
                                timeout=5.0,
                            )
                        )
                        self.last_chat_time = current_time

                if current_time - self.last_summary_time >= self.summary_interval:
                    if self.summary_task is None or self.summary_task.done():
                        self.summary_task = asyncio.create_task(
                            asyncio.wait_for(
                                self.persona.summary_context(self),
                                timeout=5.0,
                            )
                        )

                        self.last_summary_time = current_time

        except Exception as e:
            print(f"Enemy decision error: {e}")
