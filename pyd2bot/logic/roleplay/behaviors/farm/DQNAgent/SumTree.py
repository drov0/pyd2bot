import numpy as np


class SumTree:
    
    def __init__(self, capacity):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1)
        self.transitions = np.zeros(capacity, dtype=object)
        self.write = 0
        self.count = 0

    def add(self, priority, transition):
        index = self.write + self.capacity - 1
        self.transitions[self.write] = transition
        self.update(index, priority)
        self.write = (self.write + 1) % self.capacity
        self.count = min(self.count + 1, self.capacity)

    def update(self, index, priority):
        delta = priority - self.tree[index]
        self.tree[index] = priority
        self._propagate(index, delta)

    def get(self, value):
        parent = 0
        while True:
            left_child = 2 * parent + 1
            right_child = left_child + 1
            if left_child >= len(self.tree):
                break
            if value <= self.tree[left_child]:
                parent = left_child
            else:
                value -= self.tree[left_child]
                parent = right_child
        index = parent - self.capacity + 1
        return index, self.tree[parent], self.transitions[index]

    def total(self):
        return self.tree[0]

    def _propagate(self, index, delta):
        parent = (index - 1) // 2
        self.tree[parent] += delta
        if parent != 0:
            self._propagate(parent, delta)
