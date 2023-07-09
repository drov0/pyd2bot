import csv
import gc
import os
import random

import keras
import numpy as np
import tensorflow as tf
from keras.layers import Dense
from keras.models import Sequential, load_model
from keras.optimizers import Adam

from pyd2bot.logic.roleplay.behaviors.farm.DQNAgent.PrioritizedMemory import \
    PrioritizedMemory
from pyd2bot.logic.roleplay.behaviors.farm.DQNAgent.ResourceFarmerState import \
    ResourceFarmerState
from pydofus2.com.ankamagames.jerakine.logger.Logger import Logger

CURR_DIR = os.path.dirname(os.path.abspath(__file__))

class DQNAgent:
    
    def __init__(self):
        self.state_size = ResourceFarmerState.STATE_SIZE
        self.action_size = ResourceFarmerState.ACTION_SIZE
        self.memory = PrioritizedMemory(2000, self)
        self.gamma = 0.99999  # discount rate
        self.epsilon = 0.999  # exploration rate
        self.epsilon_min = 0.3
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.experiences_file = os.path.join(CURR_DIR, 'experience_data.csv')
        self.model = self._build_model()
        self.model_path = None

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        model = Sequential()
        model.add(Dense(512, input_dim=self.state_size, activation="relu"))
        model.add(Dense(512, activation="relu"))
        model.add(Dense(256, activation="relu"))
        model.add(Dense(128, activation="relu"))
        model.add(Dense(64, activation="relu"))
        model.add(Dense(self.action_size, activation="linear"))
        model.compile(loss="mse", optimizer=Adam(learning_rate=self.learning_rate), run_eagerly=True)
        return model

    def remember(self, state, action, reward, next_state):
        self.memory.add(state, action, reward, next_state)        
        
        # Save to CSV for offline training.
        with open(self.experiences_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(state.tolist() + [action, reward] + next_state.tolist())

    def act(self, state: ResourceFarmerState):
        # Adjust epsilon based on state characteristics
        epsilon = self.epsilon
        if state.nbrVertexVisites.get(state.vertex, 0) > 10:
            epsilon = 0.1  # Decrease epsilon if the current vertex has been visited frequently
        if not state.getFarmableResources():
            epsilon = 0.8  # Decrease epsilon if there are no farmable resources in the current state
        Logger().debug(f"Bot probability of exploration is : {epsilon:.2f}")
        if np.random.rand() <= epsilon:
            Logger().debug("Agent will chose a random action")
            return state.getRandomValidAction()
        Logger().debug("Agent will chose the best action")
        state_repr = state.represent()
        state_repr = np.expand_dims(state_repr, axis=0)
        act_values = self.model.predict(state_repr)
        return state.getValidAction(act_values[0])

    def replay(self, batch_size):
        minibatch, is_weights = self.memory.sample(batch_size)
        for (state, action, reward, next_state), is_weight in zip(minibatch, is_weights):
            self._train_single(state, action, reward, next_state, is_weight)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            Logger().debug("Epsilon updated")

    def load(self, file_path):
        self.model = load_model(file_path)

    def save(self, file_path):
        self.model.save(file_path)

    def train_from_csv(self, batch_size, epochs):
        with open(self.experiences_file, 'r') as file:
            reader = csv.reader(file)
            data = []
            for row in reader:
                state = np.array(row[:self.state_size], dtype=float)
                action = int(row[self.state_size])
                reward = float(row[self.state_size + 1])
                next_state = np.array(row[self.state_size + 2:], dtype=float)
                data.append((state, action, reward, next_state))
        
        random.shuffle(data)  # Shuffle the data before batching
        batch_count = len(data) // batch_size

        for i in range(batch_count):
            batch_data = data[i*batch_size:(i+1)*batch_size]
            states, targets = [], []

            for state, action, reward, next_state in batch_data:
                target = self.model.predict(np.expand_dims(state, axis=0))[0]
                q_values = self.model.predict(np.expand_dims(next_state, axis=0))[0]
                Q_future = ResourceFarmerState.getMaxQvalue(next_state, q_values)
                target[action] = reward + Q_future * self.gamma
                states.append(state)
                targets.append(target)

            states = np.array(states)
            targets = np.array(targets)

            self.model.fit(states, targets, epochs=1, verbose=1)
            keras.backend.clear_session()
            gc.collect()

        self.save(self.model_path)
        
    def _train_single(self, state, action, reward, _next_state, is_weight=1):
        if action < ResourceFarmerState.ACTION_SIZE:
            state = np.expand_dims(state, axis=0)
            next_state = np.expand_dims(_next_state, axis=0)
            target = self.model.predict(state)
            
            q_values = self.model.predict(next_state)[0]
            Q_future = ResourceFarmerState.getMaxQvalue(_next_state, q_values)
            target[0][action] = reward + Q_future * self.gamma

            # Adjust the target based on the importance sampling weight
            target *= is_weight

            self.model.fit(state, target, epochs=1, verbose=0)
            
if __name__ == "__main__":
    model_path = os.path.join(CURR_DIR, "lamarque.samuel99@gmail.com_agent_model")
    agent = DQNAgent()
    agent.model_path = model_path
    # agent.load(model_path)
    for _ in range(100):
        agent.train_from_csv(32, 100)