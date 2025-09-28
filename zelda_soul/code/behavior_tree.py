from __future__ import annotations
from enum import Enum, auto
from typing import Callable, Iterable, Protocol, Sequence as TypingSequence


class NodeStatus(Enum):
    """Possible results from ticking a behavior tree node."""

    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


class SupportsTick(Protocol):
    def tick(self, blackboard: dict) -> NodeStatus: ...


class Node:
    """Base class for all behavior tree nodes."""

    def tick(self, blackboard: dict) -> NodeStatus:
        raise NotImplementedError("Behavior tree nodes must implement tick().")


class BehaviorTree:
    """A simple behavior tree runner keeping a reference to the root node."""

    def __init__(self, root: SupportsTick):
        self.root = root

    def tick(self, blackboard: dict) -> NodeStatus:
        return self.root.tick(blackboard)


class CompositeNode(Node):
    """A node that manages an ordered collection of children."""

    def __init__(self, children: TypingSequence[SupportsTick] | Iterable[SupportsTick]):
        self.children = list(children)


class Sequence(CompositeNode):
    """Runs children in order until one fails; succeeds only if all succeed."""

    def tick(self, blackboard: dict) -> NodeStatus:
        for child in self.children:
            status = child.tick(blackboard)
            if status != NodeStatus.SUCCESS:
                return status
        return NodeStatus.SUCCESS


class Selector(CompositeNode):
    """Runs each child until one succeeds; fails only if all fail."""

    def tick(self, blackboard: dict) -> NodeStatus:
        for child in self.children:
            status = child.tick(blackboard)
            if status != NodeStatus.FAILURE:
                return status
        return NodeStatus.FAILURE


class ConditionNode(Node):
    """Evaluates a predicate against the blackboard."""

    def __init__(self, predicate: Callable[[dict], bool]):
        self.predicate = predicate

    def tick(self, blackboard: dict) -> NodeStatus:
        return NodeStatus.SUCCESS if self.predicate(blackboard) else NodeStatus.FAILURE


class ActionNode(Node):
    """Executes a callable that returns a NodeStatus."""

    def __init__(self, action: Callable[[dict], NodeStatus]):
        self.action = action

    def tick(self, blackboard: dict) -> NodeStatus:
        return self.action(blackboard)


class Inverter(Node):
    """Inverts the result of its child node."""

    def __init__(self, child: SupportsTick):
        self.child = child

    def tick(self, blackboard: dict) -> NodeStatus:
        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        if status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return status


class Succeeder(Node):
    """Always returns SUCCESS after ticking its child."""

    def __init__(self, child: SupportsTick):
        self.child = child

    def tick(self, blackboard: dict) -> NodeStatus:
        _ = self.child.tick(blackboard)
        return NodeStatus.SUCCESS
