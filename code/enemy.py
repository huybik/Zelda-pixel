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
        self.animations = {"idle": [], "move": [], "attack": []}
        self.import_graphics(path, name, self.animations)
        self.text_bubble = None

        self.status = "idle"
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)

        # movement
        self.hitbox = self.rect
        self.obstacle_sprites = obstacle_sprites
        self.target_location = pygame.math.Vector2()
        self.current_speed = 0

        # stats
        self.name = name
        monster_info = monster_data[self.name]
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
        self.full_name = full_name

        self.want_to_attack = False

        # ChatGPT API params
        self.last_chat_time = 0
        self.last_summary_time = 0

        self.chat_interval = 3  # seconds
        self.summary_interval = 10  # seconds
        self.reason = None

        self.decision_task = None
        self.summary_task = None

        self.current_decision = None
        self.event_status = None
        self.target_name = None

        # cooldowns
        self.observation_time = 0
        self.observation_cooldown = 1000
        self.can_save_observation = True

        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_duration = 2000

        self.attack_time = 0
        self.attack_cooldown = 2000
        self.can_attack = True

        # sound
        self.attack_sound = pygame.mixer.Sound(monster_info["attack_sound"])
        self.attack_sound.set_volume(0.6)

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
        # Execute attack if decided
        # can attack will end after attack animation
        # can attack will be set to true after cooldow
        if self.target_name != "player":
            print(self.target_name)

        if self.can_attack:
            self.status = "attack"
            self.attack_time = pygame.time.get_ticks()
            self.attack_sound.play()
            target.get_damage(attacker=self)
            self.event_status = f"attack entity {target.full_name}"
            self.can_save_observation = True

    def flickering(self):
        if not self.vulnerable:
            self.image.set_alpha(wave_value())
        else:
            self.image.set_alpha(255)

    def interaction(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):
        # this is entity player interaction
        # TODO: refactor this to not handle entity vs entity
        if not self.text_bubble:
            self.text_bubble = TextBubble([self.groups[0]])

        if self.reason:
            self.text_bubble.update_text(self.reason, self.rect)

        if self.persona.decision != self.current_decision:
            self.current_decision = self.persona.decision
            decision = self.persona.parse_decision(self.current_decision)
            if decision:
                self.target_location = decision["target_location"]
                self.want_to_attack = decision["want_to_attack"]
                self.target_name = decision["target_name"]
                self.reason = decision["reason"]

        # chose target

        target = player
        for entity in entities:
            if entity != self and entity.full_name == self.target_name:
                target = entity
                break

        distance, _ = get_distance_direction(self, target)
        if distance <= self.attack_radius and self.want_to_attack:
            self.attack(target)
        else:
            self.status = "move"

        # any_key_pressed = any(pygame.key.get_pressed())
        # if self.can_save_observation and any_key_pressed:
        if self.can_save_observation:
            self.memory.save_observation(self, player, entities, objects)
            self.observation_time = pygame.time.get_ticks()
            self.can_save_observation = False

    def update(self):
        # main update for sprite
        # if self.status == "move":
        self.move(self.target_location, self.speed)

        self.animate()
        self.cooldown()
        self.flickering()

    def enemy_update(
        self, player: "Player", entities: list["Entity"], objects: list["Tile"]
    ):
        distance, _ = get_distance_direction(self, player)
        # knockback

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
                                self.persona.summary_context(
                                    self, player, entities, objects
                                ),
                                timeout=5.0,
                            )
                        )

                        self.last_summary_time = current_time

        except Exception as e:
            print(f"Enemy decision error: {e}")
