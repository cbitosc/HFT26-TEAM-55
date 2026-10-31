from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.config import ENVIRONMENT
from app.db.database import init_db
from app.routers.repository import router as repository_router
from app.routers.search import router as search_router
from app.routers.ai import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize database tables and FTS5 on startup."""
    init_db()
    from app.services.source_store import init
    init()
    yield


app = FastAPI(
    title="CodeCompass API",
    description="Backend service for CodeCompass - Helping New Contributors Find the Right Code",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """Root welcome endpoint."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    return FileResponse(Path(__file__).parent / "static/index.html")


@app.get("/health")
def health_check():
    """Health check endpoint to verify backend service status."""
    return {
        "status": "healthy",
        "service": "codecompass-backend",
        "environment": ENVIRONMENT,
    }


# Mount API routers under /api namespace (e.g. /api/repository/upload, /api/repository/status, /api/search, /api/ai/explain)
api_router = APIRouter(prefix="/api")
api_router.add_api_route("/health", health_check, methods=["GET"])
api_router.include_router(repository_router)
api_router.include_router(search_router)
api_router.include_router(ai_router)
app.include_router(api_router)

# Also mount directly (e.g. /repository/upload, /search, /ai/explain) for versatile direct invocation
app.include_router(repository_router)
app.include_router(search_router)
app.include_router(ai_router)

from app.routers.explorer import router as explorer_router
app.include_router(explorer_router)

from fastapi.staticfiles import StaticFiles
from pathlib import Path
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
