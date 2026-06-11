import asyncio
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .dag_engine import DAGNode


class MessageType(str, Enum):
    TASK_ASSIGN = "TASK_ASSIGN"
    STATUS_UPDATE = "STATUS_UPDATE"
    RESULT_REPORT = "RESULT_REPORT"
    ERROR_REPORT = "ERROR_REPORT"


@dataclass
class AMPMessage:
    type: MessageType
    sender: str
    recipient: str
    payload: Dict[str, Any]
    message_id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


class WorkerAgent:
    def __init__(self, worker_id: str, execute_fn):
        self.worker_id = worker_id
        self.execute_fn = execute_fn
        self.alive = True
        self.last_heartbeat = time.time()

    async def execute_node(self, node: DAGNode) -> Dict[str, Any]:
        self.last_heartbeat = time.time()
        result = await self.execute_fn(node)
        self.last_heartbeat = time.time()
        return {"worker_id": self.worker_id, "node_id": node.id, "result": result}


class MasterAgent:
    def __init__(self, execute_fn, worker_count: int = 4):
        self.execute_fn = execute_fn
        self.worker_count = worker_count
        self.workers: Dict[str, WorkerAgent] = {}
        self.task_queue: "asyncio.Queue[DAGNode]" = asyncio.Queue()
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
        self.messages: List[Dict[str, Any]] = []

        for _ in range(worker_count):
            self.spawn_worker()

    def spawn_worker(self) -> str:
        wid = f"worker-{uuid.uuid4().hex[:8]}"
        self.workers[wid] = WorkerAgent(wid, self.execute_fn)
        return wid

    def kill_worker(self, worker_id: str):
        if worker_id in self.workers:
            self.workers[worker_id].alive = False
            del self.workers[worker_id]

    def _record_msg(self, msg: AMPMessage):
        self.messages.append(msg.to_dict())

    async def _worker_loop(self, worker: WorkerAgent):
        while worker.alive:
            node = await self.task_queue.get()
            self._record_msg(
                AMPMessage(
                    type=MessageType.TASK_ASSIGN,
                    sender="master",
                    recipient=worker.worker_id,
                    payload={"node_id": node.id, "task": node.task},
                )
            )
            try:
                self._record_msg(
                    AMPMessage(
                        type=MessageType.STATUS_UPDATE,
                        sender=worker.worker_id,
                        recipient="master",
                        payload={"node_id": node.id, "status": "in_progress"},
                    )
                )
                result = await worker.execute_node(node)
                self.results[node.id] = result
                self._record_msg(
                    AMPMessage(
                        type=MessageType.RESULT_REPORT,
                        sender=worker.worker_id,
                        recipient="master",
                        payload={"node_id": node.id, "status": "completed", "result": result},
                    )
                )
            except Exception as e:
                self.errors[node.id] = str(e)
                self._record_msg(
                    AMPMessage(
                        type=MessageType.ERROR_REPORT,
                        sender=worker.worker_id,
                        recipient="master",
                        payload={"node_id": node.id, "status": "failed", "error": str(e)},
                    )
                )
            finally:
                self.task_queue.task_done()

    async def execute_nodes(self, nodes: List[DAGNode]) -> Dict[str, Any]:
        for node in nodes:
            await self.task_queue.put(node)

        loops = [asyncio.create_task(self._worker_loop(w)) for w in self.workers.values()]
        await self.task_queue.join()
        for t in loops:
            t.cancel()

        return {
            "results": self.results,
            "errors": self.errors,
            "messages": self.messages,
            "workers": list(self.workers.keys()),
        }

    def health_check(self) -> Dict[str, Any]:
        now = time.time()
        out = {}
        for wid, w in self.workers.items():
            lag = now - w.last_heartbeat
            out[wid] = {"alive": w.alive, "last_heartbeat_lag_sec": round(lag, 3)}
        return out

    def recover_workers(self):
        # ensure pool size
        while len(self.workers) < self.worker_count:
            self.spawn_worker()
