import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx

from .mcp_protocol import MCPRequest


class MCPClient:
    def __init__(self):
        self.http_clients: Dict[str, httpx.AsyncClient] = {}

    async def _http_call(self, endpoint: str, method: str, params: Dict[str, Any], req_id: str = "1") -> Dict[str, Any]:
        client = self.http_clients.setdefault(endpoint, httpx.AsyncClient(timeout=120))
        req = MCPRequest(method=method, params=params, id=req_id).to_dict()
        r = await client.post(endpoint, json=req)
        r.raise_for_status()
        return r.json()

    async def tools_list(self, endpoint: str) -> List[Dict[str, Any]]:
        resp = await self._http_call(endpoint, "tools/list", {})
        return resp.get("result", {}).get("tools", [])

    async def tools_call(self, endpoint: str, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        resp = await self._http_call(endpoint, "tools/call", {"name": tool, "arguments": arguments})
        return resp.get("result", {})

    async def stdio_call(self, cmd: List[str], method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        req = MCPRequest(method=method, params=params, id="1").to_dict()
        proc.stdin.write((json.dumps(req) + "\n").encode())
        await proc.stdin.drain()
        line = await proc.stdout.readline()
        await proc.wait()
        return json.loads(line.decode() or "{}")

    async def close(self):
        for c in self.http_clients.values():
            await c.aclose()
