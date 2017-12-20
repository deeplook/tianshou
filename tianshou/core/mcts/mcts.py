import numpy as np
import math
import time

c_puct = 5


def list2tuple(list):
    try:
        return tuple(list2tuple(sub) for sub in list)
    except TypeError:
        return list


def tuple2list(tuple):
    try:
        return list(tuple2list(sub) for sub in tuple)
    except TypeError:
        return tuple


class MCTSNode(object):
    def __init__(self, parent, action, state, action_num, prior, inverse=False):
        self.parent = parent
        self.action = action
        self.children = {}
        self.state = state
        self.action_num = action_num
        self.prior = np.array(prior).reshape(-1)
        self.inverse = inverse

    def selection(self, simulator):
        raise NotImplementedError("Need to implement function selection")

    def backpropagation(self, action):
        raise NotImplementedError("Need to implement function backpropagation")

    def valid_mask(self, simulator):
        pass

class UCTNode(MCTSNode):
    def __init__(self, parent, action, state, action_num, prior, inverse=False):
        super(UCTNode, self).__init__(parent, action, state, action_num, prior, inverse)
        self.Q = np.zeros([action_num])
        self.W = np.zeros([action_num])
        self.N = np.zeros([action_num])
        self.ucb = self.Q + c_puct * self.prior * math.sqrt(np.sum(self.N)) / (self.N + 1)
        self.mask = None

    def selection(self, simulator):
        self.valid_mask(simulator)
        action = np.argmax(self.ucb)
        if action in self.children.keys():
            return self.children[action].selection(simulator)
        else:
            self.children[action] = ActionNode(self, action)
            return self.children[action].selection(simulator)

    def backpropagation(self, action):
        action = int(action)
        self.N[action] += 1
        self.W[action] += self.children[action].reward
        for i in range(self.action_num):
            if self.N[i] != 0:
                self.Q[i] = (self.W[i] + 0.) / self.N[i]
        self.ucb = self.Q + c_puct * self.prior * math.sqrt(np.sum(self.N)) / (self.N + 1.)
        if self.parent is not None:
            if self.inverse:
                self.parent.backpropagation(-self.children[action].reward)
            else:
                self.parent.backpropagation(self.children[action].reward)

    def valid_mask(self, simulator):
        # let all invalid actions be illeagel in mcts
        if self.mask is None:
            self.mask = simulator.simulate_is_valid_list(self.state, range(self.action_num - 1))
        self.ucb[self.mask] = -float("Inf")


class TSNode(MCTSNode):
    def __init__(self, parent, action, state, action_num, prior, method="Gaussian", inverse=False):
        super(TSNode, self).__init__(parent, action, state, action_num, prior, inverse)
        if method == "Beta":
            self.alpha = np.ones([action_num])
            self.beta = np.ones([action_num])
        if method == "Gaussian":
            self.mu = np.zeros([action_num])
            self.sigma = np.zeros([action_num])


class ActionNode(object):
    def __init__(self, parent, action):
        self.parent = parent
        self.action = action
        self.children = {}
        self.next_state = None
        self.origin_state = None
        self.state_type = None
        self.reward = 0

    def type_conversion_to_tuple(self):
        if type(self.next_state) is np.ndarray:
            self.next_state = self.next_state.tolist()
        if type(self.next_state) is list:
            self.next_state = list2tuple(self.next_state)

    def type_conversion_to_origin(self):
        if self.state_type is np.ndarray:
            self.next_state = np.array(self.next_state)
        if self.state_type is list:
            self.next_state = tuple2list(self.next_state)

    def selection(self, simulator):
        self.next_state, self.reward = simulator.simulate_step_forward(self.parent.state, self.action)
        self.origin_state = self.next_state
        self.state_type = type(self.next_state)
        self.type_conversion_to_tuple()
        if self.next_state is not None:
            if self.next_state in self.children.keys():
                return self.children[self.next_state].selection(simulator)
            else:
                return self.parent, self.action
        else:
            return self.parent, self.action

    def expansion(self, evaluator, action_num):
        if self.next_state is not None:
            prior, value = evaluator(self.next_state)
            self.children[self.next_state] = UCTNode(self, self.action, self.origin_state, action_num, prior,
                                                     self.parent.inverse)
            return value
        else:
            return 0.

    def backpropagation(self, value):
        self.reward += value
        self.parent.backpropagation(self.action)


class MCTS(object):
    def __init__(self, simulator, evaluator, root, action_num, method="UCT", inverse=False):
        self.simulator = simulator
        self.evaluator = evaluator
        prior, _ = self.evaluator(root)
        self.action_num = action_num
        if method == "":
            self.root = root
        if method == "UCT":
            self.root = UCTNode(None, None, root, action_num, prior, inverse=inverse)
        if method == "TS":
            self.root = TSNode(None, None, root, action_num, prior, inverse=inverse)
        self.inverse = inverse

    def search(self, max_step=None, max_time=None):
        step = 0
        start_time = time.time()
        if max_step is None:
            max_step = int("Inf")
        if max_time is None:
            max_time = float("Inf")
        if max_step is None and max_time is None:
            raise ValueError("Need a stop criteria!")

        while step < max_step and time.time() - start_time < max_step:
            self._expand()
            step += 1

    def _expand(self):
        node, new_action = self.root.selection(self.simulator)
        value = node.children[new_action].expansion(self.evaluator, self.action_num)
        node.children[new_action].backpropagation(value + 0.)

if __name__ == "__main__":
    pass
