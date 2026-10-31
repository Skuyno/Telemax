"""Tests for the install_service HTTP routes."""

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
from app import state
from app.marker import write_installed_marker


def test_index_shows_the_form_when_not_configured(client: TestClient) -> None:
    """A fresh repo with no .env anywhere shows the install form."""
    response = client.get("/")

    assert response.status_code == 200
    assert 'name="superuser_username"' in response.text
    assert "Имя суперпользователя" in response.text


def test_index_shows_the_stub_once_the_marker_exists(
    client: TestClient, repo_root: Path
) -> None:
    """Once installed, the page stops offering the form entirely."""
    write_installed_marker(repo_root, version="0.1.0")

    response = client.get("/")

    assert response.status_code == 200
    assert "установлен" in response.text.lower()
    assert "0.1.0" in response.text
    assert "install-form" not in response.text


def test_index_shows_form_when_repo_has_no_manifests_at_all(
    tmp_path: Path, monkeypatch
) -> None:
    """An empty manifest set must not vacuously look 'fully configured'."""
    (tmp_path / "deploy").mkdir()
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    monkeypatch.setattr(main_module, "REPO_ROOT", tmp_path)
    client = TestClient(main_module.app)

    response = client.get("/")

    assert "install-form" in response.text


def test_index_shows_progress_when_a_run_is_in_progress(client: TestClient) -> None:
    """A background run in progress shows the live status, not the form."""
    state.set_step("building", "Сборка и запуск контейнеров")

    response = client.get("/")

    assert response.status_code == 200
    assert "Установка выполняется" in response.text
    assert 'id="install-form" class="hidden"' in response.text


def test_index_prefers_in_progress_over_already_configured(
    client: TestClient, repo_root: Path
) -> None:
    """Reloading mid-build must not show 'installed' prematurely.

    `.env` is written near the start of the run, long before the stack
    actually finishes coming up.
    """
    identity_env = repo_root / "src" / "services" / "identity" / ".env"
    identity_env.write_text("SUPERUSER_USERNAME=admin\n", encoding="utf-8")
    state.set_step("building")

    response = client.get("/")

    assert "Мессенджер установлен" not in response.text
    assert "Установка выполняется" in response.text


def test_index_shows_stub_for_a_hand_configured_deployment_when_idle(
    client: TestClient, repo_root: Path
) -> None:
    """An already-fully-configured .env shows the stub when idle.

    This is the hand-configured-deployment scenario — no run in progress.
    """
    identity_env = repo_root / "src" / "services" / "identity" / ".env"
    identity_env.write_text("SUPERUSER_USERNAME=admin\n", encoding="utf-8")

    response = client.get("/")

    assert "Мессенджер установлен" in response.text


def test_post_install_conflicts_when_already_installed(
    client: TestClient, repo_root: Path
) -> None:
    """A completed install refuses a second run outright."""
    write_installed_marker(repo_root, version="0.1.0")

    response = client.post("/install", json={"form_values": {}})

    assert response.status_code == 409


def test_post_install_requires_email_when_domain_is_given(client: TestClient) -> None:
    """A domain with no contact email is rejected before anything starts."""
    response = client.post(
        "/install", json={"form_values": {}, "domain": "example.com", "email": None}
    )

    assert response.status_code == 422


def test_post_install_conflicts_when_a_run_is_already_in_progress(
    client: TestClient,
) -> None:
    """Two concurrent installs would corrupt shared state — refuse the second."""
    state.set_step("building")

    response = client.post("/install", json={"form_values": {}})

    assert response.status_code == 409


def test_post_install_starts_a_background_thread(
    client: TestClient, repo_root: Path, monkeypatch
) -> None:
    """A valid request spawns exactly one daemon thread running the installer."""
    captured = {}

    class FakeThread:
        def __init__(self, target, args, daemon):
            captured["target"] = target
            captured["args"] = args
            captured["daemon"] = daemon

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(main_module.threading, "Thread", FakeThread)

    response = client.post(
        "/install", json={"form_values": {"superuser_username": "admin"}}
    )

    assert response.status_code == 202
    assert captured["started"] is True
    assert captured["daemon"] is True
    assert captured["args"][0] == repo_root
    assert captured["args"][1] == {"superuser_username": "admin"}


def test_get_status_reflects_current_state(client: TestClient) -> None:
    """The status endpoint mirrors app.state exactly."""
    state.set_step("waiting_healthy", "Ожидание готовности сервисов")

    response = client.get("/status")

    body = response.json()
    assert body["step"] == "waiting_healthy"
    assert body["message"] == "Ожидание готовности сервисов"
    assert body["running"] is True
    assert body["error"] is None
