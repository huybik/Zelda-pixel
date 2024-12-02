from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any, TypeAlias
import numpy as np
import random
from enum import Enum

from environment import Environment, EnvironmentConfig
from creature import Creature
from edible import Edible
# Type aliases
State: TypeAlias = Dict[str, Any]
Action: TypeAlias = Dict[str, Any]
Reward: TypeAlias = float

class ActionType(Enum):
    MOVE = "move"
    ATTACK = "attack"
    HEAL = "heal"
    HARVEST = "harvest"
    CHILL = "chill"
    REPRODUCE = "reproduce"

@dataclass
class SimulationConfig:
    # Environment settings
    env_size: int = 10
    n_bits: int = 8
    genome_points: int = 4
    init_stat_point: int = 100
    
    # Population settings
    n_creatures: int = 10
    n_edibles: int = 10
    edible_amount: int = 100
    
    # Simulation settings
    max_steps: int = 1000
    seed: Optional[int] = None

class ZeldaSoulEnv:
    """Reinforcement Learning environment for Zelda Soul simulation."""
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        if self.config.seed is not None:
            np.random.seed(self.config.seed)
            random.seed(self.config.seed)
        
        self._init_environment()
        self.step_count = 0
        
    def _init_environment(self) -> None:
        """Initialize the environment with creatures and edibles."""
        env_config = EnvironmentConfig(
            size=self.config.env_size,
            n_bits=self.config.n_bits,
            genome_points=self.config.genome_points,
            init_stat_point=self.config.init_stat_point
        )
        self.env = Environment(env_config)
        
        # Add creatures and edibles
        for _ in range(self.config.n_creatures):
            self.env._add_creature()
        for _ in range(self.config.n_edibles):
            self.env._add_edible(amount=self.config.edible_amount)
    
    def reset(self) -> State:
        """Reset the environment to initial state."""
        self._init_environment()
        self.step_count = 0
        return self._get_state()
    
    def step(self, action: Action) -> Tuple[State, Reward, bool, Dict[str, Any]]:
        """Execute one time step within the environment."""
        self.step_count += 1
        
        # Execute action
        reward = self._execute_action(action)
        
        # Update environment
        self.env.step()
        
        # Get new state
        state = self._get_state()
        
        # Check if episode is done
        done = self._is_done()
        
        # Additional info
        info = {
            "step_count": self.step_count,
            "n_creatures": len([e for e in self.env.entities.values() 
                              if isinstance(e, Creature)]),
            "n_edibles": len([e for e in self.env.entities.values() 
                            if isinstance(e, Edible)])
        }
        
        return state, reward, done, info
    
    def _execute_action(self, action: Action) -> Reward:
        """Execute the given action and return reward."""
        action_type = ActionType(action["type"])
        creature_id = action["creature_id"]
        creature = self.env.entities.get(creature_id)
        
        if not creature or not isinstance(creature, Creature):
            return -1.0  # Invalid creature
        
        reward = 0.0
        
        if action_type == ActionType.MOVE:
            target_loc = action["target_location"]
            success = creature.move(target_loc, self.env)
            reward = 0.1 if success else -0.1
            
        elif action_type == ActionType.ATTACK:
            target_id = action["target_id"]
            target = self.env.entities.get(target_id)
            if target and isinstance(target, Creature):
                old_hp = target.stats.hp
                success = creature.attack(target)
                damage_dealt = old_hp - target.stats.hp if success else 0
                reward = damage_dealt * 0.01
            else:
                reward = -0.1
                
        elif action_type == ActionType.HEAL:
            target_id = action["target_id"]
            target = self.env.entities.get(target_id)
            if target and isinstance(target, Creature):
                old_hp = target.stats.hp
                success = creature.heal(target)
                healing_done = target.stats.hp - old_hp if success else 0
                reward = healing_done * 0.02
            else:
                reward = -0.1
                
        elif action_type == ActionType.HARVEST:
            target_id = action["target_id"]
            target = self.env.entities.get(target_id)
            if target and isinstance(target, Edible):
                old_amount = target.stats.amount
                success = creature.harvest(target)
                amount_harvested = old_amount - target.stats.amount if success else 0
                reward = amount_harvested * 0.05
            else:
                reward = -0.1
                
        elif action_type == ActionType.CHILL:
            old_energy = creature.stats.energy
            creature.chill()
            energy_gained = creature.stats.energy - old_energy
            reward = energy_gained * 0.01
            
        elif action_type == ActionType.REPRODUCE:
            target_id = action["target_id"]
            target = self.env.entities.get(target_id)
            if target and isinstance(target, Creature):
                child = creature.reproduce(target, self.env)
                reward = 1.0 if child else -0.1
            else:
                reward = -0.1
                
        return reward
    
    def _get_state(self) -> State:
        """Return the current state of the environment."""
        # Grid state
        grid = np.array(self.env.grid)
        
        # Entity states
        entities = {}
        for entity_id, entity in self.env.entities.items():
            if isinstance(entity, Creature):
                entities[entity_id] = {
                    "type": "creature",
                    "location": entity.location,
                    "hp": entity.stats.hp,
                    "energy": entity.stats.energy,
                    "attack": entity.stats.attack,
                    "heal": entity.stats.heal,
                    "move_speed": entity.stats.move_speed
                }
            else:  # Edible
                entities[entity_id] = {
                    "type": "edible",
                    "location": entity.location,
                    "amount": entity.stats.amount
                }
        
        return {
            "grid": grid,
            "entities": entities,
            "step": self.step_count
        }
    
    def _is_done(self) -> bool:
        """Check if the episode is done."""
        if self.step_count >= self.config.max_steps:
            return True
            
        # Check if all creatures are dead
        creatures_alive = any(isinstance(e, Creature) for e in self.env.entities.values())
        if not creatures_alive:
            return True
            
        return False
    
    def get_valid_actions(self, creature_id: str) -> List[Action]:
        """Get list of valid actions for a creature."""
        creature = self.env.entities.get(creature_id)
        if not creature or not isinstance(creature, Creature):
            return []
            
        valid_actions = []
        
        # Valid moves
        for loc in creature.get_all_movable_cells(self.env):
            valid_actions.append({
                "type": ActionType.MOVE.value,
                "creature_id": creature_id,
                "target_location": loc
            })
        
        # Adjacent entities for interaction
        adjacent_entities = self.env.get_adjacent_entities(creature.location)
        for entity_id in adjacent_entities:
            entity = self.env.entities.get(entity_id)
            
            if isinstance(entity, Creature):
                # Attack
                valid_actions.append({
                    "type": ActionType.ATTACK.value,
                    "creature_id": creature_id,
                    "target_id": entity_id
                })
                
                # Heal
                valid_actions.append({
                    "type": ActionType.HEAL.value,
                    "creature_id": creature_id,
                    "target_id": entity_id
                })
                
                # Reproduce
                valid_actions.append({
                    "type": ActionType.REPRODUCE.value,
                    "creature_id": creature_id,
                    "target_id": entity_id
                })
                
            elif isinstance(entity, Edible):
                # Harvest
                valid_actions.append({
                    "type": ActionType.HARVEST.value,
                    "creature_id": creature_id,
                    "target_id": entity_id
                })
        
        # Chill (always valid)
        valid_actions.append({
            "type": ActionType.CHILL.value,
            "creature_id": creature_id
        })
        
        return valid_actions
    
    def render(self) -> None:
        """Display the current state of the environment."""
        print("\nEnvironment Grid:")
        self.env._display_grid()
        
        print("\nEntities:")
        for entity_id, entity in self.env.entities.items():
            if isinstance(entity, Creature):
                print(f"Creature {entity_id}:")
                print(f"  Location: {entity.location}")
                print(f"  HP: {entity.stats.hp}/{entity.stats.max_hp}")
                print(f"  Energy: {entity.stats.energy}/{entity.stats.max_energy}")
            else:
                print(f"Edible {entity_id}:")
                print(f"  Location: {entity.location}")
                print(f"  Amount: {entity.stats.amount}")
        print(f"\nStep: {self.step_count}/{self.config.max_steps}")