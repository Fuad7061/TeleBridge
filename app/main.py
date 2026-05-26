import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import rest_api
from app.state import set_worker
from app.workers.telegram import TelegramWorker

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
FRONTEND_OUT = BASE_DIR.parent / "frontend" / "out"
FRONTEND_PAGES_DIR = FRONTEND_OUT / "server" / "pages"
FRONTEND_STATIC_DIR = FRONTEND_OUT / "static"

_frontend_html: dict[str, str] = {}


def _load_frontend():
    _frontend_html.clear()
    if FRONTEND_PAGES_DIR.exists():
        for f in sorted(FRONTEND_PAGES_DIR.iterdir()):
            if f.suffix == ".html":
                _frontend_html[f.stem] = f.read_text()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    _load_frontend()
    w = TelegramWorker()
    set_worker(w)
    await w.start_all()
    yield
    if w:
        await w.stop_all()
    set_worker(None)


app = FastAPI(title="TeleBridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_STATIC_DIR.exists():
    app.mount(
        "/_next/static",
        StaticFiles(directory=str(FRONTEND_STATIC_DIR)),
        name="next_static",
    )

app.include_router(rest_api.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/{rest:path}")
async def serve_frontend(rest: str = ""):
    key = rest or "index"
    if key in _frontend_html:
        return HTMLResponse(_frontend_html[key])
    if "index" in _frontend_html:
        return HTMLResponse(_frontend_html["index"])
    return HTMLResponse("Frontend not built.", status_code=501)
