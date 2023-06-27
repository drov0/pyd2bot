from collections import deque
import csv
import os
import random
from keras.models import Sequential, load_model, save_model
from keras.layers import Dense
from keras.optimizers import Adam
import numpy as np
from pyd2bot.logic.roleplay.behaviors.farm.DQNAgent.ResourceFarmerState import ResourceFarmerState
CURR_DIR = os.path.dirname(os.path.abspath(__file__))

class DQNAgent:
    
    def __init__(self):
        self.state_size = ResourceFarmerState.STATE_SIZE
        self.action_size = ResourceFarmerState.ACTION_SIZE
        self.memory = deque(maxlen=20000)
        self.gamma = 0.99  # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
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
        model.compile(loss="mse", optimizer=Adam(learning_rate=self.learning_rate))
        return model

    def remember(self, state, action, reward, next_state):
        self.memory.append((state, action, reward, next_state))        
        
        # Save to CSV for offline training.
        with open(self.experiences_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(state.tolist() + [action, reward] + next_state.tolist())

    def act(self, state: ResourceFarmerState):
        if np.random.rand() <= self.epsilon:
            return state.getRandomValidAction()
        state_repr = state.represent()
        state_repr = np.expand_dims(state_repr, axis=0)
        act_values = self.model.predict(state_repr)
        qvalues = act_values[0]
        return state.getValidAction(qvalues)

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state in minibatch:
            if action < ResourceFarmerState.ACTION_SIZE:
                state = np.expand_dims(state, axis=0)
                next_state = np.expand_dims(next_state, axis=0)
                target = self.model.predict(state)
                Q_future = max(self.model.predict(next_state)[0])
                target[0][action] = reward + Q_future * self.gamma
                self.model.fit(state, target, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def load(self, file_path):
        self.model = load_model(file_path)

    def save(self, file_path):
        self.model.save(file_path)

    def train_from_csv(self, batch_size):
        with open(self.experiences_file, 'r') as file:
            reader = csv.reader(file)
            data = []
            for row in reader:
                state = np.array(row[:self.state_size], dtype=float)
                action = int(row[self.state_size])
                reward = float(row[self.state_size + 1])
                next_state = np.array(row[self.state_size + 2:], dtype=float)
                data.append((state, action, reward, next_state))

        random.shuffle(data)

        for i in range(0, len(data), batch_size):
            batch_data = data[i:i+batch_size]
            for state, action, reward, next_state in batch_data:
                self._train_single(state, action, reward, next_state)
            
        self.save(self.model_path)
        
    def _train_single(self, state, action, reward, next_state):
        if action < ResourceFarmerState.ACTION_SIZE:
            state = np.expand_dims(state, axis=0)
            next_state = np.expand_dims(next_state, axis=0)
            target = self.model.predict(state)
            Q_future = max(self.model.predict(next_state)[0])
            target[0][action] = reward + Q_future * self.gamma
            self.model.fit(state, target, epochs=1, verbose=0)
            
if __name__ == "__main__":
    model_path = os.path.join(CURR_DIR, "lamarque.samuel99@gmail.com_agent_model")
    agent = DQNAgent()
    agent.model_path = model_path
    agent.load(model_path)
    agent.train_from_csv(32)