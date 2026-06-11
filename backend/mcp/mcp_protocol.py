from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MCPError(Exception):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "data": self.data}


@dataclass
class MCPRequest:
    method: str
    params: Dict[str, Any]
    id: str = "1"

    def to_dict(self) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": self.id, "method": self.method, "params": self.params}


@dataclass
class MCPResponse:
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": self.id}
        if self.error is not None:
            payload["error"] = self.error
        else:
            payload["result"] = self.result or {}
        return payload


def validate_request(data: Dict[str, Any]) -> MCPRequest:
    if data.get("jsonrpc") != "2.0":
        raise MCPError(code=-32600, message="Invalid JSON-RPC version")
    if "method" not in data:
        raise MCPError(code=-32600, message="Missing method")
    return MCPRequest(method=data["method"], params=data.get("params", {}), id=str(data.get("id", "1")))
