"""JSON-RPC protocol implementation for agent servers."""

import json
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from agents.shared.logging_config import log_request_response

logger = structlog.get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request model."""

    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    method: str = Field(..., min_length=1)
    params: dict[str, Any] | None = None
    id: str | int | None = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response model."""

    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    result: Any | None = None
    error: dict[str, Any] | None = None
    id: str | int | None = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error model."""

    code: int
    message: str
    data: Any | None = None


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class JSONRPCHandler:
    """JSON-RPC request handler with method registration."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.methods: dict[str, Callable] = {}
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up FastAPI routes for JSON-RPC."""

        @self.app.post("/jsonrpc")
        async def handle_jsonrpc(request: Request) -> Response:
            """Handle JSON-RPC requests."""
            correlation_id = str(uuid.uuid4())
            start_time = time.time()

            try:
                body = await request.body()
                request_data = json.loads(body)

                # Validate request
                try:
                    rpc_request = JSONRPCRequest(**request_data)
                except ValidationError as e:
                    return self._create_error_response(
                        INVALID_REQUEST,
                        "Invalid request format",
                        str(e),
                        request_data.get("id"),
                    )

                # Execute method
                response_data = await self._execute_method(rpc_request, correlation_id)

                # Log request/response
                duration_ms = (time.time() - start_time) * 1000
                log_request_response(
                    logger,
                    rpc_request.method,
                    rpc_request.params or {},
                    response_data,
                    duration_ms,
                    correlation_id,
                )

                return Response(
                    content=json.dumps(response_data, cls=DateTimeEncoder),
                    media_type="application/json",
                )

            except json.JSONDecodeError:
                return self._create_error_response(
                    PARSE_ERROR,
                    "Parse error",
                    "Invalid JSON",
                )
            except Exception as e:
                logger.error(
                    "Unexpected error handling JSON-RPC request",
                    error=str(e),
                    correlation_id=correlation_id,
                    exc_info=True,
                )
                return self._create_error_response(
                    INTERNAL_ERROR,
                    "Internal error",
                    str(e),
                )

    def register_method(self, name: str, handler: Callable) -> None:
        """
        Register a JSON-RPC method handler.

        Args:
            name: Method name
            handler: Async function to handle the method
        """
        self.methods[name] = handler
        logger.info("Registered JSON-RPC method", method=name)

    async def _execute_method(
        self,
        request: JSONRPCRequest,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Execute a JSON-RPC method.

        Args:
            request: Validated JSON-RPC request
            correlation_id: Request correlation ID

        Returns:
            JSON-RPC response data
        """
        if request.method not in self.methods:
            return self._create_error_response(
                METHOD_NOT_FOUND,
                f"Method '{request.method}' not found",
                request_id=request.id,
            )

        try:
            handler = self.methods[request.method]

            # Call handler with parameters
            if request.params:
                result = await handler(**request.params)
            else:
                result = await handler()

            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request.id,
            }

        except TypeError as e:
            return self._create_error_response(
                INVALID_PARAMS,
                "Invalid parameters",
                str(e),
                request.id,
            )
        except Exception as e:
            logger.error(
                "Method execution failed",
                method=request.method,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True,
            )
            return self._create_error_response(
                INTERNAL_ERROR,
                "Method execution failed",
                str(e),
                request.id,
            )

    def _create_error_response(
        self,
        code: int,
        message: str,
        data: Any = None,
        request_id: str | int | None = None,
    ) -> dict[str, Any]:
        """
        Create a JSON-RPC error response.

        Args:
            code: Error code
            message: Error message
            data: Additional error data
            request_id: Original request ID

        Returns:
            JSON-RPC error response
        """
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message,
            },
            "id": request_id,
        }

        if data is not None:
            error_response["error"]["data"] = data

        return error_response


def create_jsonrpc_app(title: str, description: str) -> tuple[FastAPI, JSONRPCHandler]:
    """
    Create a FastAPI app with JSON-RPC support.

    Args:
        title: Application title
        description: Application description

    Returns:
        Tuple of (FastAPI app, JSONRPCHandler)
    """
    app = FastAPI(
        title=title,
        description=description,
        version="1.0.0",
    )

    # Add CORS middleware to allow frontend requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": title}

    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics() -> dict[str, Any]:
        """Basic metrics endpoint."""
        import psutil

        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

    handler = JSONRPCHandler(app)
    return app, handler
