from typing import Any, Callable, Dict, List

from .mcp_protocol import MCPError, MCPResponse, validate_request


class MCPServer:
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, schema: Dict[str, Any], handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self.tools[name] = {"name": name, "schema": schema, "handler": handler}

    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": t["name"], "schema": t["schema"]} for t in self.tools.values()]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.tools:
            raise MCPError(code=-32601, message=f"Tool not found: {name}")
        return self.tools[name]["handler"](arguments)

    def handle_rpc(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            req = validate_request(payload)
            if req.method == "initialize":
                return MCPResponse(id=req.id, result={"server": "prometheus-mcp", "version": "0.1.0"}).to_dict()
            if req.method == "tools/list":
                return MCPResponse(id=req.id, result={"tools": self.list_tools()}).to_dict()
            if req.method == "tools/call":
                name = req.params.get("name", "")
                args = req.params.get("arguments", {})
                result = self.call_tool(name, args)
                return MCPResponse(id=req.id, result={"output": result}).to_dict()
            raise MCPError(code=-32601, message=f"Method not found: {req.method}")
        except MCPError as e:
            req_id = str(payload.get("id", "1"))
            return MCPResponse(id=req_id, error=e.to_dict()).to_dict()
        except Exception as e:
            req_id = str(payload.get("id", "1"))
            return MCPResponse(id=req_id, error={"code": -32000, "message": str(e)}).to_dict()
