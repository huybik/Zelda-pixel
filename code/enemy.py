import pygame
from entity import Entity
from settings import monster_data, output_format
from debug import debug
import time
from tooltips import TextBubble, StatusBars
import json
import asyncio
from persona import Persona
from memstream import MemoryStream
from support import get_distance_direction, wave_value
import random

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity
    from tile import Tile
    from player import Player

# from ui import UI


class Enemy(Entity):

    def __init__(
        self,
        name,
        full_name,
        pos,
        groups,
        obstacle_sprites,
    ):

        # general setup
        super().__init__(groups)
        self.sprite_type = "enemy"
        self.groups = groups
        self.memory = MemoryStream()
        self.persona = Persona()

        # graphic setup
        path = "../graphics/monsters/"
        self.animations = {
            "idle": [],
            "move": [],
            "attack": [],
            "heal": [],
            "mine": [],
            "runaway": [],
        }
        self.import_graphics(path, name, self.animations)

        self.action = "idle"
        self.image = self.animations[self.action][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)

        self.hitbox = self.rect
        self.starting_point = pos

        # movement
        self.obstacle_sprites = obstacle_sprites
        self.target_location = pygame.math.Vector2()
        self.current_speed = 0

        # stats
        self.name = name
        monster_info = monster_data[self.name]
        self.monster_info = monster_info

        self.health = monster_info["health"]
        self.max_health = monster_info["health"]
        self.exp = monster_info["exp"]
        self.speed = monster_info["speed"]
        self.attack_damage = monster_info["damage"]
        self.resistance = monster_info["resistance"]
        self.act_radius = monster_info["act_radius"]
        self.notice_radius = monster_info["notice_radius"]
        self.attack_type = monster_info["attack_type"]
        self.characteristic = monster_info["characteristic"]
        self.full_name = full_name

        self.energy = self.max_health
        self.max_energy = self.max_health
        self.aggression = 0

        # ChatGPT API params
        self.last_chat_time = 0
        self.last_summary_time = 0
        self.last_internal_move_update = 0

        self.chat_interval = 6  # seconds
        self.summary_interval = 20  # seconds
        self.internal_move_update_interval = 0.5  # seconds

        self.reason = None

        self.decision_task = None
        self.summary_task = None

        self.current_decision = None
        self.event_status = None

        # cooldowns
        self.observation_time = 0
        self.observation_cooldown = 1000
        self.can_save_observation = True

        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_duration = 1000

        self.act_time = 0
        self.act_cooldown = 1000
        self.can_act = True

        # sound
        self.attack_sound = pygame.mixer.Sound(monster_info["attack_sound"])
        self.attack_sound.set_volume(0.6)
        self.heal_sound = pygame.mixer.Sound("../audio/heal.wav")
        self.heal_sound.set_volume(0.6)

        # Add status bars
        self.status_bars = None
        # upgrade cost
        self.upgrade_cost = 100
        self.upgrade_percentage = 0.05  # this increase cost and stat

        self.text_bubble = TextBubble([self.groups[0]])
        self.status_bars = StatusBars(
            self.groups[0], (self.rect.centerx, self.rect.centery)
        )

    def cooldown(self):
        # this cooldown to prevent attack animation spam
        current_time = pygame.time.get_ticks()

        if not self.can_act:
            if current_time - self.act_time >= self.act_cooldown:
                self.can_act = True
        if current_time - self.observation_time >= self.observation_cooldown:
            self.can_save_observation = True
        if current_time - self.vulnerable_time >= self.vulnerable_duration:
            self.vulnerable = True

    def animate(self):
        animation = self.animations[self.animate_sequence]

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
            if self.animate_sequence == self.action:
                # self.can_act = False
                self.animate_sequence = "move"
        self.image = animation[int(self.frame_index)]

        # Tint the sprite red based on aggression
        if self.aggression > 0:
            tinted_image = self.image.copy()
            # Convert aggression (0-100) to alpha value (0-255)
            alpha = min(255, int((self.aggression / 100) * 255))
            # Increase red tint while decreasing green/blue as aggression rises
            tinted_image.fill(
                (255, max(255 - alpha, 128), max(255 - alpha, 128)),
                special_flags=pygame.BLEND_RGBA_MULT,
            )
            self.image = tinted_image

    def move(self, target: pygame.math.Vector2, speed: int):
        current = pygame.math.Vector2(self.hitbox.centerx, self.hitbox.centery)

        if target:
            # Calculate desired direction
            desired_direction = target - current
            distance = desired_direction.magnitude()

            if distance != 0:
                desired_direction = desired_direction.normalize()
            if distance < 3:
                return

            # Smooth direction changes (lerp between current and desired direction)
            if hasattr(self, "current_direction"):
                smoothing = 0.1  # Lower value = smoother movement
                self.current_direction = pygame.math.Vector2(
                    self.current_direction.x
                    + (desired_direction.x - self.current_direction.x) * smoothing,
                    self.current_direction.y
                    + (desired_direction.y - self.current_direction.y) * smoothing,
                )
            else:
                self.current_direction = desired_direction

            self.direction = self.current_direction.normalize()

            # Check if we're stuck
            if hasattr(self, "last_position"):
                pos_difference = current - self.last_position
                if pos_difference.length() < 0.1:  # If barely moving
                    self.stuck_time = getattr(self, "stuck_time", 0) + 1
                    if self.stuck_time > 10:  # If stuck for too long
                        # Try moving perpendicular to current direction
                        self.direction = pygame.math.Vector2(
                            -self.direction.y, self.direction.x
                        )
                        self.stuck_time = 0
                else:
                    self.stuck_time = 0
            self.last_position = current

        # Gradual speed adjustment
        base_speed = speed
        if self.check_collision(self.hitbox):
            self.current_speed = (
                getattr(self, "current_speed", base_speed) * 0.95
            )  # Gradual slowdown
        else:
            self.current_speed = min(
                base_speed, getattr(self, "current_speed", base_speed) * 1.05
            )  # Gradual speedup

        # Apply movement
        if self.current_speed > 0:
            move_delta = self.direction * self.current_speed
        else:
            move_delta = self.direction * self.speed
        self.hitbox.x += move_delta.x
        self.collision("horizontal")
        self.hitbox.y += move_delta.y
        self.collision("vertical")
        self.rect.center = self.hitbox.center

    def check_collision(self, test_rect):
        for sprite in self.obstacle_sprites:
            if test_rect.colliderect(sprite.hitbox):
                return True
        return False

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

    def attack(self, target: "Entity"):
        # set event name
        self.attack_sound.play()
        if target.sprite_type == "player" or target.sprite_type == "enemy":
            target.get_damage(attacker=self)

    def heal(self, target: "Entity"):
        if self.energy > 0 and target.health < target.max_health:
            self.heal_sound.play()

            # action
            self.energy -= self.attack_damage
            if self.energy < 0:
                self.energy = 0

            target.get_heal(healer=self)

    def mine(self, target: "Tile"):

        # save status
        # action
        if self.energy < self.max_energy:
            self.energy += int(0.05 * self.max_energy)
            if self.energy > self.max_energy:
                self.energy = self.max_energy
        if self.health < self.max_health:
            self.health += int(0.05 * self.max_health)
            if self.health > self.max_health:
                self.health = self.max_health

        self.animation_player.create_particles(
            "sparkle", target.hitbox.center, [self.groups[0]]
        )
        self.exp += 10

    def respawn(self):
        self.rect.topleft = self.starting_point
        self.hitbox = self.rect
        self.health = self.monster_info["health"]
        self.max_health = self.monster_info["health"]
        self.exp = self.monster_info["exp"]
        self.speed = self.monster_info["speed"]
        self.attack_damage = self.monster_info["damage"]

        self.energy = self.max_health
        self.max_energy = self.max_health
        self.vulnerable = False

    def upgrade(self):
        if self.exp >= self.upgrade_cost:
            # self.exp -= self.upgrade_cost
            self.upgrade_cost += int(self.upgrade_cost * (1 + self.upgrade_percentage))
            self.max_health = int(self.max_health * (1 + self.upgrade_percentage))
            self.max_energy = int(self.max_energy * (1 + self.upgrade_percentage))
            self.speed = int(self.speed * (1 + self.upgrade_percentage))
            self.attack_damage = int(self.attack_damage * (1 + self.upgrade_percentage))

    def flickering(self):
        if not self.vulnerable:
            self.image.set_alpha(wave_value())
        else:
            self.image.set_alpha(255)

    def set_decision(self, decision):
        if decision:
            self.target_name = decision["target_name"]
            self.aggression = int(decision["aggression"])
            self.action = decision["action"]
            self.reason = decision["reason"]

            # self.target_name = "player"
            # self.action = "runaway"

    def interaction(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):

        if self.persona.decision != self.current_decision:
            self.set_decision(self.persona.decision)
            self.current_decision = self.persona.decision

        else:
            target = self.target_select(player, entities, objects)
            if target:
                distance, _ = get_distance_direction(self, target)
                if distance <= self.act_radius and self.can_act:

                    if self.action == "attack":
                        self.attack(target)
                    elif self.action == "heal":
                        self.heal(target)
                    elif self.action == "mine":
                        self.mine(target)
                    elif self.action == "runaway":
                        self.runaway(target)

                    self.can_act = False
                    self.animate_sequence = self.action
                    self.act_time = pygame.time.get_ticks()

                    event_status = f"{self.action} {target.full_name}"

                    if self.event_status != event_status:
                        self.event_status = event_status
                        self.can_save_observation = True

                current_time = pygame.time.get_ticks()
                if (
                    current_time - self.last_internal_move_update
                    >= self.internal_move_update_interval
                ):
                    self.internal_move_update(target)
                    self.last_internal_move_update = current_time

        # any_key_pressed = any(pygame.key.get_pressed())
        # if self.can_save_observation and any_key_pressed:

    def target_select(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):
        # chose target
        target = None
        if self.target_name == "player":
            target = player

        for entity in entities:
            if entity != self and entity.full_name == self.target_name:
                target = entity
                break
        for object in objects:
            if object.full_name == self.target_name:
                target = object
                break

        return target

    def update(self):
        # main update for sprite
        # if self.action == "move":
        self.move(self.target_location, self.speed)

        self.animate()
        self.cooldown()
        self.flickering()
        self.upgrade()

        # Update status bars position to follow enemy

    def enemy_update(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):
        distance, _ = get_distance_direction(self, player)
        # knockback

        if distance > self.notice_radius:
            self.action = "idle"
            self.direction = pygame.math.Vector2()
            self.target_name = None

            # if self.text_bubble:
            #     self.text_bubble.kill()
            #     self.text_bubble = None
            # if self.status_bars:
            #     self.status_bars.kill()
            #     self.status_bars = None

        else:
            self.interaction(player, entities, objects)

        self.status_bars.update_rect(
            self  # Max energy (if you want to add energy system later)
        )

        if self.reason:
            self.text_bubble.update_text(
                f"{self.full_name}:{self.action} {self.reason}", self.rect
            )

        # save observation
        if self.can_save_observation:
            self.memory.save_observation(self, player, entities, objects)
            self.observation_time = pygame.time.get_ticks()
            self.can_save_observation = False

        # wander arround if no target
        if not self.target_name or self.target_name == "None":
            # walk aimlessly for a bit to find new target
            self.target_location = pygame.math.Vector2(
                random.randint(0, 800),  # Assuming the game screen width is 800
                random.randint(0, 600),  # Assuming the game screen height is 600
            )
        # Update status bars

    def runaway(self, target):
        pass

    def internal_move_update(self, target: "Entity"):

        if self.vulnerable:  # avoid moving when knockback in effect
            if self.action == "runaway":
                distance, direction = get_distance_direction(self, target)

                self.direction = -direction.normalize()
                self.target_location = pygame.math.Vector2()
            elif (
                self.action == "attack"
                or self.action == "mine"
                or self.action == "heal"
            ):
                self.target_location = pygame.math.Vector2(
                    target.hitbox.center
                ) + pygame.math.Vector2(random.randint(-3, 3), random.randint(-3, 3))

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
                                self.persona.fetch_decision(self),
                                timeout=5.0,
                            )
                        )
                        self.last_chat_time = current_time

                if current_time - self.last_summary_time >= self.summary_interval:
                    if self.summary_task is None or self.summary_task.done():
                        self.summary_task = asyncio.create_task(
                            asyncio.wait_for(
                                self.persona.summary_context(self),
                                timeout=10.0,
                            )
                        )

                        self.last_summary_time = current_time

        except Exception as e:
            print(f"Enemy decision error: {e}")
