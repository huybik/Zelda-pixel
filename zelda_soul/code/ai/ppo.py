import gymnasium as gym
import numpy as np
from tqdm import tqdm
import torch
from torch import nn
from torch.optim import AdamW
from torch.utils.tensorboard import SummaryWriter
import torch.nn.functional as F


class PolicyNet(nn.Module):
    def __init__(self, nvec_s: int, nvec_u: int):
        super(PolicyNet, self).__init__()  # this for nn modules
        self.fc1 = nn.Linear(nvec_s, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, nvec_u)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        dist = torch.distributions.Categorical(logits=x)
        # sample index from output probabilities, similar to softmax
        action = dist.sample()
        # entropy of distribution
        entropy = dist.entropy()
        log_prob = dist.log_prob(action)
        return action, log_prob, entropy


class ValueNet(nn.Module):
    def __init__(self, n_features, n_hidden):
        super(ValueNet, self).__init__()
        self.fc1 = nn.Linear(n_features, n_hidden)
        self.fc2 = nn.Linear(n_hidden, int(n_hidden / 2))
        self.fc3 = nn.Linear(int(n_hidden / 2), 1)

    def forward(self, x) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)


env = gym.make("CartPole-v1", render_mode="human")


class Reinforce:
    def __init__(self, env: gym.Env, lr, gamma, n_steps):

        self.env = env
        self.lr = lr
        self.gamma = gamma
        self.n_steps = n_steps

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.policy_net = PolicyNet(
            env.observation_space.shape[0], env.action_space.n
        ).to(self.device)
        self.optimizer_policy = AdamW(self.policy_net.parameters(), lr=lr)

        self.value_net = ValueNet(env.observation_space.shape[0], 256).to(self.device)
        self.optimizer_value = AdamW(self.value_net.parameters(), lr=lr)

        self.total_steps = 0

        # stats
        self.episodes = 0
        self.total_rewards = 0
        self.mean_episode_reward = 0
        self.clip_epsilon = 0.2

    def rollout(self):

        state, info = self.env.reset()
        terminated = False
        truncated = False
        self.log_probs = []
        self.rewards = []
        self.entropies = []
        self.values = []
        self.old_probs = None

        while True:

            # policy net
            action, log_prob, entropy = self.policy_net(
                torch.from_numpy(state).float().to(self.device)
            )
            next_state, reward, terminated, truncated, _ = self.env.step(action.item())

            self.rewards.append(reward)
            self.log_probs.append(log_prob)
            self.entropies.append(entropy)

            # value net
            value = self.value_net(torch.from_numpy(state).float().to(self.device))
            self.values.append(value)

            state = next_state

            self.total_rewards += reward
            self.total_steps += 1
            self.pbar.update(1)

            if terminated or truncated:
                self.episodes += 1
                if self.episodes % 10 == 0:
                    self.mean_episode_reward = self.total_rewards / self.episodes
                    self.pbar.set_description(
                        f"Reward: {self.mean_episode_reward :.3f}"
                    )
                    self.writer.add_scalar(
                        "Reward", self.mean_episode_reward, self.total_steps
                    )
                    self.episodes = 0
                    self.total_rewards = 0

                return self.mean_episode_reward
                break

    def calculate_returns(self):

        next_returns = 0
        returns = np.zeros_like(self.rewards, dtype=np.float32)
        for i in reversed(range(len(self.rewards))):
            next_returns = self.rewards[i] + self.gamma * next_returns
            returns[i] = next_returns

        # Convert to tensor
        returns = torch.tensor(returns, dtype=torch.float32, device=self.device)

        # Normalize returns
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)

        return returns

    def learn(self):

        self.log_probs = torch.stack(self.log_probs)
        self.entropies = torch.stack(self.entropies)
        self.values = torch.stack(self.values)
        if not self.old_probs:
            self.old_probs = self.log_probs.detach()

        returns = self.calculate_returns()
        advantages = returns.squeeze() - self.values

        # ppo
        ratios = torch.exp(self.log_probs - self.old_probs)
        surr1 = ratios * advantages.detach()
        surr2 = (
            torch.clamp(ratios, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
            * advantages.detach()
        )
        policy_loss = -torch.min(surr1, surr2).mean()

        # policy_loss = -torch.mean(advantages.detach() * self.log_probs)

        entropy_loss = -torch.mean(self.entropies)
        policy_loss = policy_loss + 0.001 * entropy_loss

        self.value_loss = F.mse_loss(self.values.squeeze(), returns)

        total_loss = policy_loss + 0.5 * self.value_loss
        # optimize policy net
        self.optimizer_policy.zero_grad()
        self.optimizer_value.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1)
        torch.nn.utils.clip_grad_norm_(self.value_net.parameters(), 1)

        self.optimizer_policy.step()

        self.optimizer_value.step()

        # update old probs
        self.old_probs = self.log_probs.detach()

    def train(self):
        self.writer = SummaryWriter(
            log_dir="runs/reinforce_logs/REINFORCE_WITH_BASELINE"
        )

        self.pbar = tqdm(total=self.n_steps, position=0, leave=True)
        while self.total_steps < self.n_steps:
            if self.rollout() >= 500:
                # early stopping when solved the game
                break
            # self.rollout()
            self.learn()


def main():
    env = gym.make("CartPole-v1")
    agent = Reinforce(env, 0.0005, 0.99, 400000)
    agent.train()

    env = gym.make("CartPole-v1", render_mode="human")

    n_episodes = 100
    for _ in range(n_episodes):
        obs, info = env.reset()
        terminated = False
        truncated = False
        while not terminated:
            with torch.no_grad():
                action = agent.policy_net(
                    torch.from_numpy(obs).float().to(agent.device)
                )[0].item()
                obs, reward, terminated, truncated, info = env.step(action)
                env.render()


if __name__ == "__main__":
    main()
# observation space
# action space


def calculate_kl_divergence(old_probs, new_probs):
    kl_div = torch.sum(
        old_probs * (torch.log(old_probs) - torch.log(new_probs)), dim=-1
    )
    return kl_div.mean()
