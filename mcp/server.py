"""
Prompt Inspector MCP Server (v0.1.0)

A standalone MCP server that provides prompt injection detection capabilities
via the Model Context Protocol. It connects to the Prompt Inspector backend API
to perform text analysis.

Authentication:
  MCP clients must provide the App API Key via X-App-Key header or as a
  Bearer token in the Authorization header.

Transport:
  SSE (Server-Sent Events) — compatible with VS Code, Cursor, Claude Desktop,
  Dify, and other MCP-capable clients.

Architecture:
  FastAPI (outermost) — owns CORS + auth middleware
    └── FastMCP mounted at "/" — handles MCP protocol (SSE + JSON-RPC)
"""

import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP, Context
from fastmcp.utilities.types import Image
from mcp.types import Icon

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    _env_example = Path(__file__).parent / ".env.example"
    if _env_example.exists():
        load_dotenv(_env_example)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("prompt_inspector_mcp")

# ---------------------------------------------------------------------------
# Shared HTTP client (managed via lifespan)
# ---------------------------------------------------------------------------

_http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the shared HTTP client."""
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=httpx.Timeout(30.0),
    )
    logger.info(f"MCP server started — backend: {API_BASE_URL}")
    yield
    await _http_client.aclose()
    _http_client = None
    logger.info("MCP server stopped")


# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

# Server logo: use local file during dev, fall back to CDN in production
_LOGO_LOCAL = Path(__file__) / "static" / "logo-96x96.png"
_LOGO_CDN = "https://promptinspector.io/logo-96x96.png"

if _LOGO_LOCAL.exists():
    _logo_icon = Icon(src=Image(path=str(_LOGO_LOCAL)).to_data_uri(), mimeType="image/png", sizes=["96x96"])
else:
    _logo_icon = Icon(src=_LOGO_CDN, mimeType="image/png", sizes=["96x96"])

mcp = FastMCP(
    name="Prompt Inspector",
    version="0.1.0",
    instructions=(
        "Prompt Inspector is a prompt injection detection service. "
        "Use the 'detect' tool to check whether a piece of text contains "
        "prompt injection attacks or other malicious content.\n\n"
        "Authentication: provide your App API Key via X-App-Key header or "
        "as a Bearer token in the Authorization header."
    ),
    icons=[_logo_icon],
)

# ---------------------------------------------------------------------------
# FastAPI wrapper — outermost layer handling CORS and auth
# ---------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)

# CORS: let FastAPI's native middleware handle all preflight OPTIONS cleanly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id"],
)

# ---------------------------------------------------------------------------
# Auth middleware (FastAPI @app.middleware style — runs after CORS)
# ---------------------------------------------------------------------------

_auth_cache: dict[str, float] = {}
_CACHE_TTL: int = 300  # seconds


@app.middleware("http")
async def app_key_auth_middleware(request: Request, call_next):
    """
    Validate X-App-Key on MCP transport paths (/sse, /messages).

    Fast path: TTL cache avoids a backend round-trip within 300 s.
    Slow path: calls GET /api/v1/verify-key on the backend.
    Validated key is stored in request.state for tool handlers to reuse.
    """
    # OPTIONS is handled entirely by CORSMiddleware above — pass through
    if request.method == "OPTIONS":
        return await call_next(request)

    # Only guard MCP transport paths
    if not request.url.path.startswith(("/sse", "/messages")):
        return await call_next(request)

    # Extract key: X-App-Key preferred, then Authorization Bearer
    app_key = request.headers.get("x-app-key", "").strip()
    if not app_key:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            app_key = auth[7:].strip()

    if not app_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: Missing X-App-Key or Authorization header."},
        )

    # Fast path: cache hit
    now = time.monotonic()
    if app_key in _auth_cache and _auth_cache[app_key] > now:
        request.state.validated_app_key = app_key
        return await call_next(request)

    # Slow path: validate against backend
    if _http_client is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "MCP server is not ready. Please try again later."},
        )

    try:
        verify_resp = await _http_client.get(
            "/api/v1/verify-key",
            headers={"X-App-Key": app_key},
        )
    except Exception as exc:
        logger.error(f"Key verification request failed: {exc}")
        return JSONResponse(
            status_code=502,
            content={"detail": "Failed to reach authentication service."},
        )

    if verify_resp.status_code != 200:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: Invalid or inactive App Key."},
        )

    # Verification passed — populate cache and request state
    _auth_cache[app_key] = now + _CACHE_TTL
    # Evict expired entries
    expired = [k for k, v in _auth_cache.items() if v <= now]
    for k in expired:
        del _auth_cache[k]

    request.state.validated_app_key = app_key
    return await call_next(request)


# ---------------------------------------------------------------------------
# Helper: extract API key for use inside tool handlers
# ---------------------------------------------------------------------------

def _extract_api_key() -> str | None:
    """
    Extract the App API Key for use inside tool handlers.

    Priority order:
      1. request.state.validated_app_key — injected by auth middleware (zero cost)
      2. X-App-Key request header
      3. Authorization: Bearer <key> header

    Note: environment variable fallback is intentionally omitted.
    All requests must carry an explicit key per-connection.
    """
    try:
        from fastmcp.server.dependencies import get_http_request
        request = get_http_request()
        if request is not None:
            state_key = getattr(request.state, "validated_app_key", None)
            if state_key:
                return state_key
            x_app_key = request.headers.get("x-app-key", "")
            if x_app_key:
                return x_app_key.strip()
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                return auth[7:].strip()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def detect(text: str, ctx: Context) -> str:
    """Detect potential prompt injection or malicious content in the given text.

    This tool analyzes the provided text using Prompt Inspector's multi-layer
    detection engine (sensitive word matching + semantic vector search + optional
    LLM review) and returns a human-readable result with an attached JSON summary.

    Authentication:
        The MCP client must supply the App API Key via the X-App-Key header
        (or Authorization: Bearer <key>) when connecting to this server.
        No per-call api_key parameter is accepted.

    Args:
        text: The text to analyse for prompt injection. Must be a non-empty string.

    Returns:
        A human-readable string containing:
        - Safety status (SAFE / THREAT DETECTED)
        - Risk score (0.0 = safe, 1.0 = certain threat)
        - Detected threat categories
        - Processing latency and request ID
        - Raw JSON for programmatic parsing

    Errors:
        - Authentication failure: ensure X-App-Key is configured in the MCP client.
        - Monthly quota exceeded (HTTP 429): your plan's monthly request limit has
          been reached. Visit https://promptinspector.io to upgrade your subscription
          or contact support.
        - Text too long (HTTP 413): reduce the input length or upgrade your plan at
          https://promptinspector.io.
    """
    if not text or not text.strip():
        return "Error: Parameter 'text' is required and must be a non-empty string."

    key = _extract_api_key()
    if not key:
        return (
            "Error: Authentication required. "
            "Configure X-App-Key in your MCP client connection settings."
        )

    if _http_client is None:
        return "Error: MCP server is not ready. Please try again later."

    try:
        response = await _http_client.post(
            "/api/v1/detect/mcp",
            json={"input_text": text},
            headers={"X-App-Key": key},
        )
    except httpx.TimeoutException:
        return "Error: Request timed out. The backend server did not respond in time."
    except httpx.ConnectError:
        return f"Error: Failed to connect to the backend API at {API_BASE_URL}. Is the server running?"
    except httpx.RequestError as exc:
        logger.error(f"HTTP request error: {exc}")
        return f"Error: HTTP request failed: {str(exc)}"

    if response.status_code == 200:
        data = response.json()
        result = data.get("result", {})
        is_safe: bool = result.get("is_safe", True)
        score = result.get("score")         # float 0.0–1.0 or null
        category: list = result.get("category", [])
        request_id: str = data.get("request_id", "")
        latency_ms: int = data.get("latency_ms", 0)

        status_icon = "\u2705" if is_safe else "\U0001f6a8"
        score_str = f"{score:.2f}" if score is not None else "N/A"
        category_str = ", ".join(category) if category else "none"
        return (
            f"{status_icon} Detection result: {'SAFE' if is_safe else 'THREAT DETECTED'}\n"
            f"Risk score : {score_str} (0.0 = safe, 1.0 = certain threat)\n"
            f"Categories : {category_str}\n"
            f"Latency    : {latency_ms} ms\n"
            f"Request ID : {request_id}\n\n"
            f"Raw JSON   : {json.dumps({'request_id': request_id, 'is_safe': is_safe, 'score': score, 'category': category, 'latency_ms': latency_ms})}"
        )
    elif response.status_code == 401:
        return "Error: Authentication failed. Invalid or inactive API key."
    elif response.status_code == 413:
        return (
            "Error: The input text exceeds the maximum allowed length for your plan. "
            "Please shorten the input or upgrade your plan at https://promptinspector.io."
        )
    elif response.status_code == 429:
        return (
            "Error: Request quota exceeded. You may have hit the per-second rate limit "
            "or your monthly plan limit. Please slow down, or visit "
            "https://promptinspector.io to upgrade your subscription plan."
        )
    else:
        logger.error(f"Backend returned {response.status_code}: {response.text}")
        return f"Error: Backend error (HTTP {response.status_code}). Please try again later."


# ---------------------------------------------------------------------------
# Mount FastMCP as a sub-application under FastAPI
# ---------------------------------------------------------------------------

try:
    mcp_asgi = mcp.http_app(transport="sse")
except (AttributeError, TypeError):
    try:
        mcp_asgi = mcp.get_asgi_app()
    except AttributeError:
        mcp_asgi = mcp.sse_app()

app.mount("/", mcp_asgi)

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
