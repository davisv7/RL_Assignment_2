import gym
import numpy as np
import random

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam

from math import exp, log
from random import uniform
from collections import deque


class DeepQ:
    def __init__(self, env):
        # Env Params
        self.env = env
        # self.env.render()
        self.state_space = self.env.observation_space.n
        self.action_space = self.env.action_space.n
        self.act_size = self.env.action_space.n
        self.obs_size = self.env.observation_space.n

        # Learning Episode Params
        self.episodes = 100000
        self.episode = 1
        self.learning_interval = 1
        self.replay_interval = 1
        self.testing_interval = 10
        self.test_cycles = 10
        self.skip = 1000  # do not fit the first x games

        # Replay Buffer Params
        self.past_games = 10  # remember the last 10 games (at least)
        self.step_limit = 100
        self.max_len = self.past_games * self.step_limit
        self.batch_size = int(self.max_len * 0.5)  # sample from 5% of experience
        self.exp_replay_buffer = deque(maxlen=self.max_len)

        # DQN Params
        self.learning_rate = 0.001
        self.gamma = .9
        self.model = Sequential()
        self.model.add(Dense(self.obs_size, input_dim=self.state_space, activation='softmax'))
        self.model.add(Dense(26, activation='sigmoid'))
        self.model.add(Dense(26, activation='sigmoid'))
        self.model.add(Dense(26, activation='sigmoid'))
        self.model.add(Dense(self.act_size, activation='softmax'))
        self.model.compile(loss='mse',
                           optimizer=Adam(lr=self.learning_rate))

        self.model.summary()

    def do_learning(self):
        """
        Have the agent learn from the environment and replay buffer.
        Periodically evaluate the agent by running tests. 
        :return:
        """
        total_reward = 0

        for i in range(1, self.episodes):
            self.episode = i
            current_state = self.env.reset()
            sub_reward = 0
            done = False
            trial = []
            while not done:

                action = self.epsilon_greedy(current_state)
                next_state, reward, done, _ = self.env.step(action)

                if self.episode > self.skip:
                    self.q_update(current_state, action, reward, next_state, done)

                sub_reward += reward
                terminal = True if next_state == self.obs_size - 1 else False
                trial.append((current_state, action, reward, next_state, terminal))
                current_state = next_state

            if reward == 1 or self.episode > self.skip:
                self.exp_replay_buffer.extend(trial)

            if self.episode % self.replay_interval == 0 and self.episode >= self.skip:
                self.experience_replay()
            if self.episode % self.testing_interval == 0 and self.episode >= self.skip:
                self.do_test()

            total_reward += sub_reward
            print('Episode {}, Reward: {}, Win Rate: {}'.format(i, total_reward, total_reward / (self.episode + 1)))

    def q_update(self, c_s, a, r, s_p, d):
        """
        Update the Q-value in the model using an observation.
        :param c_s: current state
        :param a: action
        :param r: reward
        :param s_p: next state
        :param d: done?
        :return:
        """
        if self.episode > self.skip:
            c_s_one_hot = self.one_hot_state(c_s)
            n_s_one_hot = self.one_hot_state(s_p)
            if d:
                target = r
            else:
                target = (r + self.gamma * np.max(self.model.predict(n_s_one_hot)))
            target_f = self.model.predict(c_s_one_hot)
            target_f[0][a] = target
            self.model.fit(c_s_one_hot, target_f, epochs=2, verbose=0)

    def do_test(self):
        """
        Test the agent multiple times with a greedy policy.
        :return:
        """
        sub_reward = 0
        for i in range(self.test_cycles):
            current_state = self.env.reset()
            done = False
            while not done:
                state_one_hot = self.one_hot_state(current_state)
                outputs = self.model.predict(state_one_hot)[0]
                action = np.argmax(outputs)
                next_state, reward, done, _ = self.env.step(action)
                # print(current_state,action,next_state)
                sub_reward += reward
                current_state = next_state
            # print()
        print("Test win rate after {} episodes: {} out of {} ".format(self.episode, sub_reward, self.test_cycles))

    def one_hot_state(self, state):
        """
        One-hot encode the state.
        :param state:
        :return:
        """
        state_m = np.zeros((1, self.state_space))
        state_m[0][state] = 1
        return state_m

    def decay_function(self):
        """
        Decay epsilon based on number of episodes
        :return:
        """
        epsilon = min(log(2, exp(1)) / self.episode * 10000, 1)
        return epsilon

    def epsilon_greedy(self, state):
        """
        Generate random number and compare it to epsilon. If the number is less than epsilon, do random action.
        Else, do best action.
        :param state:
        :return: action (int)
        """
        if self.episode <= self.skip:
            return self.env.action_space.sample()
        chance = uniform(0, 1)
        self.epsilon = self.decay_function()
        state_one_hot = self.one_hot_state(state)
        if chance < self.epsilon:
            return self.env.action_space.sample()
        else:
            outputs = self.model.predict(state_one_hot)[0]
            _max = np.argmax(outputs)
            return _max
            # max_indices = np.argwhere(self.model.predict(state_one_hot) == outputs[_max])
            # if len(max_indices) > 1:
            #     return np.random.choice(np.concatenate(max_indices))
            # else:
            #     return max_indices.item(0)

    def experience_replay(self):
        """
        Sample from the replay buffer and train the model.
        :return:
        """
        batch = random.choices(list(self.exp_replay_buffer), k=self.batch_size)
        for i, (s, a, r, s_p, done) in enumerate(batch):
            s_one_hot = self.one_hot_state(s)
            s_p_one_hot = self.one_hot_state(s_p)

            if done:
                target = r
            else:
                target = (r + self.gamma * np.amax(self.model.predict(s_p_one_hot)[0]))

            # print(s,a,r,target)

            target_f = self.model.predict(s_one_hot)
            target_f[0][a] = target
            self.model.fit(s_one_hot, target_f, epochs=1, verbose=False)


def main():
    env_name = 'FrozenLake-v0'
    # map_name = '8x8'
    map_name = '4x4'
    env = gym.make(env_name, map_name=map_name)

    agent = DeepQ(env)
    agent.do_learning()


if __name__ == '__main__':
    main()
