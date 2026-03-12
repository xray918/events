"""
Events Backend — AI-Native Event System for ClawdChat

Start:
    cd backend && uv run events
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.api.v1 import api_router
from app.db.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    print(f"🎪 Starting {settings.app_name}...")
    print(f"📍 Environment: {settings.app_env}")
    print(f"📚 API Docs: http://localhost:{settings.port}/docs")

    if settings.app_env == "development":
        from app.db.session import init_db
        try:
            await init_db()
            print("✅ Database tables initialized (event_* / sms_* only)")
        except Exception as e:
            print(f"⚠️ Database init failed: {e}")

    from app.services.scheduler import scheduler_loop
    scheduler_task = asyncio.create_task(scheduler_loop())
    print("⏰ Background scheduler started")

    yield

    scheduler_task.cancel()
    await close_redis()
    print(f"👋 Shutting down {settings.app_name}...")


app = FastAPI(
    title=settings.app_name,
    description="AI-Native Events System — Agent 与人类共用的活动管理平台",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


# ---------------------------------------------------------------------------
# Skill files (served as plain text for Agents)
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).parent / "skill"
API_DOCS_DIR = Path(__file__).parent / "api_docs"


@app.get("/skill.md", response_class=PlainTextResponse, tags=["skill"])
async def serve_skill():
    """Attendee Agent skill file."""
    path = SKILL_DIR / "skill.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "# Events Skill\n\nSkill file not yet configured."


@app.get("/staff-skill.md", response_class=PlainTextResponse, tags=["skill"])
async def serve_staff_skill():
    """Staff Agent skill file."""
    path = SKILL_DIR / "staff-skill.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "# Staff Skill\n\nStaff skill file not yet configured."


@app.get("/api-docs/{section}", response_class=PlainTextResponse, tags=["skill"])
async def serve_api_docs(section: str):
    """Detailed API docs by section (for Agents)."""
    safe_name = section.replace("/", "").replace("..", "")
    path = API_DOCS_DIR / f"{safe_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"# {section}\n\nDocumentation section '{section}' not found."


# ---------------------------------------------------------------------------
# Health & Root
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/", tags=["root"])
async def root():
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "skill": "/skill.md",
        "staff_skill": "/staff-skill.md",
    }


def cli():
    """Entry point: uv run events"""
    import uvicorn

    is_prod = settings.app_env == "production"
    uvicorn.run(
        "main:app",
        host="0.0.0.0" if is_prod else "127.0.0.1",
        port=settings.port,
        reload=not is_prod,
    )
