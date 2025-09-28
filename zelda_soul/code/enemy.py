import json
import pygame
from .entity import Entity
from .settings import (
    monster_data,
    CHAT_INTERVAL,
    SHORT_TERM_MEMORY_LIMIT,
    MEMORY_FLUSH_THRESHOLD,
    SUMMARY_TRIGGER_COUNT,
    AUDIO_DIR,
    GRAPHICS_DIR,
)
import time
from .tooltips import TextBubble, StatusBars
from .persona import Persona
from .memstream import MemoryStream
from .support import get_distance_direction, wave_value
import random
from typing import TYPE_CHECKING
from collections import deque
from .resources import load_sound
from .behavior_tree import (
    BehaviorTree,
    Selector,
    Sequence,
    ConditionNode,
    ActionNode,
    NodeStatus,
)
from .event_bus import event_bus, GameEvent

if TYPE_CHECKING:
    from .entity import Entity
    from .tile import Tile
    from .player import Player
    from .ai_manager import AIManager
    from .compute_manager import ComputeManager

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
        self.short_term_memory: deque = deque(maxlen=SHORT_TERM_MEMORY_LIMIT)
        self._pending_memories: list[dict] = []
        self.memory_flush_threshold = MEMORY_FLUSH_THRESHOLD
        self.observations_since_summary = 0
        self.summary_trigger_count = SUMMARY_TRIGGER_COUNT

        # Graphics and basic setup
        self.animations = {
            "idle": [], "move": [], "attack": [], "heal": [], "mine": [], "runaway": []
        }
        self.import_graphics(GRAPHICS_DIR / "monsters", name, self.animations)

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

        # AI goals & behavior tree
        self.current_goal = {"goal": "idle", "target": None, "reason": "", "priority": 0}
        self.goal_priority = 10
        self.goal_updated_at = pygame.time.get_ticks()
        self.blackboard = {
            "enemy": self,
            "current_goal": self.current_goal,
            "player": None,
            "entities": [],
            "objects": [],
            "time": self.goal_updated_at,
        }
        self.behavior_tree = self._build_behavior_tree()
        self.action_state = ActionStateMachine(self)
        self.event_bus = event_bus
        self.event_tokens: list = []
        self.last_reactive_time = 0
        self.reactive_cooldown_ms = 1000
        self.player_in_radius = False
        self._register_event_listeners()

        # Timers and cooldowns
        self.last_chat_time = 0
        self.last_internal_move_update = 0
        self.chat_interval = CHAT_INTERVAL
        self.internal_move_update_interval = 500
        self.vulnerable = True
        self.vulnerable_time = 0
        self.vulnerable_duration = 1000
        self.act_time = 0
        self.act_cooldown = 1000
        self.can_act = True
        
        self.attack_sound = load_sound(monster_info["attack_sound"])
        self.attack_sound.set_volume(0.6)
        self.heal_sound = load_sound(AUDIO_DIR / "heal.wav")
        self.heal_sound.set_volume(0.6)

        # Tooltips and other components
        self.text_bubble = TextBubble(self.visible_sprite)
        self.status_bars = StatusBars(self.visible_sprite)
        self.reason = ""

    def _build_behavior_tree(self) -> BehaviorTree:
        """Constructs the behavior tree that maps high-level goals to actions."""

        flee_goals = {"flee", "flee_threat", "runaway"}
        heal_goals = {"heal_ally", "assist_ally", "support_ally"}
        defend_goals = {"defend_ally", "guard_ally", "protect_ally"}
        attack_goals = {"attack_enemy", "attack_target", "eliminate_enemy"}
        gather_goals = {"gather_resource", "mine_resource", "collect_resource"}
        patrol_goals = {"patrol", "patrol_area", "wander"}

        return BehaviorTree(
            Selector(
                [
                    Sequence([
                        ConditionNode(lambda bb, names=flee_goals: self._goal_matches(bb, names)),
                        ActionNode(self._execute_flee_goal),
                    ]),
                    Sequence([
                        ConditionNode(lambda bb, names=heal_goals: self._goal_matches(bb, names)),
                        ActionNode(self._execute_heal_goal),
                    ]),
                    Sequence([
                        ConditionNode(lambda bb, names=defend_goals: self._goal_matches(bb, names)),
                        ActionNode(self._execute_defend_goal),
                    ]),
                    Sequence([
                        ConditionNode(lambda bb, names=attack_goals: self._goal_matches(bb, names)),
                        ActionNode(self._execute_attack_goal),
                    ]),
                    Sequence([
                        ConditionNode(lambda bb, names=gather_goals: self._goal_matches(bb, names)),
                        ActionNode(self._execute_gather_goal),
                    ]),
                    Sequence([
                        ConditionNode(lambda bb, names=patrol_goals: self._goal_matches(bb, names)),
                        ActionNode(self._execute_patrol_goal),
                    ]),
                    ActionNode(self._execute_idle_goal),
                ]
            )
        )

    def _goal_matches(self, blackboard: dict, candidate_names: set[str]) -> bool:
        goal = (blackboard.get("current_goal") or {}).get("goal") or "idle"
        return goal.lower() in candidate_names

    def decide(self, priority: int = 5, metadata: dict | None = None, bypass_interval: bool = False):
        """Requests a new high-level goal from the AI manager."""
        prompt = self.persona.prompt_generator.format_decision_prompt(self, metadata=metadata)
        if not prompt:
            if bypass_interval:
                self.last_chat_time = pygame.time.get_ticks()
            return
        self.ai_manager.request(self.full_name, 'decision', prompt, priority=priority, metadata=metadata)
        if bypass_interval:
            self.last_chat_time = pygame.time.get_ticks()

    def summary(self):
        """Requests a summary from the AI manager."""
        self._flush_pending_memories()
        prompt = self.persona.prompt_generator.format_summary_prompt(self)
        self.ai_manager.request(self.full_name, 'summary', prompt, priority=10)

    def process_ai_responses(self):
        """Polls for and applies AI responses."""
        parsed_goal = self.ai_manager.get_response(self.full_name, 'decision')
        if parsed_goal:
            self.apply_goal(parsed_goal)

        new_summary_text = self.ai_manager.get_response(self.full_name, 'summary')
        if new_summary_text and new_summary_text != "ERROR":
            self.persona.save_summary(self.full_name, new_summary_text)

    def process_compute_responses(self):
        """Polls for and applies compute worker responses."""
        new_path = self.compute_manager.get_response(self.full_name, 'pathfinding')
        if new_path is not None:
            self.path = new_path
            self.is_path_requested = False

    def enemy_update(self, player: "Player", entities: list["Entity"], objects: list["Tile"]):
        """Main update loop for the enemy."""
        self.process_ai_responses()
        self.process_compute_responses()
        distance, _ = get_distance_direction(self, player)
        is_player_nearby = distance <= self.notice_radius
        if is_player_nearby and not self.player_in_radius:
            self.event_bus.emit(GameEvent.PLAYER_ENTERS_RADIUS, {"enemy": self, "player": player})
        self.player_in_radius = is_player_nearby
        current_time = pygame.time.get_ticks()
        nearby_entities = [
            e for e in entities if e != self and get_distance_direction(self, e)[0] <= self.notice_radius
        ]
        nearby_objects = [
            o for o in objects if get_distance_direction(self, o)[0] <= self.notice_radius
        ]

        self.blackboard.update(
            {
                "player": player,
                "entities": nearby_entities,
                "objects": nearby_objects,
                "time": current_time,
            }
        )

        tree_status = self.behavior_tree.tick(self.blackboard)
        if tree_status == NodeStatus.FAILURE:
            self.action_state.ensure_action("idle", None)
        elif tree_status == NodeStatus.SUCCESS:
            self.current_goal.update({"goal": "idle", "target": None})
            self.goal_priority = 10
            self.action_state.ensure_action("idle", None)

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
        self.short_term_memory.append(memory_entry)
        self._pending_memories.append(memory_entry)
        self.observations_since_summary += 1
        if len(self._pending_memories) >= self.memory_flush_threshold:
            self._flush_pending_memories()

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
        self.event_bus.emit(GameEvent.RESOURCE_DEPLETED, {"entity": self, "resource": target})

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

    def apply_goal(self, goal_payload: dict | None):
        if not goal_payload:
            return

        goal_name = (goal_payload.get("goal") or "idle").lower()
        target_name = goal_payload.get("target") or goal_payload.get("target_name")
        reason = goal_payload.get("reason", "")
        priority = int(goal_payload.get("priority", 0))
        vigilant = int(goal_payload.get("vigilant", self.vigilant))

        if target_name in {None, "None", ""}:
            target_name = None

        metadata = goal_payload.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        location = goal_payload.get("target_location") or goal_payload.get("location")

        if self.current_goal.get("goal") not in {None, "idle"} and priority > self.goal_priority:
            return

        self.goal_priority = priority
        self.goal_updated_at = pygame.time.get_ticks()

        self.current_goal.update(
            {
                "goal": goal_name,
                "target": target_name,
                "reason": reason,
                "priority": priority,
                "metadata": metadata,
                "updated_at": self.goal_updated_at,
            }
        )

        if location and isinstance(location, dict):
            self.current_goal["target_location"] = location
        else:
            self.current_goal.pop("target_location", None)

        self.reason = reason
        self.vigilant = vigilant
        self.target_name = target_name
        self.blackboard["current_goal"] = self.current_goal
        self.action_state.reset()

    def _register_event_listeners(self):
        if self.event_tokens:
            return
        self.event_tokens = [
            self.event_bus.subscribe(GameEvent.ENTITY_TAKES_DAMAGE, self._on_entity_takes_damage),
            self.event_bus.subscribe(GameEvent.PLAYER_ENTERS_RADIUS, self._on_player_enters_radius),
            self.event_bus.subscribe(GameEvent.RESOURCE_DEPLETED, self._on_resource_depleted),
        ]

    def _unsubscribe_event_listeners(self):
        for token in self.event_tokens:
            self.event_bus.unsubscribe(token)
        self.event_tokens.clear()

    def request_reactive_goal(self, trigger: str, priority: int = 1, metadata: dict | None = None):
        now = pygame.time.get_ticks()
        if now - self.last_reactive_time < self.reactive_cooldown_ms:
            return
        self.last_reactive_time = now
        context = {"trigger": trigger, **(metadata or {})}
        self.decide(priority=priority, metadata=context, bypass_interval=True)

    def _on_entity_takes_damage(self, payload: dict):
        target = payload.get("target")
        attacker = payload.get("attacker")

        if target is self:
            self.request_reactive_goal(
                "under_attack",
                priority=0,
                metadata={"attacker": getattr(attacker, "full_name", None)},
            )
            return

        if getattr(target, "sprite_type", None) == "player" and any(
            key in self.characteristic for key in ("friend", "help")
        ):
            self.request_reactive_goal(
                "defend_player",
                priority=1,
                metadata={"attacker": getattr(attacker, "full_name", None)},
            )

    def _on_player_enters_radius(self, payload: dict):
        if payload.get("enemy") is self:
            self.request_reactive_goal("player_nearby", priority=1)

    def _on_resource_depleted(self, payload: dict):
        resource = payload.get("resource")
        if resource and self.current_goal.get("target") == getattr(resource, "full_name", None):
            self.request_reactive_goal("resource_depleted", priority=1)

    def kill(self):
        self._flush_pending_memories()
        self._unsubscribe_event_listeners()
        super().kill()

    def _resolve_target(self, identifier, blackboard):
        if not identifier or identifier in {"", "None"}:
            return None

        if isinstance(identifier, dict):
            identifier = identifier.get("name") or identifier.get("id")

        identifier = str(identifier)

        if identifier.lower() in {"player", "the player"}:
            return blackboard.get("player")

        for entity in blackboard.get("entities", []):
            if getattr(entity, "full_name", None) == identifier:
                return entity

        for obj in blackboard.get("objects", []):
            if getattr(obj, "full_name", None) == identifier:
                return obj

        return None

    def _select_default_target(self, blackboard):
        player = blackboard.get("player")
        if player and get_distance_direction(self, player)[0] <= self.notice_radius:
            return player
        for entity in blackboard.get("entities", []):
            return entity
        for obj in blackboard.get("objects", []):
            return obj
        return None

    def _goal_location_vector(self, goal_data: dict):
        raw_location = goal_data.get("target_location") or goal_data.get("location")
        if isinstance(raw_location, dict) and {"x", "y"} <= raw_location.keys():
            return pygame.math.Vector2(float(raw_location["x"]), float(raw_location["y"]))
        return None

    def _execute_attack_goal(self, blackboard: dict) -> NodeStatus:
        goal = blackboard.get("current_goal", {})
        target = self._resolve_target(goal.get("target"), blackboard) or self._select_default_target(blackboard)
        if not target:
            return NodeStatus.FAILURE
        return self.action_state.ensure_action("attack", target, goal.get("metadata"))

    def _execute_heal_goal(self, blackboard: dict) -> NodeStatus:
        goal = blackboard.get("current_goal", {})
        target = self._resolve_target(goal.get("target"), blackboard)
        if not target:
            for candidate in [blackboard.get("player")] + blackboard.get("entities", []):
                if candidate and getattr(candidate, "health", 0) < getattr(candidate, "max_health", 0):
                    target = candidate
                    break
        if not target:
            return NodeStatus.FAILURE
        return self.action_state.ensure_action("heal", target, goal.get("metadata"))

    def _execute_defend_goal(self, blackboard: dict) -> NodeStatus:
        goal = blackboard.get("current_goal", {})
        target = self._resolve_target(goal.get("target"), blackboard)
        if not target:
            return NodeStatus.FAILURE
        return self.action_state.ensure_action("guard", target, goal.get("metadata"))

    def _execute_gather_goal(self, blackboard: dict) -> NodeStatus:
        goal = blackboard.get("current_goal", {})
        target = self._resolve_target(goal.get("target"), blackboard)
        if not target:
            return NodeStatus.FAILURE
        metadata = goal.get("metadata") or {}
        location = self._goal_location_vector(goal)
        if location is not None:
            metadata = {**metadata, "location": location}
        return self.action_state.ensure_action("mine", target, metadata)

    def _execute_flee_goal(self, blackboard: dict) -> NodeStatus:
        goal = blackboard.get("current_goal", {})
        threat = self._resolve_target(goal.get("target"), blackboard) or self._select_default_target(blackboard)
        if not threat:
            return NodeStatus.SUCCESS
        return self.action_state.ensure_action("runaway", threat, goal.get("metadata"))

    def _execute_patrol_goal(self, blackboard: dict) -> NodeStatus:
        goal = blackboard.get("current_goal", {})
        metadata = goal.get("metadata") or {}
        location = self._goal_location_vector(goal)
        if location is not None:
            metadata = {**metadata, "location": location}
        return self.action_state.ensure_action("patrol", None, metadata)

    def _execute_idle_goal(self, blackboard: dict) -> NodeStatus:
        return self.action_state.ensure_action("idle", None)

    def _flush_pending_memories(self) -> None:
        if not self._pending_memories:
            return
        self.memory.write_observations(self.full_name, self._pending_memories)
        self._pending_memories.clear()

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

        if self.observations_since_summary >= self.summary_trigger_count:
            self.summary()
            self.observations_since_summary = 0

        if (self.observed_event != self.old_observed_event or 
            self.outside_event != self.old_outside_event):
            self.old_observed_event = self.observed_event
            self.old_outside_event = self.outside_event
            self.save_observation(player, entities, objects)


class ActionStateMachine:
    """State machine responsible for orchestrating multi-step actions."""

    SAFE_FLEE_DISTANCE_MULTIPLIER = 1.5

    def __init__(self, enemy: "Enemy"):
        self.enemy = enemy
        self.reset()

    def reset(self):
        self.current_action = "idle"
        self.state = "IDLE"
        self.target = None
        self.target_id = None
        self.metadata: dict = {}
        self.wait_until = 0
        self.patrol_point: pygame.math.Vector2 | None = None
        self.enemy.action = "idle"
        self.enemy.target_location = pygame.math.Vector2()
        self.enemy.direction = pygame.math.Vector2()

    def is_idle(self) -> bool:
        return self.current_action == "idle"

    def ensure_action(self, action_name: str, target, metadata: dict | None = None) -> NodeStatus:
        metadata = metadata or {}
        target_id = self._id_for(target)

        if action_name != self.current_action or target_id != self.target_id:
            self._start_action(action_name, target, metadata)
        else:
            self.metadata.update(metadata)
            if target is not None:
                self.target = target

        handler = getattr(self, f"_tick_{action_name}", None)
        if not handler:
            return NodeStatus.FAILURE
        return handler(target)

    def _start_action(self, action_name: str, target, metadata: dict):
        self.current_action = action_name
        self.state = "IDLE"
        self.target = target
        self.target_id = self._id_for(target)
        self.metadata = metadata.copy()
        self.wait_until = 0
        self.patrol_point = None
        self.enemy.target_name = self.target_id

        if action_name == "idle":
            self.enemy.action = "idle"
            self.enemy.target_location = pygame.math.Vector2()
            self.enemy.direction = pygame.math.Vector2()
        elif action_name == "patrol":
            self.enemy.action = "move"
            self._assign_patrol_point()
        elif action_name in {"attack", "heal"}:
            self.enemy.action = "move"
            self.state = "MOVING_TO_TARGET"
        elif action_name == "mine":
            self.enemy.action = "move"
            self.state = "MOVING_TO_RESOURCE"
        elif action_name == "guard":
            self.enemy.action = "move"
            self.state = "MOVING_TO_GUARD"
        elif action_name == "runaway":
            self.enemy.action = "runaway"
            self.state = "EVADING"

    def _id_for(self, target) -> str | None:
        if target is None:
            return None
        if getattr(target, "sprite_type", None) == "player":
            return "player"
        return getattr(target, "full_name", None)

    def _tick_idle(self, _target) -> NodeStatus:
        self.enemy.action = "idle"
        self.enemy.direction = pygame.math.Vector2()
        self.enemy.target_location = pygame.math.Vector2()
        return NodeStatus.RUNNING

    def _assign_patrol_point(self):
        base_location = self.metadata.get("location")
        if isinstance(base_location, pygame.math.Vector2):
            center = base_location
        elif isinstance(base_location, (tuple, list)) and len(base_location) == 2:
            center = pygame.math.Vector2(base_location)
        else:
            center = pygame.math.Vector2(self.enemy.starting_point)
        radius = float(self.metadata.get("radius", 120))
        random_offset = pygame.math.Vector2(random.uniform(-radius, radius), random.uniform(-radius, radius))
        self.patrol_point = center + random_offset
        self.enemy.target_location = self.patrol_point
        self.enemy.action = "move"
        self.state = "MOVING_TO_POINT"

    def _tick_patrol(self, _target) -> NodeStatus:
        if self.state == "WAITING":
            if pygame.time.get_ticks() >= self.wait_until:
                self._assign_patrol_point()
            return NodeStatus.RUNNING

        if self.patrol_point is None:
            self._assign_patrol_point()

        current_pos = pygame.math.Vector2(self.enemy.hitbox.center)
        if current_pos.distance_to(self.patrol_point) <= 10:
            self.state = "WAITING"
            self.wait_until = pygame.time.get_ticks() + int(self.metadata.get("wait_ms", 1000))
            self.enemy.direction = pygame.math.Vector2()
            self.enemy.action = "idle"
            return NodeStatus.RUNNING

        self.enemy.target_location = self.patrol_point
        self.enemy.action = "move"
        return NodeStatus.RUNNING

    def _tick_attack(self, target) -> NodeStatus:
        target = target or self.target
        if not (target and target.alive()):
            return NodeStatus.SUCCESS

        distance, _ = get_distance_direction(self.enemy, target)
        if distance > self.enemy.notice_radius * 1.5:
            return NodeStatus.FAILURE

        if self.state == "MOVING_TO_TARGET":
            self.enemy.action = "move"
            self.enemy.target_location = pygame.math.Vector2(target.hitbox.center)
            if distance <= self.enemy.act_radius:
                self.state = "EXECUTING"
            return NodeStatus.RUNNING

        if self.state == "EXECUTING":
            if not self.enemy.can_act:
                self.state = "COOLDOWN"
                return NodeStatus.RUNNING
            self.enemy.action = "attack"
            self.enemy.animate_sequence = "attack"
            self.enemy.attack(target)
            self.enemy.can_act = False
            self.enemy.act_time = pygame.time.get_ticks()
            self.state = "COOLDOWN"
            return NodeStatus.RUNNING

        if self.state == "COOLDOWN":
            if self.enemy.can_act:
                self.state = "MOVING_TO_TARGET"
                return NodeStatus.RUNNING
            return NodeStatus.RUNNING

        self.state = "MOVING_TO_TARGET"
        return NodeStatus.RUNNING

    def _tick_heal(self, target) -> NodeStatus:
        target = target or self.target
        if not (target and target.alive()):
            return NodeStatus.FAILURE

        if getattr(target, "health", 0) >= getattr(target, "max_health", 0):
            return NodeStatus.SUCCESS

        distance, _ = get_distance_direction(self.enemy, target)

        if self.state == "MOVING_TO_TARGET":
            self.enemy.action = "move"
            self.enemy.target_location = pygame.math.Vector2(target.hitbox.center)
            if distance <= self.enemy.act_radius:
                self.state = "EXECUTING"
            return NodeStatus.RUNNING

        if self.state == "EXECUTING":
            if not self.enemy.can_act or self.enemy.energy <= 0:
                self.state = "COOLDOWN"
                return NodeStatus.RUNNING
            self.enemy.action = "heal"
            self.enemy.animate_sequence = "heal"
            self.enemy.heal(target)
            self.enemy.can_act = False
            self.enemy.act_time = pygame.time.get_ticks()
            self.state = "COOLDOWN"
            return NodeStatus.RUNNING

        if self.state == "COOLDOWN":
            if self.enemy.can_act:
                self.state = "MOVING_TO_TARGET"
                return NodeStatus.RUNNING
            return NodeStatus.RUNNING

        self.state = "MOVING_TO_TARGET"
        return NodeStatus.RUNNING

    def _tick_mine(self, target) -> NodeStatus:
        target = target or self.target
        if not (target and target.alive()):
            return NodeStatus.SUCCESS

        distance, _ = get_distance_direction(self.enemy, target)

        if self.enemy.timber >= self.enemy.max_timber:
            return NodeStatus.SUCCESS

        if self.state == "MOVING_TO_RESOURCE":
            self.enemy.action = "move"
            target_location = self.metadata.get("location")
            if isinstance(target_location, pygame.math.Vector2):
                self.enemy.target_location = target_location
            else:
                self.enemy.target_location = pygame.math.Vector2(target.hitbox.center)
            if distance <= self.enemy.act_radius:
                self.state = "GATHERING"
            return NodeStatus.RUNNING

        if self.state == "GATHERING":
            if not self.enemy.can_act:
                self.state = "COOLDOWN"
                return NodeStatus.RUNNING
            self.enemy.action = "mine"
            self.enemy.animate_sequence = "mine"
            self.enemy.mine(target)
            self.enemy.can_act = False
            self.enemy.act_time = pygame.time.get_ticks()
            self.state = "COOLDOWN"
            return NodeStatus.RUNNING

        if self.state == "COOLDOWN":
            if self.enemy.can_act:
                self.state = "MOVING_TO_RESOURCE"
                return NodeStatus.RUNNING
            return NodeStatus.RUNNING

        self.state = "MOVING_TO_RESOURCE"
        return NodeStatus.RUNNING

    def _tick_guard(self, target) -> NodeStatus:
        target = target or self.target
        if not (target and target.alive()):
            return NodeStatus.FAILURE

        guard_radius = float(self.metadata.get("radius", self.enemy.act_radius * 1.5))
        current_distance, _ = get_distance_direction(self.enemy, target)

        if current_distance > guard_radius:
            self.enemy.action = "move"
            self.enemy.target_location = pygame.math.Vector2(target.hitbox.center)
        else:
            self.enemy.action = "idle"
            self.enemy.direction = pygame.math.Vector2()

        return NodeStatus.RUNNING

    def _tick_runaway(self, threat) -> NodeStatus:
        threat = threat or self.target
        if not (threat and threat.alive()):
            return NodeStatus.SUCCESS

        distance, direction = get_distance_direction(self.enemy, threat)
        safe_distance = self.metadata.get("safe_distance") or (self.enemy.notice_radius * self.SAFE_FLEE_DISTANCE_MULTIPLIER)

        if distance >= safe_distance:
            self.enemy.action = "idle"
            self.enemy.direction = pygame.math.Vector2()
            return NodeStatus.SUCCESS

        if direction.magnitude() == 0:
            return NodeStatus.RUNNING

        self.enemy.action = "runaway"
        self.enemy.runaway(threat)
        return NodeStatus.RUNNING
