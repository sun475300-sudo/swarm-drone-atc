/**
 * SDACS Swarm Intelligence (C++)
 * ==============================
 * Particle Swarm Optimization (PSO) for drone path planning
 * 
 * Features:
 *   - Particle Swarm Optimization
 *   - Multi-objective path optimization
 *   - Parallel computation with OpenMP
 *   - 3D trajectory optimization
 */

#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <omp.h>

struct Position {
    double x, y, z;
    
    Position operator+(const Position& other) const {
        return {x + other.x, y + other.y, z + other.z};
    }
    
    Position operator-(const Position& other) const {
        return {x - other.x, y - other.y, z - other.z};
    }
    
    Position operator*(double scalar) const {
        return {x * scalar, y * scalar, z * scalar};
    }
    
    double distanceTo(const Position& other) const {
        double dx = x - other.x;
        double dy = y - other.y;
        double dz = z - other.z;
        return std::sqrt(dx*dx + dy*dy + dz*dz);
    }
};

struct Particle {
    Position position;
    Position velocity;
    Position bestPosition;
    double bestFitness;
    double fitness;
    
    Particle(Position start, double fitness) 
        : position(start), velocity({0,0,0}), bestPosition(start), 
          bestFitness(fitness), fitness(fitness) {}
};

class SwarmOptimizer {
private:
    std::vector<Particle> particles;
    Position globalBest;
    double globalBestFitness;
    
    double inertiaWeight;
    double cognitiveWeight;
    double socialWeight;
    
    std::mt19937 rng;
    
public:
    SwarmOptimizer(int numParticles, double inertia = 0.7, double cognitive = 1.5, double social = 1.5)
        : inertiaWeight(inertia), cognitiveWeight(cognitive), socialWeight(social),
          globalBestFitness(std::numeric_limits<double>::max()) {
        
        std::random_device rd;
        rng = std::mt19937(rd());
        
        std::uniform_real_distribution<double> distX(0, 500);
        std::uniform_real_distribution<double> distY(0, 500);
        std::uniform_real_distribution<double> distZ(10, 100);
        
        for (int i = 0; i < numParticles; i++) {
            Position start = {distX(rng), distY(rng), distZ(rng)};
            double fitness = evaluateFitness(start);
            particles.emplace_back(start, fitness);
            
            if (fitness < globalBestFitness) {
                globalBestFitness = fitness;
                globalBest = start;
            }
        }
    }
    
    double evaluateFitness(const Position& pos) {
        double distanceScore = pos.distanceTo({250, 250, 50});
        
        double obstaclePenalty = 0;
        double centerDist = std::sqrt(std::pow(pos.x - 250, 2) + std::pow(pos.y - 250, 2));
        if (centerDist < 50) {
            obstaclePenalty = 1000;
        }
        
        double energyCost = pos.z * 0.1;
        
        return distanceScore + obstaclePenalty + energyCost;
    }
    
    void updateVelocity(Particle& p) {
        std::uniform_real_distribution<double> dist(0, 1);
        
        double r1 = dist(rng);
        double r2 = dist(rng);
        
        Position cognitive = (p.bestPosition - p.position) * cognitiveWeight * r1;
        Position social = (globalBest - p.position) * socialWeight * r2;
        Position inertia = p.velocity * inertiaWeight;
        
        p.velocity = inertia + cognitive + social;
        
        double maxVel = 50.0;
        double velMag = std::sqrt(p.velocity.x*p.velocity.x + 
                                   p.velocity.y*p.velocity.y + 
                                   p.velocity.z*p.velocity.z);
        if (velMag > maxVel) {
            p.velocity = p.velocity * (maxVel / velMag);
        }
    }
    
    void updatePosition(Particle& p) {
        p.position = p.position + p.velocity;
        
        p.position.x = std::max(0.0, std::min(500.0, p.position.x));
        p.position.y = std::max(0.0, std::min(500.0, p.position.y));
        p.position.z = std::max(10.0, std::min(100.0, p.position.z));
        
        p.fitness = evaluateFitness(p.position);
        
        if (p.fitness < p.bestFitness) {
            p.bestFitness = p.fitness;
            p.bestPosition = p.position;
            
            if (p.fitness < globalBestFitness) {
                globalBestFitness = p.fitness;
                globalBest = p.position;
            }
        }
    }
    
    Position optimize(int maxIterations) {
        #pragma omp parallel
        {
            #pragma omp for
            for (int iter = 0; iter < maxIterations; iter++) {
                for (auto& p : particles) {
                    updateVelocity(p);
                    updatePosition(p);
                }
            }
        }
        
        return globalBest;
    }
    
    Position getBestPosition() const { return globalBest; }
    double getBestFitness() const { return globalBestFitness; }
};

class MultiObjectiveSwarm {
public:
    struct Objective {
        double distance;
        double energy;
        double safety;
    };
    
    static Objective evaluatePath(const std::vector<Position>& path) {
        double totalDistance = 0;
        for (size_t i = 1; i < path.size(); i++) {
            totalDistance += path[i-1].distanceTo(path[i]);
        }
        
        double totalEnergy = 0;
        for (const auto& pos : path) {
            totalEnergy += pos.z * 0.1;
        }
        
        double minObstacleDist = std::numeric_limits<double>::max();
        for (const auto& pos : path) {
            double centerDist = std::sqrt(std::pow(pos.x - 250, 2) + std::pow(pos.y - 250, 2));
            if (centerDist < 50) {
                minObstacleDist = std::min(minObstacleDist, 50 - centerDist);
            }
        }
        
        return {totalDistance, totalEnergy, minObstacleDist};
    }
};

int main() {
    std::cout << "=== SDACS Swarm Intelligence (C++) ===" << std::endl;
    std::cout << "Particle Swarm Optimization for Drone Path Planning" << std::endl;
    std::cout << "OpenMP enabled: " << omp_get_max_threads() << " threads" << std::endl;
    
    int numParticles = 50;
    int maxIterations = 100;
    
    SwarmOptimizer swarm(numParticles);
    
    std::cout << "\nInitial best fitness: " << swarm.getBestFitness() << std::endl;
    
    Position optimal = swarm.optimize(maxIterations);
    
    std::cout << "\n=== Optimization Results ===" << std::endl;
    std::cout << "Best position: (" << optimal.x << ", " << optimal.y << ", " << optimal.z << ")" << std::endl;
    std::cout << "Best fitness: " << swarm.getBestFitness() << std::endl;
    
    std::vector<Position> testPath = {
        {0, 0, 30},
        {100, 100, 40},
        {200, 200, 50},
        {250, 250, 50},
        {300, 300, 40},
        {400, 400, 30}
    };
    
    auto objectives = MultiObjectiveSwarm::evaluatePath(testPath);
    std::cout << "\n=== Test Path Evaluation ===" << std::endl;
    std::cout << "Distance: " << objectives.distance << "m" << std::endl;
    std::cout << "Energy: " << objectives.energy << "Wh" << std::endl;
    std::cout << "Safety margin: " << objectives.safety << "m" << std::endl;
    
    return 0;
}
