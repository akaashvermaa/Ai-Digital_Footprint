"""Input cleaning, rate limiting, safe response headers and error handling.

Nothing the user types is ever logged: error handlers log only the exception TYPE.
Configuration comes from environment variables (see .env.example), never from code:
    ALLOWED_ORIGINS      comma-separated list of frontend origins allowed by CORS
    RATE_LIMIT_PER_MIN   analyses allowed per minute per client IP (default 10)
"""
import logging
import os
import re
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("footprint")

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁦-⁩]")

SECURITY_HEADERS = {
    "Cache-Control": "no-store",            # results contain personal data: never cache them
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


def clean_text(text: str | None) -> str:
    """Remove control and invisible/bidi-override characters, normalise newlines, trim."""
    if not text:
        return ""
    text = CONTROL_CHARS.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class RateLimiter:
    """Sliding-window limiter kept in memory (fine for one server process)."""

    def __init__(self, window: int = 60):
        self.window = window
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int) -> int:
        """Returns 0 if allowed, otherwise the number of seconds to wait."""
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= limit:
            return max(1, int(self.window - (now - q[0])) + 1)
        q.append(now)
        return 0

    def reset(self):
        self.hits.clear()


limiter = RateLimiter()


def rate_limits() -> dict[str, int]:
    per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))
    return {"/api/analyze": per_min, "/api/report": per_min * 2}


def _friendly_validation_message(exc: RequestValidationError) -> str:
    """One readable sentence; never echoes the submitted values."""
    errors = exc.errors()
    if not errors:
        return "Invalid request."
    err = errors[0]
    field = str(err["loc"][-1]) if err.get("loc") else "input"
    if err["type"] == "string_too_long":
        return f"The {field} is too long (maximum {err.get('ctx', {}).get('max_length')} characters)."
    if err["type"] == "too_long":
        return f"Too many items in '{field}'."
    return f"Invalid value for '{field}'."


def install_security(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        limit = rate_limits().get(request.url.path) if request.method == "POST" else None
        if limit:
            client = request.client.host if request.client else "unknown"
            wait = limiter.check(f"{client}:{request.url.path}", limit)
            if wait:
                response = JSONResponse(
                    {"detail": f"Too many requests. Please wait {wait} seconds and try again."},
                    status_code=429, headers={"Retry-After": str(wait)})
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    # Added after the guard, so CORS is the outermost layer and also covers 429 responses
    origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse({"detail": _friendly_validation_message(exc)}, status_code=422,
                            headers=SECURITY_HEADERS)

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception):
        logger.error("Unhandled error: %s", type(exc).__name__)   # type only, never the input
        return JSONResponse({"detail": "Something went wrong while analysing. Please try again."},
                            status_code=500, headers=SECURITY_HEADERS)
