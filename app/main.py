from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routes import configure_store, router
from app.core.config import settings
from app.services.store import EvaluationStore

settings.ensure_data_dir()
configure_store(EvaluationStore(settings.db_path))
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Run explicit LLM evaluation cases and track quality, latency, tokens, cost, and baselines.",
)
app.include_router(router)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    dashboard_path = Path(__file__).resolve().parent.parent / "web" / "index.html"
    return FileResponse(dashboard_path)
