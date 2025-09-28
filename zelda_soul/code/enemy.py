import pygame
from entity import Entity
from settings import monster_data, CHAT_INTERVAL, SUMMARY_INTERVAL, MEMORY_SIZE
import time
from tooltips import TextBubble, StatusBars
from persona import Persona
from memstream import MemoryStream
from support import get_distance_direction, wave_value
import random
from typing import TYPE_CHECKING
from behaviors import AggressiveBehavior, FriendlyBehavior, NeutralBehavior, Behavior

if TYPE_CHECKING:
    from entity import Entity
    from tile import Tile
    from player import Player
    from ai_manager import AIManager
    from compute_manager import ComputeManager

class Enemy(Entity):
    def __init__(
        self,
        name,
        full_name,
        pos,
        groups,
        obstacle_sprites,
        visible_sprite,
        ai_manager: "AIManager",
        compute_manager: "ComputeManager",
    ):
        super().__init__(groups)
        self.sprite_type = "enemy"
        self.memory = MemoryStream()
        self.persona = Persona()
        self.ai_manager = ai_manager
        self.compute_manager = compute_manager

        # Graphics and basic setup
        self.animations = {
            "idle": [], "move": [], "attack": [], "heal": [], "mine": [], "runaway": []
        }
        self.import_graphics("../graphics/monsters/", name, self.animations)

        self.action = "idle"
        
        if not self.animations.get(self.action):
            self.image = pygame.Surface((64, 64))
            self.image.fill('magenta')
            print(f"Warning: Animation frames for action '{self.action}' not found for '{name}'.")
        else:
            self.image = self.animations[self.action][0]

        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect
        self.starting_point = pos

        # Movement
        self.obstacle_sprites = obstacle_sprites
        self.visible_sprite = visible_sprite
        self.target_location = pygame.math.Vector2()
        self.path = None
        self.is_path_requested = False
        self.old_target_location = pygame.math.Vector2()

        # Stats
        monster_info = monster_data[name]
        self.name = name
        self.full_name = full_name
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
        self.energy = self.max_health
        self.max_energy = self.max_health
        self.vigilant = 0
        self.upgrade_cost = 100
        self.upgrade_percentage = 0.01
        self.timber = 0
        self.max_timber = 10

        # AI Behavior (Strategy Pattern)
        self.behavior: Behavior = self._get_behavior(self.characteristic)

        # Timers and cooldowns
        self.last_chat_time = 0
        self.last_summary_time = 0
        self.last_internal_move_update = 0
        self.chat_interval = CHAT_INTERVAL
        self.summary_interval = SUMMARY_INTERVAL
        self.internal_move_update_interval = 500
        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_duration = 1000
        self.act_time = 0
        self.act_cooldown = 1000
        self.can_act = True
        
        from resources import load_sound 
        self.attack_sound = load_sound(monster_info["attack_sound"])
        self.attack_sound.set_volume(0.6)
        self.heal_sound = load_sound("../audio/heal.wav")
        self.heal_sound.set_volume(0.6)

        # Tooltips and other components
        self.text_bubble = TextBubble(self.visible_sprite)
        self.status_bars = StatusBars(self.visible_sprite)
        self.reason = ""

    def _get_behavior(self, characteristic: str) -> Behavior:
        """Assigns a behavior strategy based on the enemy's characteristic."""
        if "friend" in characteristic or "help" in characteristic:
            return FriendlyBehavior()
        elif "aggressive" in characteristic or "enemy" in characteristic:
            return AggressiveBehavior()
        else:
            return NeutralBehavior()

    def decide(self):
        """Requests a decision from the AI manager using the current behavior."""
        prompt = self.persona.prompt_generator.format_decision_prompt(self)
        self.ai_manager.request(self.full_name, 'decision', prompt)

    def summary(self):
        """Requests a summary from the AI manager."""
        prompt = self.persona.prompt_generator.format_summary_prompt(self)
        self.ai_manager.request(self.full_name, 'summary', prompt)

    def process_ai_responses(self):
        """Polls for and applies AI responses."""
        parsed_decision = self.ai_manager.get_response(self.full_name, 'decision')
        if parsed_decision:
            self.set_decision(parsed_decision)

        new_summary_text = self.ai_manager.get_response(self.full_name, 'summary')
        if new_summary_text and new_summary_text != "ERROR":
            self.persona.save_summary(new_summary_text, f"summary_{self.full_name}.json")
            
    def process_compute_responses(self):
        """Polls for and applies compute worker responses."""
        new_path = self.compute_manager.get_response(self.full_name, 'pathfinding')
        if new_path is not None:
            self.path = new_path
            self.is_path_requested = False

    def enemy_update(self, player: "Player", entities: list["Entity"], objects: list["Tile"]):
        """Main update loop for the enemy."""
        distance, _ = get_distance_direction(self, player)
        self.process_ai_responses()
        self.process_compute_responses()
        
        nearby_entities = [e for e in entities if get_distance_direction(self, e)[0] <= self.notice_radius and e != self]
        nearby_objects = [o for o in objects if get_distance_direction(self, o)[0] <= self.notice_radius]

        if distance <= self.notice_radius:
            self.behavior.update(self, player, nearby_entities, nearby_objects)

        self.move(self.target_location, self.speed, objects)
        self.control_update(player, nearby_entities, nearby_objects)
        self.check_death()

        self.status_bars.update_rect(self)
        if self.reason:
            self.text_bubble.update_text(f"{self.action} {self.target_name or ''}: {self.reason}", self.rect)
    
    def cooldown(self):
        current_time = pygame.time.get_ticks()
        if not self.can_act and current_time - self.act_time >= self.act_cooldown:
            self.can_act = True
        if not self.vulnerable and current_time - self.vulnerable_time >= self.vulnerable_duration:
            self.vulnerable = True

    def animate(self):
        animation = self.animations[self.animate_sequence]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
            if self.animate_sequence == self.action:
                self.animate_sequence = "move"
        self.image = animation[int(self.frame_index)]

        if self.vigilant > 0:
            tinted_image = self.image.copy()
            alpha = min(255, int((self.vigilant / 100) * 255))
            tinted_image.fill((255, max(255 - alpha, 128), max(255 - alpha, 128)), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = tinted_image

    def move(self, target: pygame.math.Vector2, speed: int, objects: list = None, tile_size=64):
        current = pygame.math.Vector2(self.hitbox.centerx, self.hitbox.centery)
        
        if not target: self.direction = pygame.math.Vector2()

        if target and objects:
            is_close_to_target = current.distance_to(target) < 5
            needs_new_path = target.distance_to(self.old_target_location) > tile_size / 4

            if (needs_new_path or (not self.path and not is_close_to_target)) and not self.is_path_requested:
                self.old_target_location = target.copy()
                obstacle_hitboxes = [obj.hitbox for obj in objects]
                task_data = {'start_pos': current, 'goal_pos': target, 'obstacles': obstacle_hitboxes, 'tile_size': tile_size}
                self.compute_manager.request(self.full_name, 'pathfinding', task_data)
                self.is_path_requested = True
                self.path = None
                self.direction = pygame.math.Vector2()

        if self.path:
            next_waypoint = self.path[0]
            if current.distance_to(next_waypoint) < 5:
                self.path.pop(0)
            
            if self.path:
                self.direction = (pygame.math.Vector2(self.path[0]) - current).normalize()
            else:
                self.direction = pygame.math.Vector2()

        if self.direction.magnitude() > 0:
            move_delta = self.direction * speed
            self.hitbox.x += move_delta.x; self.collision("horizontal")
            self.hitbox.y += move_delta.y; self.collision("vertical")
            self.rect.center = self.hitbox.center
    
    def collision(self, direction):
        if direction == "horizontal":
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.x > 0: self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0: self.hitbox.left = sprite.hitbox.right
        if direction == "vertical":
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.y > 0: self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0: self.hitbox.top = sprite.hitbox.bottom

    def attack(self, target: "Entity"):
        self.attack_sound.play()
        if target.sprite_type in ["player", "enemy"]:
            target.get_damage(attacker=self)
            
    def heal(self, target: "Entity"):
        if self.energy > 0 and target.health < target.max_health and self.energy > self.attack_damage:
            self.heal_sound.play()
            self.energy -= self.attack_damage
            if self.energy <= 0:
                self.outside_event = f"out of energy to heal {target.full_name}"
                self.energy = 0
            target.get_heal(healer=self)

    def save_observation(self, player: "Player", entities: list["Enemy"], objects: list["Tile"]):
        self.observation_count += 1
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        memory_entry = {
            "timestamp": timestamp, "self": self.observation_template(self),
            "nearby_entities": [], "nearby_objects": []
        }
        for other_entity in entities:
            if other_entity != self:
                memory_entry["nearby_entities"].append(self.observation_template(other_entity))
        distance, _ = get_distance_direction(self, player)
        if distance <= self.notice_radius:
            memory_entry["nearby_entities"].append(self.observation_template(player))
        if objects:
            obj = min(objects, key=lambda o: get_distance_direction(self, o)[0], default=None)
            if obj:
                memory_entry["nearby_objects"].append({"object_name": obj.full_name, "location": {"x": obj.rect.centerx, "y": obj.rect.centery}})
        self.memory.write_memory(memory_entry, f"stream_{self.full_name}.json", threshold=MEMORY_SIZE)

    def observation_template(self, entity: "Entity"):
        health = f'{int(entity.health)}/{int(entity.stats["health"])}' if entity.sprite_type == "player" else f"{int(entity.health)}/{int(entity.max_health)}"
        energy = f'{int(entity.energy)}/{int(entity.stats["energy"])}' if entity.sprite_type == "player" else f"{int(entity.energy)}/{int(entity.max_energy)}"
        observation = {
            "entity_name": entity.full_name, "action": entity.action, "target_name": entity.target_name,
            "observations": {"intention": entity.internal_event, "event": self.outside_event, "observed": self.observed_event},
            "location": {"x": entity.rect.centerx, "y": entity.rect.centery},
            "stats": {"health": health, "energy": energy, "experience": int(entity.exp)}
        }
        if entity.target_location:
            observation["previous_moving_to"] = {"x": int(entity.target_location.x), "y": int(entity.target_location.y)}
        if entity.target_name:
            observation["previous_target_name"] = entity.target_name
        return observation

    def mine(self, target: "Tile"):
        self.animation_player.create_particles("sparkle", target.hitbox.center, [self.visible_sprite])
        if self.timber >= self.max_timber:
            self.outside_event = f"can't mine {target.full_name} because of full inventory"
            self.timber = self.max_timber
        else:
            self.timber += 1

    def upgrade(self):
        if self.exp >= self.upgrade_cost:
            self.lvl += 1
            self.upgrade_cost += int(self.upgrade_cost * (1 + self.upgrade_percentage))
            self.max_health = int(self.max_health * (1 + self.upgrade_percentage))
            self.max_energy = int(self.max_energy * (1 + self.upgrade_percentage))
            self.speed = int(self.speed * (1 + self.upgrade_percentage))
            self.attack_damage = int(self.attack_damage * (1 + self.upgrade_percentage))

    def flickering(self):
        self.image.set_alpha(wave_value() if not self.vulnerable else 255)

    def set_decision(self, decision):
        if decision:
            self.target_name = decision.get("target_name")
            self.vigilant = int(decision.get("vigilant", 0))
            
            proposed_action = decision.get("action", "idle")

            if proposed_action in self.animations:
                self.action = proposed_action
            else:
                print(f"Warning: Invalid action '{proposed_action}' for {self.full_name}. Defaulting to 'idle'.")
                self.action = "idle"
                
            self.reason = decision.get("reason", "")
            if self.target_name == "None":
                self.target_name = None

    def interaction(self, player: "Player", entities: list["Entity"], objects: list["Tile"]):
        if not self.target_name:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_internal_move_update >= self.internal_move_update_interval:
                self.wander()
                self.last_internal_move_update = current_time
                self.internal_event = "wandering"
        else:
            target = self.target_select(player, entities, objects)
            if target:
                self.internal_event = f"{self.action} {target.full_name}"
                distance, _ = get_distance_direction(self, target)
                if distance > self.act_radius:
                    current_time = pygame.time.get_ticks()
                    if current_time - self.last_internal_move_update >= self.internal_move_update_interval:
                        self.internal_move_update(target)
                        self.last_internal_move_update = current_time
                elif self.can_act:
                    if self.action == "attack": self.attack(target)
                    elif self.action == "heal": self.heal(target)
                    elif self.action == "mine": self.mine(target)
                    elif self.action == "runaway": self.runaway(target)
                    self.can_act = False
                    self.animate_sequence = self.action
                    self.act_time = pygame.time.get_ticks()
                    for entity in entities:
                        if entity != self and entity != target:
                            entity.observed_event = f"{self.full_name} {self.action} {target.full_name}"
    
    def target_select(self, player, entities, objects):
        if self.target_name == "player": return player
        for entity in entities:
            if entity.full_name == self.target_name: return entity
        for obj in objects:
            if obj.full_name == self.target_name: return obj
        return None

    def wander(self):
        self.target_location = pygame.math.Vector2(
            random.randint(int(self.starting_point[0] - 100), int(self.starting_point[0] + 100)),
            random.randint(int(self.starting_point[1] - 100), int(self.starting_point[1] + 100))
        )
        self.action = "move"

    def runaway(self, target):
        _, direction = get_distance_direction(self, target)
        if direction.magnitude() != 0:
            self.direction = -direction.normalize()
        self.target_location = pygame.math.Vector2()

    def internal_move_update(self, target: "Entity"):
        if self.vulnerable:
            if self.action == "runaway": self.runaway(target)
            elif self.action in ["attack", "mine", "heal"]:
                self.target_location = pygame.math.Vector2(target.hitbox.center)

    def update(self):
        self.animate()
        self.cooldown()
        self.flickering()
        self.upgrade()

    def check_death(self):
        if self.health <= 0:
            self.kill()
            self.status_bars.kill()
            self.text_bubble.kill()

    def control_update(self, player, entities, objects):
        current_time = pygame.time.get_ticks()
        
        if not self.first_observation:
            self.save_observation(player, entities, objects)
            self.first_observation = True
            
        if current_time - self.last_chat_time >= self.chat_interval:
            self.decide()
            self.last_chat_time = current_time

        if current_time - self.last_summary_time >= self.summary_interval:
            self.summary()
            self.last_summary_time = current_time

        if (self.observed_event != self.old_observed_event or 
            self.outside_event != self.old_outside_event):
            self.old_observed_event = self.observed_event
            self.old_outside_event = self.outside_event
            self.save_observation(player, entities, objects)