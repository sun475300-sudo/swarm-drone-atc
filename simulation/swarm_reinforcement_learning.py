"""
Multi-Agent Swarm Reinforcement Learning
Phase 353 - MAPPO, QMIX, CTDE for drone swarm coordination
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import random


@dataclass
class AgentState:
    agent_id: str
    position: np.ndarray
    velocity: np.ndarray
    observations: np.ndarray = field(default_factory=lambda: np.zeros(10))
    last_action: Optional[np.ndarray] = None
    reward: float = 0.0


@dataclass
class JointAction:
    actions: Dict[str, np.ndarray]


class ReplayBuffer:
    def __init__(self, capacity: int = 100000):
        self.capacity = capacity
        self.buffer: List[Dict] = []
        self.position = 0

    def push(self, data: Dict):
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = data
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Dict]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self):
        return len(self.buffer)


class NeuralNetwork:
    def __init__(
        self, input_dim: int, output_dim: int, hidden_dims: List[int] = [128, 128]
    ):
        self.layers = []
        dims = [input_dim] + hidden_dims + [output_dim]

        for i in range(len(dims) - 1):
            w = np.random.randn(dims[i], dims[i + 1]) * np.sqrt(2.0 / dims[i])
            b = np.zeros(dims[i + 1])
            self.layers.append((w, b))

    def forward(self, x: np.ndarray) -> np.ndarray:
        for i, (w, b) in enumerate(self.layers):
            x = x @ w + b
            if i < len(self.layers) - 1:
                x = np.tanh(x)
        return x

    def get_action(self, state: np.ndarray) -> np.ndarray:
        q_values = self.forward(state)
        return np.argmax(q_values)


class PPOAgent:
    def __init__(self, agent_id: str, obs_dim: int, action_dim: int):
        self.agent_id = agent_id
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        self.policy = NeuralNetwork(obs_dim, action_dim)
        self.value = NeuralNetwork(obs_dim, 1)
        self.gamma = 0.99
        self.epsilon = 0.2
        self.learning_rate = 0.0003
        self.buffer = ReplayBuffer()

    def get_action(
        self, obs: np.ndarray, deterministic: bool = False
    ) -> Tuple[np.ndarray, float]:
        action_idx = self.policy.get_action(obs.reshape(1, -1))[0]
        action = np.zeros(self.action_dim)
        action[action_idx] = 1.0

        log_prob = np.log(action[action_idx] + 1e-8)
        value = self.value.forward(obs.reshape(1, -1))[0, 0]

        return action, log_prob, value

    def update(self, batch: Dict) -> float:
        states = batch["observations"]
        actions = batch["actions"]
        old_log_probs = batch["log_probs"]
        rewards = batch["rewards"]
        dones = batch["dones"]

        returns = []
        discounted = 0
        for r, done in zip(reversed(rewards), reversed(dones)):
            discounted = r + self.gamma * discounted * (1 - done)
            returns.insert(0, discounted)
        returns = np.array(returns)

        returns = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)

        loss = np.mean((returns - np.mean(returns)) ** 2)
        return loss


class MAPPO:
    def __init__(self, num_agents: int, obs_dim: int, action_dim: int):
        self.num_agents = num_agents
        self.agents: Dict[str, PPOAgent] = {}

        for i in range(num_agents):
            agent_id = f"drone_{i}"
            self.agents[agent_id] = PPOAgent(agent_id, obs_dim, action_dim)

    def get_joint_action(
        self, observations: Dict[str, np.ndarray], deterministic: bool = False
    ) -> Dict[str, np.ndarray]:
        joint_action = {}
        for agent_id, obs in observations.items():
            action, _, _ = self.agents[agent_id].get_action(obs, deterministic)
            joint_action[agent_id] = action
        return joint_action

    def update(self, batch: Dict) -> Dict[str, float]:
        losses = {}
        for agent_id in self.agents:
            if agent_id in batch["agent_ids"]:
                losses[agent_id] = self.agents[agent_id].update(batch)
        return losses


class QMIX:
    def __init__(self, num_agents: int, obs_dim: int, action_dim: int):
        self.num_agents = num_agents
        self.agents: Dict[str, PPOAgent] = {}

        self.q_mixer = NeuralNetwork(num_agents, 1, [64, 32])

        for i in range(num_agents):
            agent_id = f"drone_{i}"
            self.agents[agent_id] = PPOAgent(agent_id, obs_dim, action_dim)

    def mix_q_values(self, q_values: np.ndarray) -> float:
        return self.q_mixer.forward(q_values.reshape(1, -1))[0, 0]

    def get_joint_action(
        self, observations: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        q_values = []
        joint_action = {}

        for agent_id, obs in observations.items():
            action, _, _ = self.agents[agent_id].get_action(obs)
            joint_action[agent_id] = action
            q_values.append(
                np.max(self.agents[agent_id].policy.forward(obs.reshape(1, -1)))
            )

        total_q = self.mix_q_values(np.array(q_values))
        return joint_action, total_q


class CTDEController:
    def __init__(self, num_agents: int = 10, obs_dim: int = 20, action_dim: int = 5):
        self.num_agents = num_agents
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        self.mappo = MAPPO(num_agents, obs_dim, action_dim)
        self.qmix = QMIX(num_agents, obs_dim, action_dim)

        self.global_state_dim = obs_dim * num_agents
        self.global_state = np.zeros(self.global_state_dim)

    def update_global_state(self, observations: Dict[str, np.ndarray]):
        states = []
        for agent_id in sorted(observations.keys()):
            states.extend(observations[agent_id])
        self.global_state = np.array(states)

    def train_step(self, experiences: List[Dict]) -> Dict[str, float]:
        batch = {
            "observations": [],
            "actions": [],
            "rewards": [],
            "dones": [],
            "log_probs": [],
            "agent_ids": [],
        }

        for exp in experiences:
            for agent_id, obs in exp["observations"].items():
                batch["observations"].append(obs)
                batch["actions"].append(exp["joint_actions"][agent_id])
                batch["rewards"].append(exp["reward"])
                batch["dones"].append(exp["done"])
                batch["log_probs"].append(0.0)
                batch["agent_ids"].append(agent_id)

        mappo_losses = self.mappo.update(batch)

        return mappo_losses


class SwarmEnvironment:
    def __init__(self, num_drones: int = 10, workspace_size: float = 100.0):
        self.num_drones = num_drones
        self.workspace_size = workspace_size
        self.drones: Dict[str, AgentState] = {}
        self.target_position = np.array([50.0, 50.0, 50.0])
        self.obstacles: List[np.ndarray] = []

        self._init_drones()

    def _init_drones(self):
        for i in range(self.num_drones):
            drone_id = f"drone_{i}"
            self.drones[drone_id] = AgentState(
                agent_id=drone_id,
                position=np.random.uniform(0, self.workspace_size, 3),
                velocity=np.zeros(3),
            )

    def reset(self) -> Dict[str, np.ndarray]:
        self._init_drones()
        return self._get_observations()

    def _get_observations(self) -> Dict[str, np.ndarray]:
        observations = {}
        for drone_id, drone in self.drones.items():
            rel_pos = drone.position - self.target_position
            distances = []
            for other_id, other in self.drones.items():
                if other_id != drone_id:
                    distances.append(np.linalg.norm(drone.position - other.position))

            obs = np.concatenate(
                [
                    drone.position / self.workspace_size,
                    drone.velocity / 10.0,
                    rel_pos / self.workspace_size,
                    [min(distances) / self.workspace_size] if distances else [1.0],
                ]
            )
            observations[drone_id] = obs
        return observations

    def step(
        self, joint_actions: Dict[str, np.ndarray]
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, float], bool]:
        rewards = {}

        for drone_id, drone in self.drones.items():
            action = joint_actions[drone_id]

            movement = (action[:3] - 0.5) * 2.0
            drone.position += movement
            drone.position = np.clip(drone.position, 0, self.workspace_size)

            dist_to_target = np.linalg.norm(drone.position - self.target_position)
            reward = -dist_to_target / self.workspace_size

            for other_id, other in self.drones.items():
                if other_id != drone_id:
                    dist = np.linalg.norm(drone.position - other.position)
                    if dist < 5.0:
                        reward -= 1.0

            rewards[drone_id] = reward

        observations = self._get_observations()

        total_reward = sum(rewards.values())
        done = all(
            np.linalg.norm(drone.position - self.target_position) < 10
            for drone in self.drones.values()
        )

        return observations, rewards, done


def train_swarm_rl(num_episodes: int = 100):
    env = SwarmEnvironment(num_drones=5)
    controller = CTDEController(num_agents=5)

    episode_rewards = []

    for episode in range(num_episodes):
        observations = env.reset()
        episode_reward = 0

        for step in range(100):
            joint_actions = controller.mappo.get_joint_action(observations)

            next_obs, rewards, done = env.step(joint_actions)

            experience = {
                "observations": observations,
                "joint_actions": joint_actions,
                "reward": sum(rewards.values()),
                "done": done,
            }

            episode_reward += sum(rewards.values())
            observations = next_obs

            if step % 10 == 0:
                controller.train_step([experience])

            if done:
                break

        episode_rewards.append(episode_reward)

        if episode % 10 == 0:
            avg_reward = np.mean(episode_rewards[-10:])
            print(f"Episode {episode}: Avg Reward = {avg_reward:.2f}")

    return episode_rewards


if __name__ == "__main__":
    print("=== Multi-Agent Swarm RL (MAPPO + QMIX + CTDE) ===")

    print("\nTraining swarm...")
    rewards = train_swarm_rl(num_episodes=50)

    print(f"\nFinal avg reward: {np.mean(rewards[-10:]):.2f}")
