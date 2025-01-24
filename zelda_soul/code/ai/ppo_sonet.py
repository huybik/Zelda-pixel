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
    def __init__(self, input_dim, n_actions):
        super(ActorCritic, self).__init__()
        
        # Shared features
        self.shared = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU()
        )
        
        # Actor (Policy) head
        self.actor = nn.Sequential(
            nn.Linear(64, n_actions),
            nn.Softmax(dim=-1)
        )
        
        # Critic (Value) head
        self.critic = nn.Sequential(
            nn.Linear(64, 1)
        )
    
    def forward(self, state):
        features = self.shared(state)
        action_probs = self.actor(features)
        value = self.critic(features)
        return action_probs, value

class PPOAgent:
    def __init__(self, input_dim, n_actions, lr=0.0003, gamma=0.99, clip_epsilon=0.2, 
                 n_epochs=10, batch_size=32):
        self.gamma = gamma
        self.clip_epsilon = clip_epsilon
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        
        self.actor_critic = ActorCritic(input_dim, n_actions)
        self.optimizer = optim.Adam(self.actor_critic.parameters(), lr=lr)
        self.memory = PPOMemory()
    
    def choose_action(self, state):
        state = torch.FloatTensor(state).unsqueeze(0)
        
        with torch.no_grad():
            action_probs, value = self.actor_critic(state)
        
        dist = Categorical(action_probs)
        action = dist.sample()
        
        return action.item(), action_probs[0][action.item()].item(), value.item()
    
    def learn(self):
        states = torch.FloatTensor(np.array(self.memory.states))
        actions = torch.LongTensor(np.array(self.memory.actions))
        old_probs = torch.FloatTensor(np.array(self.memory.probs))
        values = torch.FloatTensor(np.array(self.memory.values))
        
        # Calculate advantages
        rewards = []
        discounted_reward = 0
        for reward, done in zip(reversed(self.memory.rewards), reversed(self.memory.dones)):
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
            surr2 = torch.clamp(ratio, 1-self.clip_epsilon, 1+self.clip_epsilon) * advantages
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            critic_loss = nn.MSELoss()(critic_value.squeeze(), rewards)
            
            # Total loss
            total_loss = actor_loss + 0.5 * critic_loss
            
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
            print(f'Episode {episode}, Reward: {episode_reward}')
            
        # # early stopping
        # if episode_reward >= 1000:  # Early stopping if well-trained
        #     print(f'Episode {episode}, Reward: {episode_reward}')
        #     print(f'Environment solved in {episode} episodes!')
        #     break
    
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
                obs, reward, terminated, truncated, _  = env.step(action)
                done = terminated or truncated
                env.render()
                
        env.close()
if __name__ == '__main__':
    agent = train()
    run(agent)