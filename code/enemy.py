import pygame
from entity import Entity
from settings import monster_data
from debug import debug
import time
from boubble import TextBubble
import json
import asyncio

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from persona import Persona
    from memstream import MemoryStream

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
        persona: "Persona",
        memory: "MemoryStream",
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

        # graphic setup
        path = "../graphics/monsters/"
        self.animations = {"idle": [], "move": [], "attack": []}
        self.import_graphics(path, monster_name, self.animations)
        self.text_bubble = None

        self.status = "idle"
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)

        # movement
        # self.hitbox = self.rect.inflate(0, HITBOX_OFFSET["enemy"])
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

        # player interaction
        self.attack_time = 0
        self.attack_cooldown = 2000
        self.can_attack = True
        self.want_to_attack = False

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
        self.persona = persona
        self.memory = memory

        self.last_chat_time = 0
        self.last_summary_time = 0

        self.chat_interval = 3  # seconds
        self.summary_interval = 10  # seconds
        self.reason = None

        self.event_log_interval = 1000  # miliseconds
        self.last_event_log_time = 0

        self.decision_task = None
        self.summary_task = None

        self.current_decision = None

        # store decision and summary

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
        # this cooldown to prevent attack animation spam
        if not self.can_attack:
            current_time = pygame.time.get_ticks()
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

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

        if not self.first_hit:
            self.hit_sound.play()
            attack_type = player.attack_type
            if attack_type == "weapon" and not self.first_hit:
                self.health -= player.get_full_weapon_damage()
            elif attack_type == "magic" and not self.first_hit:
                self.health -= player.get_full_magic_damage()
                # magic damage
            self.first_hit = True
            # save attacked event
            self.memory.log_memory(self, player)

        if self.health <= 0:
            self.status = "death"
            # save death event
            self.memory.log_memory(self, player)

            self.kill()
            self.text_bubble.kill()
            self.trigger_death_particles(self.monster_name, self.rect.center)
            self.add_exp(self.exp)
            self.death_sound.play()

    def parse_decision(self, response):
        try:
            data = json.loads(response)

            coords = data["move"].split(",")
            if len(coords) != 2:
                raise ValueError("Move coordinates must be in format 'x,y'")

            x = float(coords[0].strip())
            y = float(coords[1].strip())

            self.target = pygame.math.Vector2(x, y)

            self.reason = data["reason"]
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

            # Try moving with obstacle avoidance
            next_pos = pygame.math.Vector2(self.hitbox.centerx, self.hitbox.centery)
            next_pos.x += self.direction.x * speed
            next_pos.y += self.direction.y * speed

            # Check for potential collisions
            test_rect = self.hitbox.copy()
            test_rect.center = next_pos

            will_collide = False
            for sprite in self.obstacle_sprites:
                if test_rect.colliderect(sprite.hitbox):
                    will_collide = True
                    break

            if will_collide:
                # Try alternate directions
                alternate_directions = [
                    pygame.math.Vector2(
                        self.direction.y, -self.direction.x
                    ),  # Try right
                    pygame.math.Vector2(
                        -self.direction.y, self.direction.x
                    ),  # Try left
                ]

                for alt_dir in alternate_directions:
                    test_rect = self.hitbox.copy()
                    test_rect.x += alt_dir.x * speed
                    test_rect.y += alt_dir.y * speed

                    can_move = True
                    for sprite in self.obstacle_sprites:
                        if test_rect.colliderect(sprite.hitbox):
                            can_move = False
                            break

                    if can_move:
                        self.direction = alt_dir
                        break

            # Apply movement
            self.hitbox.x += self.direction.x * speed
            self.collision("horizontal")
            self.hitbox.y += self.direction.y * speed
            self.collision("vertical")

            self.rect.center = self.hitbox.center

    def attack(self, player):
        # Execute attack if decided
        # can attack will end after attack animation
        # can attack will be set to true after cooldow
        if self.can_attack:
            self.status = "attack"
            self.attack_time = pygame.time.get_ticks()
            self.attack_sound.play()
            self.damage_player(self.attack_damage, self.attack_type)

    def interaction(self, player, distance):
        if not self.text_bubble:
            self.text_bubble = TextBubble([self.groups[0]])

        if self.reason:
            self.text_bubble.update_text(self.reason, self.rect)

        any_key_pressed = any(pygame.key.get_pressed())
        current_time = pygame.time.get_ticks()
        if (
            current_time - self.last_event_log_time >= self.event_log_interval
            and any_key_pressed
        ):
            self.memory.log_memory(self, player)
            self.last_event_log_time = current_time

        if self.persona.decision != self.current_decision:
            self.current_decision = self.persona.decision
            self.parse_decision(self.current_decision)
            if distance <= self.attack_radius and self.want_to_attack:
                self.attack(player)
            else:
                self.status = "move"

    def update(self):
        # main update for sprite
        # if self.status == "move":
        self.move(self.target, self.speed)

        self.animate()
        self.cooldown()

    def enemy_update(self, player):
        # self.get_status(player)
        distance, _ = self.get_player_distance_direction(player)

        # knockback
        if self.first_hit:
            self.direction *= -(player.knockback - self.resistance) / 5
            self.move(None, self.speed)

        if distance > self.notice_radius:
            self.status = "idle"
            self.direction = pygame.math.Vector2()

            if self.text_bubble:
                self.text_bubble.kill()
                self.text_bubble = None

        else:
            self.interaction(player, distance)

    async def enemy_decision(self, player):
        try:
            distance, _ = self.get_player_distance_direction(player)
            current_time = time.time()

            if distance <= self.notice_radius:
                if current_time - self.last_chat_time >= self.chat_interval:
                    # Add timeout to prevent hanging
                    if self.decision_task is None or self.decision_task.done():
                        self.decision_task = asyncio.create_task(
                            asyncio.wait_for(
                                self.persona.fetch_decision(self, player),
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
