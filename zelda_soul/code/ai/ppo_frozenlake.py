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
        self.fc1 = nn.Linear(state_dim, HIDDEN_DIM)
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

        s_batch = torch.tensor(s_lst, dtype=torch.float32)
        a_batch = torch.tensor(a_lst)
        r_batch = torch.tensor(r_lst, dtype=torch.float32)
        s_prime_batch = torch.tensor(s_prime_lst, dtype=torch.float32)
        prob_a_batch = torch.tensor(prob_a_lst, dtype=torch.float32)
        done_batch = torch.tensor(done_lst, dtype=torch.float32)

        self.data = []
        return s_batch, a_batch, r_batch, s_prime_batch, prob_a_batch, done_batch

    def train(self):
        s, a, r, s_prime, prob_a, done = self.make_batch()
        for _ in range(K_EPOCH):
            td_target = r + GAMMA * self.network.v(s_prime) * done
            delta = td_target - self.network.v(s)
            delta = delta.detach().numpy()

            advantage_lst = []
            advantage = 0.0
            for delta_t in delta[::-1]:
                advantage = GAMMA * advantage + delta_t[0]
                advantage_lst.append([advantage])
            advantage_lst.reverse()
            advantage = torch.tensor(advantage_lst, dtype=torch.float32)

            pi = self.network.pi(s, softmax_dim=1)
            pi_a = pi.gather(1, a)
            ratio = torch.exp(torch.log(pi_a) - torch.log(prob_a))

            surr1 = ratio * advantage
            surr2 = torch.clamp(ratio, 1 - EPS_CLIP, 1 + EPS_CLIP) * advantage
            loss = -torch.min(surr1, surr2) + nn.functional.mse_loss(self.network.v(s), td_target.detach())

            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()

# Environment Setup
env = gym.make('FrozenLake-v1', is_slippery=True, render_mode=None)
state_dim = env.observation_space.n
action_dim = env.action_space.n

# Convert discrete state into one-hot encoded vectors
def one_hot(state, state_dim):
    state_vector = np.zeros(state_dim)
    state_vector[state] = 1
    return state_vector

# Training Loop
agent = PPOAgent(state_dim, action_dim)
score = 0.0

for n_episode in range(1000):
    state, _ = env.reset()
    state = one_hot(state, state_dim)
    done = False

    while not done:
        prob = agent.network.pi(torch.from_numpy(state).float())
        dist = Categorical(prob)
        action = dist.sample().item()
        next_state, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated

        next_state_one_hot = one_hot(next_state, state_dim)
        agent.put_data((state, action, reward, next_state_one_hot, prob[action].item(), done))
        state = next_state_one_hot
        score += reward

    if n_episode % 20 == 0 and n_episode > 0:
        print(f"Episode {n_episode}, Avg Score: {score / 20}")
        score = 0.0
        agent.train()

env.close()