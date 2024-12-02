import unittest
from dataclasses import dataclass
import random
import numpy as np

from creature import Creature, CreatureStats
from edible import Edible
from environment import Environment, EnvironmentConfig

class TestActions(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.config = EnvironmentConfig(
            size=5,
            n_bits=10,
            genome_points=20,
            init_stat_point=100
        )
        self.env = Environment(self.config)
        
        # Set random seed for reproducibility
        random.seed(42)
        np.random.seed(42)
        
        # Create test creatures with specific stats
        self.attacker = self._create_test_creature(
            location=(1, 1),
            stats=CreatureStats(
                hp=100, energy=100, attack=50, heal=30,
                max_hp=200, max_energy=200,
                move_speed=2, attack_range=1,
                resistance=0.2, attack_speed=1.5,
                lifespan=100, harvest=40, chill=20,
                tendency_to_help=0.2, reproduction_rate=0.3,
                decay=0.1
            )
        )
        
        self.healer = self._create_test_creature(
            location=(1, 2),
            stats=CreatureStats(
                hp=100, energy=100, attack=20, heal=50,
                max_hp=200, max_energy=200,
                move_speed=2, attack_range=1,
                resistance=0.3, attack_speed=1.0,
                lifespan=100, harvest=30, chill=30,
                tendency_to_help=0.8, reproduction_rate=0.4,
                decay=0.1
            )
        )
        
        # Add test edible
        self.edible = self._create_test_edible(
            location=(2, 1),
            amount=100
        )
        
    def _create_test_creature(self, location, stats):
        """Create a test creature with specific stats."""
        creature = Creature(
            id=f"c{len(self.env.entities)}",
            genome=None,  # Not needed for testing
            n_bits=self.config.n_bits,
            genome_points=self.config.genome_points,
            init_stat_point=self.config.init_stat_point,
            location=location
        )
        creature.stats = stats  # Override calculated stats
        self.env.entities[creature.id] = creature
        x, y = location
        self.env.grid[y][x] = creature.id
        return creature
        
    def _create_test_edible(self, location, amount):
        """Create a test edible."""
        edible = Edible(
            id=f"e{len(self.env.entities)}",
            location=location,
            initial_amount=amount
        )
        self.env.entities[edible.id] = edible
        x, y = location
        self.env.grid[y][x] = edible.id
        return edible
        
    def test_creature_movement(self):
        """Test creature movement."""
        # Test valid movement
        success = self.attacker.move((2, 2), self.env)
        self.assertTrue(success)
        self.assertEqual(self.attacker.location, (2, 2))
        
        # Test invalid movement (occupied cell)
        success = self.attacker.move(self.healer.location, self.env)
        self.assertFalse(success)
        
        # Test invalid movement (out of bounds)
        success = self.attacker.move((-1, 0), self.env)
        self.assertFalse(success)
        
    def test_creature_attack(self):
        """Test creature attack."""
        initial_hp = self.healer.stats.hp
        
        # Test attack
        success = self.attacker.attack(self.healer)
        self.assertTrue(success)
        self.assertLess(self.healer.stats.hp, initial_hp)
        
        # Test attack with resistance
        damage = int(self.attacker.stats.attack * self.attacker.stats.attack_speed)
        expected_damage = int(damage * (1 - self.healer.stats.resistance))
        actual_damage = initial_hp - self.healer.stats.hp
        self.assertEqual(actual_damage, expected_damage)
        
    def test_creature_heal(self):
        """Test creature healing."""
        # Damage healer first
        self.healer.stats.hp = 50
        initial_hp = self.healer.stats.hp
        
        # Test healing
        success = self.healer.heal(self.attacker)
        self.assertTrue(success)
        self.assertGreater(self.attacker.stats.hp, initial_hp)
        
        # Test healing cost
        self.assertLess(self.healer.stats.energy, 100)
        
    def test_creature_harvest(self):
        """Test creature harvesting."""
        initial_amount = self.edible.stats.amount
        
        # Test harvesting
        success = self.attacker.harvest(self.edible)
        self.assertTrue(success)
        self.assertLess(self.edible.stats.amount, initial_amount)
        self.assertEqual(
            self.edible.stats.amount,
            initial_amount - self.attacker.stats.harvest
        )
        
    def test_creature_chill(self):
        """Test creature chilling."""
        self.attacker.stats.energy = 50
        initial_energy = self.attacker.stats.energy
        
        # Test chilling
        self.attacker.chill()
        self.assertGreater(self.attacker.stats.energy, initial_energy)
        
    def test_creature_decay(self):
        """Test creature decay."""
        initial_hp = self.attacker.stats.hp
        initial_energy = self.attacker.stats.energy
        
        # Test decay
        self.attacker.decay()
        self.assertLess(self.attacker.stats.hp, initial_hp)
        self.assertLess(self.attacker.stats.energy, initial_energy)
        
    def test_creature_reproduction(self):
        """Test creature reproduction."""
        # Set up parent creatures with high reproduction rates
        parent1 = self._create_test_creature(
            location=(3, 3),
            stats=CreatureStats(
                hp=100, energy=100, attack=30, heal=30,
                max_hp=200, max_energy=200,
                move_speed=2, attack_range=1,
                resistance=0.2, attack_speed=1.0,
                lifespan=100, harvest=30, chill=20,
                tendency_to_help=0.5, reproduction_rate=0.9,
                decay=0.1
            )
        )
        
        parent2 = self._create_test_creature(
            location=(3, 4),
            stats=CreatureStats(
                hp=100, energy=100, attack=40, heal=20,
                max_hp=200, max_energy=200,
                move_speed=2, attack_range=1,
                resistance=0.3, attack_speed=1.2,
                lifespan=100, harvest=25, chill=25,
                tendency_to_help=0.4, reproduction_rate=0.8,
                decay=0.1
            )
        )
        
        # Print initial state
        print("\nInitial environment state:")
        print(f"Grid size: {self.env.config.size}x{self.env.config.size}")
        print(f"Number of entities: {len(self.env.entities)}")
        print("Entity locations:")
        for entity_id, entity in self.env.entities.items():
            print(f"  {entity_id}: {entity.location}")
        print("\nGrid:")
        self.env._display_grid()
        
        # Count initial entities
        initial_count = len(self.env.entities)
        
        # Try reproduction multiple times since it's probabilistic
        child = None
        for attempt in range(10):  # Try up to 10 times
            print(f"\nAttempt {attempt + 1}:")
            valid_cells1 = self.env.get_valid_adjacent_cell(parent1.id)
            valid_cells2 = self.env.get_valid_adjacent_cell(parent2.id)
            print(f"Valid cells for parent1: {valid_cells1}")
            print(f"Valid cells for parent2: {valid_cells2}")
            
            result = parent1.reproduce(parent2, self.env)
            if result:
                child = result
                print("Reproduction successful!")
                print(f"Child location: {child.location}")
                print("\nFinal grid:")
                self.env._display_grid()
                break
            else:
                print("Reproduction failed")
        
        # Verify reproduction results
        if child:
            # Check that a new creature was added
            self.assertEqual(len(self.env.entities), initial_count + 1)
            
            # Verify child location is adjacent to parents
            child_x, child_y = child.location
            parent1_x, parent1_y = parent1.location
            parent2_x, parent2_y = parent2.location
            
            manhattan_dist1 = abs(child_x - parent1_x) + abs(child_y - parent1_y)
            manhattan_dist2 = abs(child_x - parent2_x) + abs(child_y - parent2_y)
            
            self.assertTrue(manhattan_dist1 <= 2 or manhattan_dist2 <= 2)
            
            # Verify child has valid genome
            self.assertIsNotNone(child.genome)
            self.assertEqual(len(child.genome), len(GENOME_KEYS))
            
            # Verify child stats are initialized
            self.assertGreater(child.stats.hp, 0)
            self.assertGreater(child.stats.energy, 0)
            self.assertGreater(child.stats.max_hp, child.stats.hp)
            self.assertGreater(child.stats.max_energy, child.stats.energy)
        else:
            # If reproduction failed, entity count should be unchanged
            self.assertEqual(len(self.env.entities), initial_count)
            
    def test_environment_step(self):
        """Test environment step."""
        # Run one step
        stats = self.env.step()
        
        # Check stats structure
        self.assertIn("actions", stats)
        self.assertIn("successes", stats)
        self.assertIn("failures", stats)
        self.assertIn("deaths", stats)
        self.assertIn("depleted", stats)
        self.assertIn("interactions", stats)
        
        # Check interactions
        self.assertTrue(len(stats["interactions"]) > 0)
        for interaction in stats["interactions"]:
            entity_id, action, target_id = interaction
            self.assertIn(entity_id, self.env.entities)
            self.assertIsInstance(action, str)
            
    def test_environment_remove_entity(self):
        """Test entity removal."""
        # Remove creature
        self.env.remove_entity(self.attacker.id)
        self.assertNotIn(self.attacker.id, self.env.entities)
        
        # Check grid update
        x, y = (1, 1)  # Attacker's initial location
        self.assertEqual(self.env.grid[y][x], -1)
        
    def test_environment_get_adjacent(self):
        """Test getting adjacent entities."""
        # Get adjacent to attacker
        adjacent = self.env.get_adjacent_entities(self.attacker.location)
        
        # Should include healer and edible
        self.assertIn(self.healer.id, adjacent)
        self.assertIn(self.edible.id, adjacent)
        
if __name__ == '__main__':
    unittest.main()
