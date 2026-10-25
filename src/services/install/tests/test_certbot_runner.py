"""Tests for the certbot wrapper — subprocess.run is mocked throughout."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.certbot_runner import CertbotError, issue_certificate

_RUN = "app.certbot_runner.subprocess.run"


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_issue_certificate_uses_compose_project_derived_volume_names(
    tmp_path: Path,
) -> None:
    """Volume names follow Compose's own `<project>_<suffix>` convention.

    A manual certbot run earlier in this project got this wrong by guessing
    volume names instead of deriving them from the deploy directory's own
    name — this test exists specifically to not repeat that mistake.
    """
    deploy_dir = tmp_path / "deploy"
    with patch(_RUN, return_value=_completed()) as run:
        issue_certificate(deploy_dir, domain="example.com", email="admin@example.com")

    command = run.call_args.args[0]
    assert "deploy_certbot_www:/var/www/certbot" in command
    assert "deploy_certbot_conf:/etc/letsencrypt" in command


def test_issue_certificate_passes_domain_and_email(tmp_path: Path) -> None:
    """The requested domain and contact email reach the certbot command."""
    deploy_dir = tmp_path / "deploy"
    with patch(_RUN, return_value=_completed()) as run:
        issue_certificate(deploy_dir, domain="example.com", email="admin@example.com")

    command = run.call_args.args[0]
    assert "example.com" in command
    assert "admin@example.com" in command
    assert "--non-interactive" in command


def test_issue_certificate_raises_with_certbots_own_error_text(tmp_path: Path) -> None:
    """A failed challenge surfaces certbot's real stderr, not a generic message."""
    deploy_dir = tmp_path / "deploy"
    failed = _completed(returncode=1, stderr="Challenge failed for domain example.com")
    with patch(_RUN, return_value=failed):
        with pytest.raises(CertbotError, match="Challenge"):
            issue_certificate(deploy_dir, domain="example.com", email="a@example.com")
