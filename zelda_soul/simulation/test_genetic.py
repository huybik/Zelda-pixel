import unittest
import random
import numpy as np
from typing import List

from creature import Creature, GENOME_KEYS
from genetic import GeneticConfig, GeneticOptimizer

class TestGeneticOptimizer(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.config = GeneticConfig(
            env_size=5,
            n_bits=8,
            genome_points=4,
            init_stat_point=100,
            population_size=6,
            n_generations=2,
            tournament_size=2,
            elite_size=1,
            mutation_rate=0.2,
            crossover_rate=0.8,
            seed=42
        )
        self.optimizer = GeneticOptimizer(self.config)
        
    def test_population_initialization(self):
        """Test population initialization."""
        # Check population size
        self.assertEqual(len(self.optimizer.population), self.config.population_size)
        
        # Check creature structure
        for creature in self.optimizer.population:
            # Check genome structure
            self.assertEqual(len(creature.genome), len(GENOME_KEYS))
            for gene in creature.genome.values():
                self.assertEqual(len(gene), self.config.n_bits)
                
            # Check location validity
            x, y = creature.location
            self.assertTrue(0 <= x < self.config.env_size)
            self.assertTrue(0 <= y < self.config.env_size)
            
    def test_environment_initialization(self):
        """Test environment initialization with edibles."""
        # Count edibles in environment
        edibles = [
            entity for entity in self.optimizer.env.entities.values()
            if entity.id.startswith('e')
        ]
        
        # Check number of edibles
        self.assertEqual(len(edibles), self.config.n_edibles)
        
        # Check edible amounts
        for edible in edibles:
            self.assertEqual(
                edible.stats.amount,
                self.config.edible_amount
            )
            
        # Check edible locations
        edible_locations = [e.location for e in edibles]
        self.assertEqual(
            len(edible_locations),
            len(set(edible_locations))  # No duplicates
        )
        
    def test_fitness_evaluation(self):
        """Test fitness calculation."""
        # Get fitness for each creature
        fitness_scores = [
            self.optimizer.evaluate_fitness(c) 
            for c in self.optimizer.population
        ]
        
        # Check fitness values
        for fitness in fitness_scores:
            self.assertIsInstance(fitness, float)
            self.assertGreater(fitness, 0)
            
        # Check fitness diversity
        unique_scores = len(set(fitness_scores))
        self.assertGreater(unique_scores, 1)
        
    def test_parent_selection(self):
        """Test parent selection."""
        n_parents = 4
        
        # Select parents
        parents = self.optimizer.select_parents(n_parents)
        
        # Check number of parents
        self.assertEqual(len(parents), n_parents)
        
        # Check parent validity
        for parent in parents:
            self.assertIsInstance(parent, Creature)
            self.assertIn(parent, self.optimizer.population)
            
    def test_crossover(self):
        """Test crossover operation."""
        parent1 = self.optimizer.population[0]
        parent2 = self.optimizer.population[1]
        
        # Create child
        child = self.optimizer.crossover(parent1, parent2)
        
        # Check child structure
        self.assertIsInstance(child, Creature)
        self.assertEqual(len(child.genome), len(GENOME_KEYS))
        
        # Check genome mixing
        mixed = False
        for key in GENOME_KEYS:
            if (child.genome[key] != parent1.genome[key] and 
                child.genome[key] != parent2.genome[key]):
                mixed = True
                break
        self.assertTrue(mixed)
        
    def test_mutation(self):
        """Test mutation operation."""
        creature = self.optimizer.population[0]
        
        # Store original genome
        original = {
            key: gene.copy() 
            for key, gene in creature.genome.items()
        }
        
        # Apply mutation multiple times
        n_mutations = 5
        for _ in range(n_mutations):
            self.optimizer.mutate(creature)
        
        # Check for changes
        changes = 0
        for key in GENOME_KEYS:
            if creature.genome[key] != original[key]:
                changes += 1
        self.assertGreater(changes, 0)
        
    def test_evolution(self):
        """Test evolution process."""
        n_generations = 3
        
        # Get initial best fitness
        initial_best = max(
            self.optimizer.population,
            key=self.optimizer.evaluate_fitness
        )
        initial_fitness = self.optimizer.evaluate_fitness(initial_best)
        
        # Run evolution
        final_population = self.optimizer.evolve(n_generations)
        
        # Check population size maintained
        self.assertEqual(
            len(final_population), 
            self.config.population_size
        )
        
        # Check fitness improved
        final_best = max(
            final_population,
            key=self.optimizer.evaluate_fitness
        )
        final_fitness = self.optimizer.evaluate_fitness(final_best)
        
        self.assertGreater(final_fitness, initial_fitness)
        
if __name__ == "__main__":
    unittest.main()
