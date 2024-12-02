from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import random
import numpy as np

from creature import Creature, GENOME_KEYS
from environment import Environment, EnvironmentConfig

@dataclass
class GeneticConfig:
    """Configuration for genetic algorithm."""
    env_size: int = 5
    n_bits: int = 10
    genome_points: int = 20
    init_stat_point: int = 100
    n_edibles: int = 3  # Number of edibles in environment
    edible_amount: int = 100  # Fixed amount for each edible
    population_size: int = 10
    n_generations: int = 5
    tournament_size: int = 3
    elite_size: int = 2
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    seed: Optional[int] = 42

class GeneticOptimizer:
    """Genetic algorithm for optimizing creature behavior."""
    def __init__(self, config: GeneticConfig = None):
        self.config = config or GeneticConfig()
        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)
            
        self.population: List[Creature] = []
        self.env = None
        self.initialize_population()
        
    def initialize_population(self) -> None:
        """Initialize random population and environment."""
        env_config = EnvironmentConfig(
            size=self.config.env_size,
            n_bits=self.config.n_bits,
            genome_points=self.config.genome_points,
            init_stat_point=self.config.init_stat_point
        )
        self.env = Environment(env_config)
        
        # Add edibles first to ensure good distribution
        for _ in range(self.config.n_edibles):
            self.env._add_edible(amount=self.config.edible_amount)
        
        # Create initial population
        for _ in range(self.config.population_size):
            creature = self.env._add_creature()
            if creature:
                self.population.append(creature)
    
    def evaluate_fitness(self, creature: Creature) -> float:
        """Calculate fitness score for a creature."""
        stats = creature.stats
        
        # Base stats contribution (weighted by importance)
        base_fitness = (
            stats.hp * 1.5 + 
            stats.energy * 1.2 + 
            stats.attack * 1.3 + 
            stats.heal * 1.0
        )
        
        # Combat stats contribution (normalized and weighted)
        combat_fitness = (
            stats.move_speed * 50 +
            stats.attack_range * 40 +
            stats.resistance * 150 +
            stats.attack_speed * 120
        )
        
        # Resource management contribution (with diminishing returns)
        resource_fitness = (
            np.log1p(stats.lifespan) * 30 +
            np.log1p(stats.harvest) * 25 +
            np.log1p(stats.chill) * 20
        )
        
        # Behavioral traits contribution (with penalties)
        behavior_fitness = (
            stats.tendency_to_help * 80 +
            stats.reproduction_rate * 100 +
            (1 - stats.decay) * 120  # Lower decay is better
        )
        
        # Add random noise to break ties (very small amount)
        noise = random.uniform(0, 0.1)
        
        return base_fitness + combat_fitness + resource_fitness + behavior_fitness + noise

    def select_parents(self, n_parents: int) -> List[Creature]:
        """Select parents using tournament selection with diversity preservation."""
        parents = []
        tournament_size = min(self.config.tournament_size, len(self.population))
        
        # Calculate population diversity
        genomes = [tuple(sum(c.genome[k]) for k in GENOME_KEYS) for c in self.population]
        unique_genomes = len(set(genomes))
        
        # Adjust selection pressure based on diversity
        diversity_weight = max(0.2, unique_genomes / len(self.population))
        
        for _ in range(n_parents):
            tournament = random.sample(self.population, tournament_size)
            
            if random.random() < diversity_weight:
                # Select for diversity
                winner = max(tournament, 
                           key=lambda x: self.evaluate_fitness(x) * 
                           (1 + 0.2 * (genomes.count(tuple(sum(x.genome[k]) for k in GENOME_KEYS)) == 1)))
            else:
                # Select for fitness
                winner = max(tournament, key=self.evaluate_fitness)
                
            parents.append(winner)
            
        return parents

    def crossover(self, parent1: Creature, parent2: Creature) -> Creature:
        """Create child through enhanced crossover."""
        child_genome = {}
        
        for key in GENOME_KEYS:
            # Always do crossover for better mixing
            # Multi-point crossover with 2-3 points
            n_points = random.randint(2, 3)
            points = sorted(random.sample(range(1, len(parent1.genome[key])), n_points))
            
            # Build child genome by alternating between parents
            child_gene = []
            start = 0
            parent = parent1 if random.random() < 0.5 else parent2
            
            for point in points + [len(parent1.genome[key])]:
                child_gene.extend(parent.genome[key][start:point])
                parent = parent2 if parent == parent1 else parent1
                start = point
                
            child_genome[key] = child_gene
            
            # Small chance of mutation during crossover
            if random.random() < self.config.mutation_rate * 0.5:
                idx = random.randint(0, len(child_genome[key]) - 1)
                child_genome[key][idx] = 1 - child_genome[key][idx]
        
        return Creature(
            id=self.env._generate_creature_id(),
            genome=child_genome,
            n_bits=parent1.n_bits,
            init_stat_point=parent1.init_stat_point,
            location=self.env.get_random_empty_location()
        )

    def mutate(self, creature: Creature) -> None:
        """Apply adaptive mutation to creature's genome."""
        # Calculate current fitness
        fitness = self.evaluate_fitness(creature)
        
        # Get population statistics
        pop_fitnesses = [self.evaluate_fitness(c) for c in self.population]
        avg_fitness = sum(pop_fitnesses) / len(pop_fitnesses)
        
        # Adjust mutation rate based on fitness
        if fitness < avg_fitness:
            # Increase mutation rate for below-average individuals
            effective_rate = min(1.0, self.config.mutation_rate * 1.5)
        else:
            # Decrease mutation rate for above-average individuals
            effective_rate = max(0.01, self.config.mutation_rate * 0.8)
            
        for key in creature.genome:
            if random.random() < effective_rate:
                # Number of bits to mutate (1-2)
                n_mutations = random.randint(1, 2)
                for _ in range(n_mutations):
                    idx = random.randint(0, len(creature.genome[key]) - 1)
                    creature.genome[key][idx] = 1 - creature.genome[key][idx]

    def evolve(self, n_generations: int) -> List[Creature]:
        """Run evolution for specified generations."""
        best_fitness = float('-inf')
        best_creature = None
        
        for gen in range(n_generations):
            # Evaluate and sort population
            self.population.sort(key=self.evaluate_fitness, reverse=True)
            current_best = self.population[0]
            current_fitness = self.evaluate_fitness(current_best)
            
            if current_fitness > best_fitness:
                best_fitness = current_fitness
                best_creature = current_best
                
            # Print progress
            avg_fitness = sum(map(self.evaluate_fitness, self.population)) / len(self.population)
            print(f"Generation {gen}:")
            print(f"  Best Fitness: {current_fitness:.2f}")
            print(f"  Avg Fitness: {avg_fitness:.2f}")
            
            # Create next generation
            next_gen = []
            
            # Elitism: Keep best individuals
            next_gen.extend(self.population[:self.config.elite_size])
            
            # Fill rest with children
            parents = self.select_parents(max(len(self.population) // 2, 4))
            while len(next_gen) < self.config.population_size:
                parent1, parent2 = random.sample(parents, 2)
                child = self.crossover(parent1, parent2)
                self.mutate(child)
                next_gen.append(child)
            
            self.population = next_gen[:self.config.population_size]
            
            # Ensure we don't lose the best solution
            if best_creature and self.evaluate_fitness(self.population[0]) < best_fitness:
                self.population[-1] = best_creature
        
        # Return final population sorted by fitness
        self.population.sort(key=self.evaluate_fitness, reverse=True)
        return self.population

def main():
    """Run genetic algorithm optimization."""
    config = GeneticConfig(
        env_size=5,
        n_bits=8,
        genome_points=4,
        init_stat_point=100,
        n_edibles=3,
        edible_amount=100,
        population_size=20,
        n_generations=10,
        tournament_size=4,
        elite_size=2,
        mutation_rate=0.1,
        crossover_rate=0.7,
        seed=42
    )
    
    optimizer = GeneticOptimizer(config)
    final_population = optimizer.evolve(config.n_generations)
    
    print("\nBest creature stats:")
    best_creature = final_population[0]
    print(f"Fitness: {optimizer.evaluate_fitness(best_creature):.2f}")
    print("Stats:")
    for key, value in best_creature.stats.__dict__.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
