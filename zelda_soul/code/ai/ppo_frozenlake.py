import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

# Hyperparameters
GAMMA = 0.99
LR = 1e-3
EPS_CLIP = 0.2
K_EPOCH = 3
T_HORIZON = 2000
HIDDEN_DIM = 128


# Neural Network for Policy and Value Approximation
class PPO(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(PPO, self).__init__()
        self.state_embedding = nn.Embedding(state_dim, HIDDEN_DIM)
        self.fc1 = nn.Linear(HIDDEN_DIM, HIDDEN_DIM)
        self.fc_pi = nn.Linear(HIDDEN_DIM, action_dim)
        self.fc_v = nn.Linear(HIDDEN_DIM, 1)
        self.relu = nn.ReLU()

    def pi(self, x, softmax_dim=0):
        x = self.relu(self.fc1(x))
        return torch.softmax(self.fc_pi(x), dim=softmax_dim)

    def v(self, x):
        x = self.relu(self.fc1(x))
        return self.fc_v(x)


# PPO Agent
class PPOAgent:
    def __init__(self, state_dim, action_dim):
        self.network = PPO(state_dim, action_dim)
        self.optimizer = optim.Adam(self.network.parameters(), lr=LR)
        self.data = []

    def put_data(self, transition):
        self.data.append(transition)

    def make_batch(self):
        s_lst, a_lst, r_lst, s_prime_lst, prob_a_lst, done_lst = [], [], [], [], [], []
        for transition in self.data:
            s, a, r, s_prime, prob_a, done = transition
            s_lst.append(s)
            a_lst.append([a])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
            prob_a_lst.append([prob_a])
            done_lst.append([0 if done else 1])

        s_batch = torch.tensor(s_lst, dtype=torch.long)  # State indices
        a_batch = torch.tensor(a_lst)
        r_batch = torch.tensor(r_lst, dtype=torch.float32)
        s_prime_batch = torch.tensor(s_prime_lst, dtype=torch.long)  # State indices
        prob_a_batch = torch.tensor(prob_a_lst, dtype=torch.float32)
        done_batch = torch.tensor(done_lst, dtype=torch.float32)

        self.data = []
        return s_batch, a_batch, r_batch, s_prime_batch, prob_a_batch, done_batch

    def train(self):
        s, a, r, s_prime, prob_a, done = self.make_batch()
        s_embedded = self.network.state_embedding(s)
        s_prime_embedded = self.network.state_embedding(s_prime)

        for _ in range(K_EPOCH):
            td_target = r + GAMMA * self.network.v(s_prime_embedded) * done
            delta = td_target - self.network.v(s_embedded)
            delta = delta.detach()

            advantage = torch.zeros_like(delta)
            for t in reversed(range(len(delta))):
                advantage[t] = delta[t] + (
                    GAMMA * advantage[t + 1] if t + 1 < len(delta) else 0
                )

            pi = self.network.pi(s_embedded, softmax_dim=1)
            pi_a = pi.gather(1, a)
            ratio = torch.exp(torch.log(pi_a) - torch.log(prob_a))

            surr1 = ratio * advantage
            surr2 = torch.clamp(ratio, 1 - EPS_CLIP, 1 + EPS_CLIP) * advantage
            loss = -torch.min(surr1, surr2).mean() + nn.functional.mse_loss(
                self.network.v(s_embedded), td_target.detach()
            )

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()


# Environment Setup
env = gym.make("FrozenLake-v1", is_slippery=True, render_mode=None)
state_dim = env.observation_space.n
action_dim = env.action_space.n

# Training Loop
agent = PPOAgent(state_dim, action_dim)
score = 0.0

for n_episode in range(10000):
    state, _ = env.reset()
    done = False

    while not done:
        state_tensor = torch.tensor([state], dtype=torch.long)
        state_embedded = agent.network.state_embedding(state_tensor).squeeze(0)

        prob = agent.network.pi(state_embedded)
        dist = Categorical(prob)
        action = dist.sample().item()

        next_state, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated

        agent.put_data(
            (state, action, reward, next_state, prob[action].detach().item(), done)
        )
        state = next_state
        score += reward

    if n_episode % 20 == 0 and n_episode > 0:
        agent.train()
        print(f"Episode {n_episode}, Avg Score: {score / 20}")
        score = 0.0

env.close()
