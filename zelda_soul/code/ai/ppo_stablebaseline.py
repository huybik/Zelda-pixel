from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.env_checker import check_env
from environment.env import Environment, EnvironmentConfig


def train(model=None, total_timesteps=1000000):
    env = Environment()
    check_env(env, warn=True, skip_render_check=True)
    # Wrap the environment to be compatible with Stable-Baselines3
    # For vectorized environments, use `make_vec_env` if training on multiple instances.
    env = make_vec_env(Environment, n_envs=1)

    # Initialize PPO agent
    if not model:
        model = PPO(
            policy="MultiInputPolicy",  # Use Multi-Layer Perceptron policy
            env=env,
            learning_rate=3e-4,
            gamma=0.99,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            clip_range=0.2,
            verbose=1,
        )
    else:
        model.set_env(env)

    # Train the model
    model.learn(total_timesteps=total_timesteps)

    # Save the best model
    model.save("ppo_best_model")
    print("Model saved!")

    return model


def run(model=None):
    # Load your custom environment for evaluation
    env = Environment()

    obs, _ = env.reset()
    done = False

    n_episodes = 1
    for _ in range(n_episodes):
        obs, info = env.reset()
        done = False
        reward_sum = 0
        while not done:
            # action, _states = model.predict(obs, deterministic=True)
            action, _states = model.predict(obs)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            reward_sum += reward
            print(env.int_to_action[int(action)], reward_sum)
            env.render()

    env.close()


if __name__ == "__main__":
    # Train and evaluate the model
    model = train()
    run(model)
