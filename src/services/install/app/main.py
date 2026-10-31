"""Service entry point: the install form, progress API, and the stub page."""

import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import installer, marker, state
from app.discovery import discover_manifests
from app.env_writer import is_fully_configured
from app.forms import collect_form_fields
from app.health.router import router as health_router
from app.repo_root import resolve_repo_root

# Repo root is bind-mounted into this container at the same absolute path it
# has on the host (see deploy/docker-compose.install.yml) — the env var is
# how the container is told where that mount landed.
REPO_ROOT = resolve_repo_root(os.environ.get("REPO_ROOT"), Path(__file__))

app = FastAPI()
app.include_router(health_router)

_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class InstallRequest(BaseModel):
    """Body of POST /install."""

    form_values: dict[str, str] = {}
    domain: str | None = None
    email: str | None = None


def _already_configured() -> bool:
    """Whether every discovered manifest's .env is already fully set.

    Returns:
        bool: True if a hand-configured deployment is already in place, so
            the wizard has nothing to do.
    """
    manifests = discover_manifests(REPO_ROOT)
    return bool(manifests) and all(is_fully_configured(m) for m in manifests)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Serve the install form, the live progress view, or the stub page.

    Checked in this order on purpose: a background run in progress (`state`)
    must win over `_already_configured()` — that check turns true the
    moment `.env` files are written, which happens near the very start of
    `run_installation`, long before `docker compose up --build` actually
    finishes. Without this ordering, reloading the page mid-build (e.g.
    after closing and reopening the tab) would wrongly show "installed"
    while the stack is still coming up.

    Args:
        request: the incoming request (required by Jinja2Templates).

    Returns:
        HTMLResponse: the rendered form, progress view, or stub page.
    """
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if marker.is_installed(REPO_ROOT):
        context = {"installed": True, "version": version, "in_progress": False}
    elif state.is_running():
        context = {"installed": False, "in_progress": True, "fields": []}
    elif _already_configured():
        context = {"installed": True, "version": version, "in_progress": False}
    else:
        fields = collect_form_fields(discover_manifests(REPO_ROOT))
        context = {"installed": False, "in_progress": False, "fields": fields}
    return _templates.TemplateResponse(request, "index.html", context)


@app.post("/install", status_code=202)
def start_install(payload: InstallRequest) -> dict[str, bool]:
    """Start the installation in a background thread.

    Args:
        payload: submitted form values, plus an optional domain/email pair.

    Returns:
        dict[str, bool]: `{"started": True}` once the background run begins.

    Raises:
        HTTPException: 409 if already installed or already running, 422 if
            a domain was given with no contact email.
    """
    if marker.is_installed(REPO_ROOT):
        raise HTTPException(status_code=409, detail="Уже установлено")
    if state.is_running():
        raise HTTPException(status_code=409, detail="Установка уже выполняется")
    if payload.domain and not payload.email:
        raise HTTPException(
            status_code=422, detail="Email обязателен, если указан домен"
        )

    state.reset()
    state.set_step("starting", "Запуск установки")
    thread = threading.Thread(
        target=installer.run_installation,
        args=(REPO_ROOT, payload.form_values, payload.domain, payload.email),
        daemon=True,
    )
    thread.start()
    return {"started": True}


@app.get("/status")
def get_status() -> dict[str, str | bool | None]:
    """Report the current installation progress.

    Returns:
        dict: the current step, a human-readable message, any error, and
            whether a run is currently in progress.
    """
    current = state.get_state()
    return {
        "step": current.step,
        "message": current.message,
        "error": current.error,
        "running": current.running,
    }
