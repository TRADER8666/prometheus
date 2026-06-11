import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional


class NodeState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class DAGNode:
    id: str
    task: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    state: NodeState = NodeState.PENDING
    result: Any = None
    retries: int = 0
    max_retries: int = 2
    condition: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DAGExecutor:
    def __init__(
        self,
        nodes: List[DAGNode],
        execution_fn: Callable[[DAGNode], Awaitable[Any]],
        max_parallel: int = 4,
        task_id: Optional[str] = None,
        on_state_change: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self.task_id = task_id or str(uuid.uuid4())
        self.nodes: Dict[str, DAGNode] = {n.id: n for n in nodes}
        self.execution_fn = execution_fn
        self.max_parallel = max_parallel
        self.on_state_change = on_state_change
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

    def topological_sort(self) -> List[str]:
        indeg = {nid: 0 for nid in self.nodes}
        graph: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Node {nid} depends on unknown node {dep}")
                graph[dep].append(nid)
                indeg[nid] += 1

        queue = [nid for nid, d in indeg.items() if d == 0]
        out: List[str] = []
        while queue:
            cur = queue.pop(0)
            out.append(cur)
            for nxt in graph[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)

        if len(out) != len(self.nodes):
            raise ValueError("Cycle detected in DAG")
        return out

    def _emit(self):
        if self.on_state_change:
            self.on_state_change(self.task_id, self.get_state())

    def _condition_allows(self, node: DAGNode) -> bool:
        if not node.condition:
            return True
        when = node.condition.get("when")
        source = node.condition.get("node")
        if not source or source not in self.nodes:
            return True
        source_node = self.nodes[source]
        if when == "success":
            return source_node.state == NodeState.COMPLETED
        if when == "failure":
            return source_node.state == NodeState.FAILED
        return True

    def _ready_nodes(self) -> List[DAGNode]:
        ready: List[DAGNode] = []
        for node in self.nodes.values():
            if node.state != NodeState.PENDING:
                continue
            deps_done = all(self.nodes[d].state in {NodeState.COMPLETED, NodeState.SKIPPED} for d in node.dependencies)
            deps_failed = any(self.nodes[d].state == NodeState.FAILED for d in node.dependencies)
            if deps_failed:
                node.state = NodeState.SKIPPED
                node.error = "Dependency failed"
                continue
            if deps_done and self._condition_allows(node):
                ready.append(node)
        return ready

    async def _run_single(self, node: DAGNode):
        node.state = NodeState.IN_PROGRESS
        self._emit()
        try:
            backoff = 1.0
            while True:
                try:
                    node.result = await self.execution_fn(node)
                    node.state = NodeState.COMPLETED
                    node.error = None
                    break
                except Exception as e:
                    node.retries += 1
                    node.error = str(e)
                    if node.retries > node.max_retries:
                        node.state = NodeState.FAILED
                        break
                    await asyncio.sleep(backoff)
                    backoff *= 2
        finally:
            self._emit()

    async def execute(self) -> Dict[str, Any]:
        self.topological_sort()  # validate
        self.started_at = time.time()
        self._emit()

        while True:
            ready = self._ready_nodes()
            if not ready:
                in_progress = any(n.state == NodeState.IN_PROGRESS for n in self.nodes.values())
                if not in_progress:
                    break
                await asyncio.sleep(0.05)
                continue

            batch = ready[: self.max_parallel]
            await asyncio.gather(*[self._run_single(n) for n in batch])

        self.completed_at = time.time()
        self._emit()
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "nodes": {
                nid: {
                    "id": n.id,
                    "task": n.task,
                    "dependencies": n.dependencies,
                    "state": n.state.value,
                    "result": n.result,
                    "retries": n.retries,
                    "max_retries": n.max_retries,
                    "condition": n.condition,
                    "error": n.error,
                }
                for nid, n in self.nodes.items()
            },
        }
