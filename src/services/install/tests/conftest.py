"""Shared fixtures for install_service endpoint tests."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

import app.main as main_module
from app import state


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    state.reset()


@pytest.fixture
def repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal fake repo: deploy/, VERSION, and one service's install.yml."""
    (tmp_path / "deploy").mkdir()
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    identity_dir = tmp_path / "src" / "services" / "identity"
    identity_dir.mkdir(parents=True)
    (identity_dir / "install.yml").write_text(
        yaml.safe_dump(
            {
                "vars": {
                    "SUPERUSER_USERNAME": {
                        "source": "form",
                        "field": "superuser_username",
                        "label": "Имя суперпользователя",
                        "required": True,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(main_module, "REPO_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def client(repo_root: Path) -> TestClient:
    """A TestClient bound to the fake repo above."""
    return TestClient(main_module.app)
