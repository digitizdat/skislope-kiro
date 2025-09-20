"""MCP (Model Context Protocol) implementation for agent servers."""

import json
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str
    description: str
    inputSchema: dict[str, Any]


class MCPRequest(BaseModel):
    """MCP request model."""

    method: str
    params: dict[str, Any] | None = None


class MCPResponse(BaseModel):
    """MCP response model."""

    result: Any | None = None
    error: str | None = None


class MCPHandler:
    """MCP protocol handler for agent servers."""

    def __init__(self, app: FastAPI, agent_name: str):
        self.app = app
        self.agent_name = agent_name
        self.tools: dict[str, MCPTool] = {}
        self.tool_handlers: dict[str, Any] = {}
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up FastAPI routes for MCP."""

        @self.app.get("/mcp/tools")
        async def list_tools() -> dict[str, Any]:
            """List available MCP tools."""
            return {
                "tools": list(self.tools.values()),
                "agent": self.agent_name,
            }

        @self.app.post("/mcp/call")
        async def call_tool(request: Request) -> Response:
            """Call an MCP tool."""
            try:
                body = await request.body()
                request_data = json.loads(body)

                tool_name = request_data.get("name")
                arguments = request_data.get("arguments", {})

                if tool_name not in self.tool_handlers:
                    return Response(
                        content=json.dumps({"error": f"Tool '{tool_name}' not found"}),
                        media_type="application/json",
                        status_code=404,
                    )

                # Execute tool
                handler = self.tool_handlers[tool_name]
                result = await handler(**arguments)

                return Response(
                    content=json.dumps({"result": result}),
                    media_type="application/json",
                )

            except Exception as e:
                logger.error(
                    "MCP tool execution failed",
                    tool=tool_name,
                    error=str(e),
                    exc_info=True,
                )
                return Response(
                    content=json.dumps({"error": str(e)}),
                    media_type="application/json",
                    status_code=500,
                )

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Any,
    ) -> None:
        """
        Register an MCP tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool input
            handler: Async function to handle tool calls
        """
        tool = MCPTool(
            name=name,
            description=description,
            inputSchema=input_schema,
        )

        self.tools[name] = tool
        self.tool_handlers[name] = handler

        logger.info(
            "Registered MCP tool",
            tool=name,
            agent=self.agent_name,
        )


def add_mcp_support(app: FastAPI, agent_name: str) -> MCPHandler:
    """
    Add MCP protocol support to a FastAPI app.

    Args:
        app: FastAPI application
        agent_name: Name of the agent

    Returns:
        MCP handler instance
    """
    return MCPHandler(app, agent_name)
