// Phase 492: Swarm Evolution Engine (Rust)
// NEAT 기반 신경진화, 안전한 유전자 교차/변이

use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct Gene {
    pub innovation: u32,
    pub src: usize,
    pub dst: usize,
    pub weight: f64,
    pub enabled: bool,
}

#[derive(Clone, Debug)]
pub struct Genome {
    pub id: u32,
    pub genes: Vec<Gene>,
    pub n_inputs: usize,
    pub n_outputs: usize,
    pub n_hidden: usize,
    pub fitness: f64,
}

impl Genome {
    pub fn new(id: u32, n_inputs: usize, n_outputs: usize) -> Self {
        Genome { id, genes: Vec::new(), n_inputs, n_outputs, n_hidden: 0, fitness: 0.0 }
    }

    pub fn activate(&self, inputs: &[f64]) -> Vec<f64> {
        let total = self.n_inputs + self.n_outputs + self.n_hidden;
        let mut values = vec![0.0; total];
        for (i, &v) in inputs.iter().enumerate().take(self.n_inputs) {
            values[i] = v;
        }
        for gene in &self.genes {
            if gene.enabled && gene.src < total && gene.dst < total {
                values[gene.dst] += values[gene.src] * gene.weight;
            }
        }
        values[self.n_inputs..self.n_inputs + self.n_outputs]
            .iter()
            .map(|&v| v.tanh())
            .collect()
    }

    pub fn distance(&self, other: &Genome) -> f64 {
        let my_innovations: std::collections::HashSet<u32> =
            self.genes.iter().map(|g| g.innovation).collect();
        let other_innovations: std::collections::HashSet<u32> =
            other.genes.iter().map(|g| g.innovation).collect();
        let disjoint = my_innovations.symmetric_difference(&other_innovations).count();
        let common: Vec<u32> = my_innovations.intersection(&other_innovations).cloned().collect();

        let mut weight_diff = 0.0;
        if !common.is_empty() {
            let my_weights: HashMap<u32, f64> =
                self.genes.iter().map(|g| (g.innovation, g.weight)).collect();
            let other_weights: HashMap<u32, f64> =
                other.genes.iter().map(|g| (g.innovation, g.weight)).collect();
            for &inn in &common {
                if let (Some(&w1), Some(&w2)) = (my_weights.get(&inn), other_weights.get(&inn)) {
                    weight_diff += (w1 - w2).abs();
                }
            }
            weight_diff /= common.len() as f64;
        }

        let n = self.genes.len().max(other.genes.len()).max(1) as f64;
        disjoint as f64 / n + 0.4 * weight_diff
    }
}

pub struct PRNG {
    state: u64,
}

impl PRNG {
    pub fn new(seed: u64) -> Self {
        PRNG { state: seed.wrapping_add(1) }
    }

    pub fn next_f64(&mut self) -> f64 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        (self.state as f64) / (u64::MAX as f64)
    }

    pub fn next_gaussian(&mut self) -> f64 {
        let u1 = self.next_f64().max(1e-10);
        let u2 = self.next_f64();
        (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
    }
}

pub struct NEATEvolver {
    pub population: Vec<Genome>,
    pub generation: u32,
    innovation_counter: u32,
    genome_counter: u32,
    rng: PRNG,
}

impl NEATEvolver {
    pub fn new(pop_size: usize, n_inputs: usize, n_outputs: usize, seed: u64) -> Self {
        let mut rng = PRNG::new(seed);
        let mut innovation_counter = 0u32;
        let mut population = Vec::with_capacity(pop_size);

        for i in 0..pop_size {
            let mut genome = Genome::new(i as u32, n_inputs, n_outputs);
            for src in 0..n_inputs {
                for dst in 0..n_outputs {
                    innovation_counter += 1;
                    genome.genes.push(Gene {
                        innovation: innovation_counter,
                        src,
                        dst: n_inputs + dst,
                        weight: rng.next_gaussian() * 0.5,
                        enabled: true,
                    });
                }
            }
            population.push(genome);
        }

        NEATEvolver {
            population,
            generation: 0,
            innovation_counter,
            genome_counter: pop_size as u32,
            rng,
        }
    }

    pub fn mutate(&mut self, genome: &Genome) -> Genome {
        self.genome_counter += 1;
        let mut new_genes: Vec<Gene> = genome.genes.iter().cloned().collect();
        let mut n_hidden = genome.n_hidden;

        // Weight mutation
        for gene in &mut new_genes {
            if self.rng.next_f64() < 0.1 {
                gene.weight += self.rng.next_gaussian() * 0.3;
            }
        }

        // Add node
        if self.rng.next_f64() < 0.05 && !new_genes.is_empty() {
            let idx = (self.rng.next_f64() * new_genes.len() as f64) as usize % new_genes.len();
            let old = new_genes[idx].clone();
            new_genes[idx].enabled = false;
            let new_node = genome.n_inputs + genome.n_outputs + n_hidden;
            self.innovation_counter += 1;
            new_genes.push(Gene {
                innovation: self.innovation_counter, src: old.src,
                dst: new_node, weight: 1.0, enabled: true,
            });
            self.innovation_counter += 1;
            new_genes.push(Gene {
                innovation: self.innovation_counter, src: new_node,
                dst: old.dst, weight: old.weight, enabled: true,
            });
            n_hidden += 1;
        }

        // Add link
        if self.rng.next_f64() < 0.1 {
            let total = genome.n_inputs + genome.n_outputs + n_hidden;
            let src = (self.rng.next_f64() * total as f64) as usize % total;
            let dst = genome.n_inputs + (self.rng.next_f64() * (total - genome.n_inputs) as f64) as usize % (total - genome.n_inputs).max(1);
            if src != dst {
                self.innovation_counter += 1;
                new_genes.push(Gene {
                    innovation: self.innovation_counter, src, dst,
                    weight: self.rng.next_gaussian() * 0.5, enabled: true,
                });
            }
        }

        Genome {
            id: self.genome_counter,
            genes: new_genes,
            n_inputs: genome.n_inputs,
            n_outputs: genome.n_outputs,
            n_hidden,
            fitness: 0.0,
        }
    }

    pub fn crossover(&mut self, p1: &Genome, p2: &Genome) -> Genome {
        let (better, worse) = if p1.fitness >= p2.fitness { (p1, p2) } else { (p2, p1) };
        let worse_map: HashMap<u32, &Gene> = worse.genes.iter().map(|g| (g.innovation, g)).collect();
        self.genome_counter += 1;
        let mut child_genes = Vec::new();

        for gene in &better.genes {
            if let Some(other) = worse_map.get(&gene.innovation) {
                if self.rng.next_f64() < 0.5 {
                    child_genes.push((*other).clone());
                } else {
                    child_genes.push(gene.clone());
                }
            } else {
                child_genes.push(gene.clone());
            }
        }

        Genome {
            id: self.genome_counter,
            genes: child_genes,
            n_inputs: better.n_inputs,
            n_outputs: better.n_outputs,
            n_hidden: better.n_hidden.max(worse.n_hidden),
            fitness: 0.0,
        }
    }

    pub fn evolve(&mut self) {
        self.generation += 1;
        self.population.sort_by(|a, b| b.fitness.partial_cmp(&a.fitness).unwrap());
        let elite = (self.population.len() / 10).max(2);
        let mut new_pop: Vec<Genome> = self.population[..elite].to_vec();

        while new_pop.len() < self.population.len() {
            let idx1 = (self.rng.next_f64() * elite as f64) as usize % elite;
            let idx2 = (self.rng.next_f64() * elite as f64) as usize % elite;
            let p1 = self.population[idx1].clone();
            let p2 = self.population[idx2].clone();
            let child = self.crossover(&p1, &p2);
            let mutated = self.mutate(&child);
            new_pop.push(mutated);
        }

        self.population = new_pop;
    }

    pub fn best_fitness(&self) -> f64 {
        self.population.iter().map(|g| g.fitness).fold(f64::NEG_INFINITY, f64::max)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_genome_activate() {
        let mut evolver = NEATEvolver::new(10, 3, 2, 42);
        let genome = &evolver.population[0];
        let output = genome.activate(&[1.0, 0.5, -0.3]);
        assert_eq!(output.len(), 2);
        assert!(output.iter().all(|&v| v >= -1.0 && v <= 1.0));
    }

    #[test]
    fn test_evolution() {
        let mut evolver = NEATEvolver::new(20, 4, 2, 42);
        for genome in &mut evolver.population {
            genome.fitness = genome.genes.len() as f64 * 0.1;
        }
        evolver.evolve();
        assert_eq!(evolver.generation, 1);
        assert_eq!(evolver.population.len(), 20);
    }

    #[test]
    fn test_genetic_distance() {
        let evolver = NEATEvolver::new(10, 3, 2, 42);
        let d = evolver.population[0].distance(&evolver.population[1]);
        assert!(d >= 0.0);
    }
}
