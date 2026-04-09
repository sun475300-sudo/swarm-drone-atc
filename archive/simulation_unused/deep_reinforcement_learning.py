"""
Deep Reinforcement Learning Controller
Phase 270 P0 - Advanced DRL for autonomous drone control
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random


@dataclass
class DroneState:
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    battery: float
    nearby_drones: List[str] = field(default_factory=list)
    target_position: Optional[Tuple[float, float, float]] = None


@dataclass
class DroneAction:
    dx: float
    dy: float
    dz: float
    speed_factor: float = 1.0


class ReplayBuffer:
    def __init__(self, capacity: int = 100000):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, state, action, reward, next_state, done):
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int):
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self):
        return len(self.buffer)


class NeuralNetwork:
    def __init__(
        self, input_dim: int, output_dim: int, hidden_dims: List[int] = [256, 256]
    ):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dims = hidden_dims

        layer_dims = [input_dim] + hidden_dims + [output_dim]
        self.weights = []
        self.biases = []

        for i in range(len(layer_dims) - 1):
            w = np.random.randn(layer_dims[i], layer_dims[i + 1]) * np.sqrt(
                2.0 / layer_dims[i]
            )
            b = np.zeros(layer_dims[i + 1])
            self.weights.append(w)
            self.biases.append(b)

    def forward(self, x: np.ndarray) -> np.ndarray:
        activation = x
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            activation = np.dot(activation, w) + b
            if i < len(self.weights) - 1:
                activation = np.relu(activation)
        return activation

    def get_action(self, state: np.ndarray) -> np.ndarray:
        q_values = self.forward(state)
        return q_values


class DRLAgent:
    def __init__(self, state_dim: int, action_dim: int):
        self.state_dim = state_dim
        self.action_dim = action_dim

        self.policy_net = NeuralNetwork(state_dim, action_dim)
        self.target_net = NeuralNetwork(state_dim, action_dim)
        self.target_net.weights = [w.copy() for w in self.policy_net.weights]
        self.target_net.biases = [b.copy() for b in self.policy_net.biases]

        self.replay_buffer = ReplayBuffer()
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.learning_rate = 0.001
        self.target_update_freq = 1000
        self.training_step = 0

    def select_action(self, state: np.ndarray, training: bool = True) -> np.ndarray:
        if training and random.random() < self.epsilon:
            action = np.random.uniform(-1, 1, self.action_dim)
        else:
            q_values = self.policy_net.forward(state)
            action = q_values / (np.linalg.norm(q_values) + 1e-8)

        return action

    def store_transition(self, state, action, reward, next_state, done):
        self.replay_buffer.push(state, action, reward, next_state, done)

    def train(self, batch_size: int = 64):
        if len(self.replay_buffer) < batch_size:
            return 0.0

        batch = self.replay_buffer.sample(batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = np.array(states)
        actions = np.array(actions)
        rewards = np.array(rewards)
        next_states = np.array(next_states)
        dones = np.array(dones)

        current_q = self.policy_net.forward(states)
        next_q = self.target_net.forward(next_states)
        max_next_q = np.max(next_q, axis=1)

        target_q = rewards + (1 - dones) * self.gamma * max_next_q

        loss = np.mean((current_q - target_q) ** 2)

        self.training_step += 1
        if self.training_step % self.target_update_freq == 0:
            self.update_target_network()

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return loss

    def update_target_network(self):
        self.target_net.weights = [
            w.copy() * 0.01 + self.policy_net.weights[i] * 0.99
            for i, w in enumerate(self.policy_net.weights)
        ]
        self.target_net.biases = [
            b.copy() * 0.01 + self.policy_net.biases[i] * 0.99
            for i, b in enumerate(self.policy_net.biases)
        ]


class DroneControlEnv:
    def __init__(self, num_drones: int = 10, workspace_size: float = 500.0):
        self.num_drones = num_drones
        self.workspace_size = workspace_size
        self.drones: Dict[str, DroneState] = {}
        self.targets: Dict[str, Tuple[float, float, float]] = {}
        self.obstacles: List[Tuple[float, float, float, float]] = []
        self.time_step = 0

        self._init_drones()

    def _init_drones(self):
        for i in range(self.num_drones):
            drone_id = f"DRL-DRONE-{i + 1:03d}"
            pos = (
                np.random.uniform(0, self.workspace_size),
                np.random.uniform(0, self.workspace_size),
                np.random.uniform(20, 80),
            )
            vel = (0.0, 0.0, 0.0)
            battery = np.random.uniform(50, 100)

            self.drones[drone_id] = DroneState(pos, vel, battery)

            target = (
                np.random.uniform(0, self.workspace_size),
                np.random.uniform(0, self.workspace_size),
                np.random.uniform(20, 80),
            )
            self.targets[drone_id] = target

    def _get_state(self, drone_id: str) -> np.ndarray:
        drone = self.drones[drone_id]
        target = self.targets.get(drone_id, (250, 250, 50))

        dx = target[0] - drone.position[0]
        dy = target[1] - drone.position[1]
        dz = target[2] - drone.position[2]
        dist_to_target = np.sqrt(dx**2 + dy**2 + dz**2)

        state = np.array(
            [
                drone.position[0] / self.workspace_size,
                drone.position[1] / self.workspace_size,
                drone.position[2] / 100.0,
                drone.velocity[0] / 20.0,
                drone.velocity[1] / 20.0,
                drone.velocity[2] / 20.0,
                drone.battery / 100.0,
                dx / self.workspace_size,
                dy / self.workspace_size,
                dz / 100.0,
                dist_to_target / self.workspace_size,
                self.time_step / 1000.0,
            ]
        )

        return state

    def _get_reward(self, drone_id: str, action: DroneAction) -> float:
        drone = self.drones[drone_id]
        target = self.targets.get(drone_id, (250, 250, 50))

        dx = target[0] - drone.position[0]
        dy = target[1] - drone.position[1]
        dz = target[2] - drone.position[2]
        dist_before = np.sqrt(dx**2 + dy**2 + dz**2)

        reward = -0.1

        if drone.battery < 20:
            reward -= 10.0

        return reward

    def step(self, actions: Dict[str, DroneAction]) -> Dict[str, np.ndarray]:
        self.time_step += 1
        observations = {}
        rewards = {}
        dones = {}

        for drone_id, action in actions.items():
            if drone_id not in self.drones:
                continue

            drone = self.drones[drone_id]
            target = self.targets.get(drone_id, (250, 250, 50))

            new_pos = (
                drone.position[0] + action.dx * action.speed_factor,
                drone.position[1] + action.dy * action.speed_factor,
                drone.position[2] + action.dz * action.speed_factor,
            )

            new_pos = (
                np.clip(new_pos[0], 0, self.workspace_size),
                np.clip(new_pos[1], 0, self.workspace_size),
                np.clip(new_pos[2], 10, 100),
            )

            dx = target[0] - new_pos[0]
            dy = target[1] - new_pos[1]
            dz = target[2] - new_pos[2]
            dist = np.sqrt(dx**2 + dy**2 + dz**2)

            new_vel = (
                action.dx * action.speed_factor,
                action.dy * action.speed_factor,
                action.dz * action.speed_factor,
            )

            battery_consumption = (
                np.linalg.norm([action.dx, action.dy, action.dz]) * 0.01
            )

            drone.position = new_pos
            drone.velocity = new_vel
            drone.battery = max(0, drone.battery - battery_consumption)

            observations[drone_id] = self._get_state(drone_id)
            rewards[drone_id] = self._get_reward(drone_id, action)
            dones[drone_id] = dist < 10 or drone.battery <= 0

        return {"observations": observations, "rewards": rewards, "dones": dones}

    def reset(self):
        self.time_step = 0
        self._init_drones()
        return {drone_id: self._get_state(drone_id) for drone_id in self.drones}


class DRLController:
    def __init__(self, num_agents: int = 10):
        self.env = DroneControlEnv(num_agents)
        self.agents: Dict[str, DRLAgent] = {}

        for drone_id in self.env.drones.keys():
            state_dim = 12
            action_dim = 4
            self.agents[drone_id] = DRLAgent(state_dim, action_dim)

    def train(self, num_episodes: int = 1000, max_steps: int = 500):
        episode_rewards = []

        for episode in range(num_episodes):
            states = self.env.reset()
            episode_reward = 0

            for step in range(max_steps):
                actions = {}

                for drone_id, state in states.items():
                    action = self.agents[drone_id].select_action(state)
                    actions[drone_id] = DroneAction(
                        dx=action[0] * 10,
                        dy=action[1] * 10,
                        dz=action[2] * 5,
                        speed_factor=action[3] + 1,
                    )

                results = self.env.step(actions)

                for drone_id in states.keys():
                    state = states[drone_id]
                    action = actions[drone_id]
                    reward = results["rewards"].get(drone_id, 0)
                    next_state = results["observations"].get(drone_id, state)
                    done = results["dones"].get(drone_id, False)

                    self.agents[drone_id].store_transition(
                        state, action, reward, next_state, done
                    )

                    loss = self.agents[drone_id].train(batch_size=32)

                    episode_reward += reward
                    states[drone_id] = next_state

                if all(results["dones"].values()):
                    break

            episode_rewards.append(episode_reward)

            if episode % 10 == 0:
                avg_reward = np.mean(episode_rewards[-10:])
                print(
                    f"Episode {episode}: Avg Reward = {avg_reward:.2f}, Epsilon = {self.agents[drone_id].epsilon:.3f}"
                )

        return episode_rewards

    def evaluate(self, num_episodes: int = 10):
        eval_rewards = []

        for episode in range(num_episodes):
            states = self.env.reset()
            episode_reward = 0

            for step in range(500):
                actions = {}

                for drone_id, state in states.items():
                    action = self.agents[drone_id].select_action(state, training=False)
                    actions[drone_id] = DroneAction(
                        dx=action[0] * 10,
                        dy=action[1] * 10,
                        dz=action[2] * 5,
                        speed_factor=action[3] + 1,
                    )

                results = self.env.step(actions)

                for drone_id in states.keys():
                    episode_reward += results["rewards"].get(drone_id, 0)
                    states[drone_id] = results["observations"].get(
                        drone_id, states[drone_id]
                    )

                if all(results["dones"].values()):
                    break

            eval_rewards.append(episode_reward)

        return np.mean(eval_rewards), np.std(eval_rewards)


def create_drl_controller(num_drones: int = 10) -> DRLController:
    controller = DRLController(num_drones)
    return controller


if __name__ == "__main__":
    print("=== Deep Reinforcement Learning Controller ===")
    controller = create_drl_controller(5)

    print("\nTraining DRL agents...")
    rewards = controller.train(num_episodes=50, max_steps=100)

    print("\nEvaluating trained agents...")
    mean_reward, std_reward = controller.evaluate(num_episodes=5)
    print(f"Evaluation: Mean Reward = {mean_reward:.2f} +/- {std_reward:.2f}")
