import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

# Step 1: Create the LunarLander-v2 environment
env = gym.make("CartPole-v1")

# Step 2: Create the PPO model
# You can adjust hyperparameters such as learning rate, number of steps, etc.
model = PPO(
    policy="MlpPolicy",          # Use a Multi-Layer Perceptron (MLP) policy
    env=env,                     # Pass the LunarLander-v2 environment
    learning_rate=3e-4,          # Set learning rate
    n_steps=2048,                # Rollout steps
    batch_size=64,               # Batch size for training
    n_epochs=10,                 # Number of epochs for training
    gamma=0.99,                  # Discount factor
    verbose=1                    # Verbosity level (1 for progress updates)
)

# Step 3: Train the PPO model
print("Training the PPO model...")
model.learn(total_timesteps=200_000)  # Train for 200,000 timesteps

# Step 4: Evaluate the trained model
# Evaluate over 10 episodes to see how well the agent performs
print("Evaluating the model...")
mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=10, render=False)
print(f"Mean Reward: {mean_reward}, Standard Deviation: {std_reward}")

# Step 5: Save the trained model
model.save("ppo_lunarlander")

# Step 6: Load and test the saved model
print("Testing the saved model...")
loaded_model = PPO.load("ppo_lunarlander")

env = gym.make("CartPole-v1", render_mode="human")
obs = env.reset()
done = False

n_episodes = 100
for _ in range(n_episodes):
    obs, info = env.reset()
    terminated = False
    truncated = False
    while not terminated:
        action, _states = loaded_model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        env.render()


env.close()