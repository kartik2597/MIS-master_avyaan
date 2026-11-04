import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request ID and security headers to every response."""
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex[:12]
    started = time.perf_counter()

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGIN_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
