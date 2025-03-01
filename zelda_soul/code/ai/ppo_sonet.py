import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from environment.env import Environment, EnvironmentConfig
import torch.nn as nn


class PPOMemory:
    def __init__(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.probs = []
        self.values = []
        self.dones = []

    def clear(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.probs = []
        self.values = []
        self.dones = []

    def store(self, state, action, reward, prob, value, done):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.probs.append(prob)
        self.values.append(value)
        self.dones.append(done)


class ActorCritic(nn.Module):
    def __init__(
        self, input_dim, n_actions, embedding_dim=8, conv_channels=16, output_dim=64
    ):
        super(ActorCritic, self).__init__()

        # Embedding for 4 possible values
        self.embedding = nn.Embedding(num_embeddings=4, embedding_dim=embedding_dim)

        # Convolutional layers
        # self.conv = nn.Sequential(
        #     nn.Conv2d(
        #         in_channels=embedding_dim,
        #         out_channels=conv_channels,
        #         kernel_size=3,
        #         stride=1,
        #         padding=1,
        #     ),
        #     nn.ReLU(),
        #     nn.Conv2d(
        #         in_channels=conv_channels,
        #         out_channels=conv_channels * 2,
        #         kernel_size=3,
        #         stride=1,
        #         padding=1,
        #     ),
        #     nn.ReLU(),
        #     # nn.MaxPool2d(kernel_size=2, stride=2),  # Reduces to 2x2 spatial size
        # )

        # Fully connected layers
        self.shared = nn.Sequential(
            nn.Flatten(),
            nn.Linear(
                embedding_dim * input_dim * input_dim, output_dim
            ),  # Adjust based on pooled size
            nn.ReLU(),
            nn.Linear(output_dim, output_dim),  # Output dimension for the encoding
        )

        # Actor (Policy) head
        self.actor = nn.Sequential(nn.Linear(output_dim, n_actions), nn.Softmax(dim=-1))

        # Critic (Value) head
        self.critic = nn.Sequential(nn.Linear(output_dim, 1))

    def forward(self, state):
        # Input shape: (batch_size, 5, 5)
        x = self.embedding(state)  # Shape: (batch_size, 5, 5, embedding_dim)
        # x = x.permute(0, 3, 1, 2)  # Shape: (batch_size, embedding_dim, 5, 5)
        # x = self.conv(x)  # Shape: (batch_size, conv_channels * 2, 2, 2)
        features = self.shared(x)  # Shape: (batch_size, output_dim)
        action_probs = self.actor(features)
        value = self.critic(features)
        return action_probs, value


class PPOAgent:
    def __init__(
        self,
        input_dim,
        n_actions,
        lr=0.0001,
        gamma=0.99,
        clip_epsilon=0.15,
        n_epochs=10,
        batch_size=32,
    ):
        self.gamma = gamma
        self.clip_epsilon = clip_epsilon
        self.n_epochs = n_epochs
        self.batch_size = batch_size

        self.actor_critic = ActorCritic(input_dim, n_actions)
        self.optimizer = optim.Adam(self.actor_critic.parameters(), lr=lr)
        self.memory = PPOMemory()

    def choose_action(self, state):
        state = torch.LongTensor(state).unsqueeze(0)

        with torch.no_grad():
            action_probs, value = self.actor_critic(state)

        dist = Categorical(action_probs)
        action = dist.sample()

        return action.item(), action_probs[0][action.item()].item(), value.item()

    def learn(self):
        states = torch.LongTensor(np.array(self.memory.states))
        actions = torch.LongTensor(np.array(self.memory.actions))
        old_probs = torch.FloatTensor(np.array(self.memory.probs))
        values = torch.FloatTensor(np.array(self.memory.values))

        # Calculate advantages
        rewards = []
        discounted_reward = 0
        for reward, done in zip(
            reversed(self.memory.rewards), reversed(self.memory.dones)
        ):
            if done:
                discounted_reward = 0
            discounted_reward = reward + (self.gamma * discounted_reward)
            rewards.insert(0, discounted_reward)

        rewards = torch.FloatTensor(rewards)
        rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-8)
        advantages = rewards - values

        # Update policy
        for _ in range(self.n_epochs):
            action_probs, critic_value = self.actor_critic(states)
            dist = Categorical(action_probs)
            new_probs = dist.log_prob(actions)

            # Policy loss
            ratio = torch.exp(new_probs - torch.log(old_probs))
            surr1 = ratio * advantages
            surr2 = (
                torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
                * advantages
            )
            actor_loss = -torch.min(surr1, surr2).mean()

            # Value loss
            critic_loss = nn.MSELoss()(critic_value.squeeze(), rewards)

            # entropy loss
            entropy_loss = -0.01 * dist.entropy().mean()

            # Total loss
            total_loss = actor_loss + 0.5 * critic_loss + entropy_loss

            # Update network
            self.optimizer.zero_grad()
            total_loss.backward()
            self.optimizer.step()

        self.memory.clear()


def train():
    # env = gym.make('CartPole-v1', render_mode=None)
    config = EnvironmentConfig()
    env = Environment(config)
    input_dim = len(env.observation())
    n_actions = len(env.int_to_action)

    agent = PPOAgent(input_dim=input_dim, n_actions=n_actions)
    n_episodes = 100000
    max_steps = 500
    best_reward = float("-inf")

    for episode in range(n_episodes):
        state, _ = env.reset()
        episode_reward = 0

        for step in range(max_steps):
            action, prob, value = agent.choose_action(state)
            next_state, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated

            # debug
            # env.render()
            # print(env.int_to_action[action]," ", reward)
            # print(env.player.stats)

            state = next_state
            episode_reward += reward
            agent.memory.store(state, action, reward, prob, value, done)

            if done:
                break

        agent.learn()

        if episode % 20 == 0:
            print(f"Episode {episode}, Reward: {episode_reward}")

            if episode_reward > best_reward:
                best_reward = episode_reward
                torch.save(agent.actor_critic.state_dict(), "best_model.pth")
                print(f"Best model saved. Episode: {episode}, Reward: {episode_reward}")

    return agent


def run(agent):
    env = Environment()
    obs = env.reset()
    done = False

    n_episodes = 100
    for _ in range(n_episodes):
        obs, info = env.reset()
        done = False
        while not done:
            action, prob, value = agent.choose_action(obs)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            env.render()

    env.close()


if __name__ == "__main__":
    agent = train()
    run(agent)
