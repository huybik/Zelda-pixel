import pygame
from entity import Entity
from settings import (
    monster_data,
    CHAT_INTERVAL,
    SUMMARY_INTERVAL,
    MEMORY_SIZE,
)
import time
from tooltips import TextBubble, StatusBars
import json
from persona import Persona
from memstream import MemoryStream
from support import get_distance_direction, wave_value
import random
from typing import TYPE_CHECKING
from queue import PriorityQueue

if TYPE_CHECKING:
    from entity import Entity
    from tile import Tile
    from player import Player
    from ai_manager import AIManager


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
    ):

        # general setup
        super().__init__(groups)
        self.sprite_type = "enemy"
        self.groups = groups
        self.memory = MemoryStream()
        self.persona = Persona()
        self.ai_manager = ai_manager

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
        self.visible_sprite = visible_sprite
        self.target_location = pygame.math.Vector2()
        self.current_speed = 0
        self.old_target_location = pygame.math.Vector2()
        self.tile_size = 64
        self.path = None

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
        self.vigilant = 0

        # API call timers
        self.last_chat_time = 0
        self.last_summary_time = 0
        self.last_internal_move_update = 0

        self.chat_interval = CHAT_INTERVAL
        self.summary_interval = SUMMARY_INTERVAL
        self.internal_move_update_interval = 500  # ticks

        self.reason = None

        # cooldowns
        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_duration = 1000

        self.act_time = 0
        self.act_cooldown = 1000
        self.can_act = True

        # sound (cached)
        from resources import load_sound
        self.attack_sound = load_sound(monster_info["attack_sound"])
        self.attack_sound.set_volume(0.6)
        self.heal_sound = load_sound("../audio/heal.wav")
        self.heal_sound.set_volume(0.6)

        # Add tooltips
        self.text_bubble = TextBubble(self.visible_sprite)
        self.status_bars = StatusBars(self.visible_sprite)

        # upgrade cost
        self.upgrade_cost = 100
        self.upgrade_percentage = 0.01  # this increase cost and stat

        # inventory
        self.timber = 0
        self.max_timber = 10

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
            tinted_image.fill(
                (255, max(255 - alpha, 128), max(255 - alpha, 128)),
                special_flags=pygame.BLEND_RGBA_MULT,
            )
            self.image = tinted_image

    def move(self, target: pygame.math.Vector2, speed: int, objects: list = None, tile_size=64):
        # A* pathfinding and movement logic remains the same...
        current = pygame.math.Vector2(self.hitbox.centerx, self.hitbox.centery)

        def to_grid(pos, tile_size):
            return (int(pos.x // tile_size), int(pos.y // tile_size))

        def to_world(grid, tile_size):
            return pygame.math.Vector2(
                grid[0] * tile_size + tile_size / 2,
                grid[1] * tile_size + tile_size / 2,
            )

        def get_occupied_grids(rect, tile_size):
            grids = set()
            start_x, start_y = int(rect.left // tile_size), int(rect.top // tile_size)
            end_x, end_y = int(rect.right // tile_size), int(rect.bottom // tile_size)
            for x in range(start_x, end_x + 1):
                for y in range(start_y, end_y + 1):
                    grids.add((x, y))
            return grids

        def find_nearest_walkable(grid, obstacle_grids):
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (grid[0] + dx, grid[1] + dy)
                if neighbor not in obstacle_grids:
                    return neighbor
            return None

        def astar_pathfinding(start, goal, obstacles, tile_size):
            start_grid, goal_grid = to_grid(start, tile_size), to_grid(goal, tile_size)
            obstacle_grids = set().union(*(get_occupied_grids(obj, tile_size) for obj in obstacles))
            if goal_grid in obstacle_grids:
                goal_grid = find_nearest_walkable(goal_grid, obstacle_grids)
                if not goal_grid: return []

            def heuristic(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
            
            open_set = PriorityQueue(); open_set.put((0, start_grid))
            came_from, g_score = {}, {start_grid: 0}
            f_score = {start_grid: heuristic(start_grid, goal_grid)}
            
            while not open_set.empty():
                _, current_grid = open_set.get()
                if current_grid == goal_grid:
                    path = []
                    while current_grid in came_from:
                        path.append(to_world(current_grid, tile_size))
                        current_grid = came_from[current_grid]
                    path.reverse(); return path
                
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbor = (current_grid[0] + dx, current_grid[1] + dy)
                    if neighbor in obstacle_grids: continue
                    tentative_g_score = g_score[current_grid] + 1
                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current_grid
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal_grid)
                        open_set.put((f_score[neighbor], neighbor))
            return []

        if target and objects:
            if to_grid(target, tile_size) != to_grid(self.old_target_location, tile_size) or not self.path:
                self.old_target_location = target
                self.path = astar_pathfinding(current, target, [obj.hitbox for obj in objects], tile_size)
            
            if self.path:
                next_waypoint = pygame.math.Vector2(self.path[0])
                desired_direction = next_waypoint - current
                if desired_direction.magnitude() < 3:
                    self.path.pop(0)
                    if not self.path: self.direction = pygame.math.Vector2(0, 0); return
                else:
                    self.direction = desired_direction.normalize()

        if self.direction.magnitude() > 0:
            move_delta = self.direction * speed
            self.hitbox.x += move_delta.x; self.collision("horizontal")
            self.hitbox.y += move_delta.y; self.collision("vertical")
            self.rect.center = self.hitbox.center
    
    # ... other methods like collision, attack, heal, save_observation, etc. remain largely the same ...
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
            "observations": {"intention": entity.internal_event, "event": entity.outside_event, "observed": entity.observed_event},
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
            self.action = decision.get("action", "idle")
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

    def decide(self):
        prompt = self.persona.format_decision_prompt(self)
        if prompt:
            self.ai_manager.request_decision(self.full_name, prompt)

    def summary(self):
        prompt = self.persona.format_summary_prompt(self)
        if prompt:
            self.ai_manager.request_summary(self.full_name, prompt)

    def process_ai_responses(self):
        """Poll for new decisions or summaries from the AI manager and apply them."""
        # Process decision
        new_decision_json = self.ai_manager.get_response(self.full_name, 'decision')
        if new_decision_json:
            try:
                parsed_decision = self.persona.parse_decision_response(new_decision_json)
                self.set_decision(parsed_decision)
            except Exception as e:
                print(f"Failed to parse decision for {self.full_name}: {new_decision_json} | Error: {e}")
        
        # Process summary
        new_summary_text = self.ai_manager.get_response(self.full_name, 'summary')
        if new_summary_text and new_summary_text != "ERROR":
            self.persona.save_summary(new_summary_text, f"summary_{self.full_name}.json")

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

    def enemy_update(self, player: "Player", entities: list["Entity"], objects: list["Tile"]):
        distance, _ = get_distance_direction(self, player)
        
        # Poll for completed AI tasks first
        self.process_ai_responses()

        nearby_entities = [e for e in entities if get_distance_direction(self, e)[0] <= self.notice_radius and e != self]
        nearby_objects = [o for o in objects if get_distance_direction(self, o)[0] <= self.notice_radius]

        if distance <= self.notice_radius:
            self.interaction(player, nearby_entities, nearby_objects)
        
        self.move(self.target_location, self.speed, objects)
        self.control_update(player, nearby_entities, nearby_objects)
        self.check_death()

        # update tooltips
        self.status_bars.update_rect(self)
        if self.reason:
            self.text_bubble.update_text(f"{self.action} {self.target_name}: {self.reason}", self.rect)
