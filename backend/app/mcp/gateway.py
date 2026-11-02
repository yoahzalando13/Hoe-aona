"""Client MCP du backend.

Au démarrage, la passerelle lance les serveurs MCP déclarés dans `mcp_servers.json`
(stdio), liste leurs outils et garde les sessions ouvertes. Le pipeline appelle ensuite
`await gateway.call("news_search", query=...)` sans savoir quel serveur répond.

En mode `direct`, ou si un serveur ne démarre pas, les outils internes sont appelés
directement : l'analyse continue, et l'incident est signalé dans /api/health.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from contextlib import AsyncExitStack
from typing import Any

from ..config import BACKEND_DIR, Settings
from ..tools.registry import TOOLS

log = logging.getLogger("hoe-aona.mcp")


def _expand_env(value: str) -> str:
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), value)


class ToolGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stack: AsyncExitStack | None = None
        self._routes: dict[str, tuple[str, Any]] = {}
        self.errors: list[str] = []
        self.used: set[str] = set()

    @property
    def mode(self) -> str:
        return "mcp" if self._routes else "direct"

    @property
    def tool_names(self) -> list[str]:
        names = set(self._routes) | set(TOOLS)
        return sorted(names)

    async def start(self) -> None:
        if self.settings.mcp_mode != "mcp":
            log.info("MCP désactivé : appels directs des outils")
            return
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            self.errors.append("Paquet « mcp » non installé : mode direct")
            return

        try:
            config = json.loads(self.settings.mcp_config_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.errors.append(f"Configuration MCP illisible : {exc}")
            return

        self._stack = AsyncExitStack()
        for name, cfg in config.get("servers", {}).items():
            if not cfg.get("enabled", True):
                continue
            command = sys.executable if cfg.get("command") == "python" else cfg["command"]
            env = {**os.environ, **{k: _expand_env(str(v)) for k, v in cfg.get("env", {}).items()}}
            params = StdioServerParameters(command=command, args=cfg.get("args", []), env=env,
                                           cwd=cfg.get("cwd") or str(BACKEND_DIR))
            try:
                read, write = await self._stack.enter_async_context(stdio_client(params))
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                listed = await session.list_tools()
                for tool in listed.tools:
                    # le premier serveur déclaré l'emporte en cas de doublon
                    self._routes.setdefault(tool.name, (name, session))
                log.info("Serveur MCP %s : %d outils", name, len(listed.tools))
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"Serveur MCP « {name} » indisponible : {exc}")
                log.warning("Serveur MCP %s indisponible : %s", name, exc)

    async def stop(self) -> None:
        if self._stack:
            await self._stack.aclose()
            self._stack = None
        self._routes.clear()

    async def call(self, tool: str, **arguments: Any) -> dict:
        arguments = {k: v for k, v in arguments.items() if v is not None}
        self.used.add(tool)
        route = self._routes.get(tool)
        if route:
            server, session = route
            try:
                result = await session.call_tool(tool, arguments)
                return self._decode(result, server)
            except Exception as exc:  # noqa: BLE001
                log.warning("Appel MCP %s échoué (%s), repli direct", tool, exc)
        if tool in TOOLS:
            return await TOOLS[tool][0](**arguments)
        return {"ok": False, "error": f"Outil inconnu : {tool}", "items": []}

    @staticmethod
    def _decode(result: Any, server: str) -> dict:
        if getattr(result, "isError", False):
            text = " ".join(getattr(c, "text", "") for c in result.content)
            return {"ok": False, "error": f"MCP {server} : {text[:300]}", "items": []}
        data = getattr(result, "structuredContent", None)
        if isinstance(data, dict):
            if set(data) == {"result"}:
                data = data["result"]
            if isinstance(data, dict):
                return data
        text = "".join(getattr(c, "text", "") for c in result.content)
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"ok": True, "items": parsed}
        except ValueError:
            return {"ok": True, "items": [{"text": text}]}


_gateway: ToolGateway | None = None


def get_gateway() -> ToolGateway:
    global _gateway
    if _gateway is None:
        from ..config import get_settings
        _gateway = ToolGateway(get_settings())
    return _gateway
