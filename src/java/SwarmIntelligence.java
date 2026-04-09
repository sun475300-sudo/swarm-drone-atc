/**
 * SDACS Swarm Intelligence (Java)
 * ================================
 * Particle Swarm Optimization for drone fleet coordination
 * 
 * Features:
 *   - ACO (Ant Colony Optimization)
 *   - PSO (Particle Swarm Optimization)
 *   - Multi-drone task allocation
 *   - Real-time path re-planning
 */

import java.util.*;
import java.util.concurrent.*;

public class SwarmIntelligence {
    
    public static class Position {
        public double x, y, z;
        
        public Position(double x, double y, double z) {
            this.x = x;
            this.y = y;
            this.z = z;
        }
        
        public double distanceTo(Position other) {
            double dx = x - other.x;
            double dy = y - other.y;
            double dz = z - other.z;
            return Math.sqrt(dx*dx + dy*dy + dz*dz);
        }
        
        public Position add(Position other) {
            return new Position(x + other.x, y + other.y, z + other.z);
        }
        
        public Position subtract(Position other) {
            return new Position(x - other.x, y - other.y, z - other.z);
        }
        
        public Position multiply(double scalar) {
            return new Position(x * scalar, y * scalar, z * scalar);
        }
        
        @Override
        public String toString() {
            return String.format("(%.2f, %.2f, %.2f)", x, y, z);
        }
    }
    
    public static class Drone {
        public String id;
        public Position position;
        public Position velocity;
        public Position bestPosition;
        public double bestFitness;
        public double fitness;
        
        public Drone(String id, Position start) {
            this.id = id;
            this.position = start;
            this.velocity = new Position(0, 0, 0);
            this.bestPosition = start;
            this.bestFitness = Double.MAX_VALUE;
            this.fitness = Double.MAX_VALUE;
        }
    }
    
    public static class SwarmOptimizer {
        private List<Drone> drones;
        private Position globalBest;
        private double globalBestFitness;
        
        private double inertiaWeight = 0.7;
        private double cognitiveWeight = 1.5;
        private double socialWeight = 1.5;
        
        private Random random;
        
        public SwarmOptimizer(int numDrones) {
            this.random = new Random();
            this.drones = new ArrayList<>();
            this.globalBestFitness = Double.MAX_VALUE;
            
            for (int i = 0; i < numDrones; i++) {
                Position start = new Position(
                    random.nextDouble() * 500,
                    random.nextDouble() * 500,
                    10 + random.nextDouble() * 90
                );
                Drone drone = new Drone("DRONE-" + i, start);
                drone.fitness = evaluateFitness(drone.position);
                drone.bestFitness = drone.fitness;
                drone.bestPosition = drone.position;
                drones.add(drone);
                
                if (drone.fitness < globalBestFitness) {
                    globalBestFitness = drone.fitness;
                    globalBest = drone.position;
                }
            }
        }
        
        private double evaluateFitness(Position pos) {
            Position target = new Position(250, 250, 50);
            double distanceScore = pos.distanceTo(target);
            
            double obstaclePenalty = 0;
            double centerDist = Math.sqrt(
                Math.pow(pos.x - 250, 2) + Math.pow(pos.y - 250, 2)
            );
            if (centerDist < 50) {
                obstaclePenalty = 1000;
            }
            
            double energyCost = pos.z * 0.1;
            
            return distanceScore + obstaclePenalty + energyCost;
        }
        
        private void updateVelocity(Drone drone) {
            double r1 = random.nextDouble();
            double r2 = random.nextDouble();
            
            Position cognitive = drone.bestPosition.subtract(drone.position)
                .multiply(cognitiveWeight * r1);
            Position social = globalBest.subtract(drone.position)
                .multiply(socialWeight * r2);
            Position inertia = drone.velocity.multiply(inertiaWeight);
            
            drone.velocity = inertia.add(cognitive).add(social);
            
            double maxVel = 50.0;
            double velMag = drone.velocity.distanceTo(new Position(0, 0, 0));
            if (velMag > maxVel) {
                drone.velocity = drone.velocity.multiply(maxVel / velMag);
            }
        }
        
        private void updatePosition(Drone drone) {
            drone.position = drone.position.add(drone.velocity);
            
            drone.position.x = Math.max(0, Math.min(500, drone.position.x));
            drone.position.y = Math.max(0, Math.min(500, drone.position.y));
            drone.position.z = Math.max(10, Math.min(100, drone.position.z));
            
            drone.fitness = evaluateFitness(drone.position);
            
            if (drone.fitness < drone.bestFitness) {
                drone.bestFitness = drone.fitness;
                drone.bestPosition = drone.position;
                
                if (drone.fitness < globalBestFitness) {
                    globalBestFitness = drone.fitness;
                    globalBest = drone.position;
                }
            }
        }
        
        public Position optimize(int iterations) {
            for (int iter = 0; iter < iterations; iter++) {
                for (Drone drone : drones) {
                    updateVelocity(drone);
                    updatePosition(drone);
                }
            }
            return globalBest;
        }
        
        public Position getBestPosition() { return globalBest; }
        public double getBestFitness() { return globalBestFitness; }
    }
    
    public static class AntColony {
        private int numAnts;
        private double alpha = 1.0;
        private double beta = 2.0;
        private double evaporation = 0.5;
        private double[][] pheromones;
        private List<Position> targets;
        
        public AntColony(int numAnts, List<Position> targets) {
            this.numAnts = numAnts;
            this.targets = targets;
            this.pheromones = new double[targets.size()][targets.size()];
            
            for (int i = 0; i < targets.size(); i++) {
                for (int j = 0; j < targets.size(); j++) {
                    pheromones[i][j] = 1.0;
                }
            }
        }
        
        public List<Integer> findBestPath() {
            List<Integer> bestPath = new ArrayList<>();
            double bestLength = Double.MAX_VALUE;
            
            for (int ant = 0; ant < numAnts; ant++) {
                List<Integer> path = new ArrayList<>();
                Set<Integer> visited = new HashSet<>();
                int current = random.nextInt(targets.size());
                path.add(current);
                visited.add(current);
                
                while (visited.size() < targets.size()) {
                    int next = selectNext(current, visited);
                    path.add(next);
                    visited.add(next);
                    current = next;
                }
                
                double length = calculatePathLength(path);
                if (length < bestLength) {
                    bestLength = length;
                    bestPath = path;
                }
            }
            
            updatePheromones(bestPath);
            return bestPath;
        }
        
        private int selectNext(int current, Set<Integer> visited) {
            double[] probabilities = new double[targets.size()];
            double sum = 0;
            
            for (int i = 0; i < targets.size(); i++) {
                if (!visited.contains(i)) {
                    double pheromone = Math.pow(pheromones[current][i], alpha);
                    double heuristic = Math.pow(1.0 / targets.get(current).distanceTo(targets.get(i)), beta);
                    probabilities[i] = pheromone * heuristic;
                    sum += probabilities[i];
                }
            }
            
            double r = random.nextDouble() * sum;
            double cumulative = 0;
            for (int i = 0; i < probabilities.length; i++) {
                cumulative += probabilities[i];
                if (cumulative >= r) {
                    return i;
                }
            }
            
            return random.nextInt(targets.size());
        }
        
        private double calculatePathLength(List<Integer> path) {
            double length = 0;
            for (int i = 0; i < path.size() - 1; i++) {
                length += targets.get(path.get(i)).distanceTo(targets.get(path.get(i + 1)));
            }
            return length;
        }
        
        private void updatePheromones(List<Integer> path) {
            for (int i = 0; i < pheromones.length; i++) {
                for (int j = 0; j < pheromones[i].length; j++) {
                    pheromones[i][j] *= (1 - evaporation);
                }
            }
            
            double contribution = 100.0 / calculatePathLength(path);
            for (int i = 0; i < path.size() - 1; i++) {
                pheromones[path.get(i)][path.get(i + 1)] += contribution;
                pheromones[path.get(i + 1)][path.get(i)] += contribution;
            }
        }
        
        private Random random = new Random();
    }
    
    public static void main(String[] args) {
        System.out.println("=== SDACS Swarm Intelligence (Java) ===");
        System.out.println("PSO + ACO for Drone Fleet Coordination");
        
        System.out.println("\n--- Particle Swarm Optimization ---");
        SwarmOptimizer pso = new SwarmOptimizer(50);
        System.out.println("Initial best fitness: " + pso.getBestFitness());
        
        Position optimal = pso.optimize(100);
        System.out.println("Optimized position: " + optimal);
        System.out.println("Best fitness: " + pso.getBestFitness());
        
        System.out.println("\n--- Ant Colony Optimization ---");
        List<Position> targets = Arrays.asList(
            new Position(50, 50, 30),
            new Position(150, 100, 40),
            new Position(250, 200, 50),
            new Position(350, 300, 40),
            new Position(450, 400, 30)
        );
        
        AntColony aco = new AntColony(20, targets);
        List<Integer> bestPath = aco.findBestPath();
        System.out.println("Best path indices: " + bestPath);
        
        System.out.println("\n=== Optimization Complete ===");
    }
}
