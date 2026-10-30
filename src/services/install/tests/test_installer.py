"""Tests for the install orchestration sequence — every collaborator is mocked.

These pin down the actual step order and the two failure-handling rules
that matter most: a DNS mismatch stops before ever calling certbot, and any
exception anywhere is caught into app.state instead of killing the thread.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from app import state
from app.dns_check import DomainCheckResult
from app.installer import run_installation


def setup_function() -> None:
    """Reset the shared module-level state before each test."""
    state.reset()


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "deploy").mkdir()
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    return tmp_path


@patch("app.installer.marker")
@patch("app.installer.compose_runner")
@patch("app.installer.nginx_setup")
@patch("app.installer.env_writer")
@patch("app.installer.discover_manifests", return_value=[])
@patch("app.installer.load_shared_secrets", return_value={})
def test_no_domain_skips_dns_and_certbot_entirely(
    _load_secrets,
    _discover,
    env_writer,
    nginx_setup,
    compose_runner,
    marker,
    tmp_path: Path,
) -> None:
    """With no domain, the plain config is written and TLS is never touched."""
    repo_root = _repo(tmp_path)

    run_installation(repo_root, form_values={}, domain=None, email=None)

    nginx_setup.write_plain_config.assert_called_once_with(repo_root)
    nginx_setup.write_bootstrap_config.assert_not_called()
    nginx_setup.write_final_config.assert_not_called()
    env_writer.write_env_files.assert_called_once()
    marker.write_installed_marker.assert_called_once_with(repo_root, "0.1.0")
    assert state.get_state().step == "done"
    assert state.get_state().error is None


@patch("app.installer.marker")
@patch("app.installer.certbot_runner")
@patch("app.installer.dns_check")
@patch("app.installer.compose_runner")
@patch("app.installer.nginx_setup")
@patch("app.installer.env_writer")
@patch("app.installer.discover_manifests", return_value=[])
@patch("app.installer.load_shared_secrets", return_value={})
def test_domain_given_runs_the_full_tls_sequence_in_order(
    _load_secrets,
    _discover,
    env_writer,
    nginx_setup,
    compose_runner,
    dns_check,
    certbot_runner,
    marker,
    tmp_path: Path,
) -> None:
    """Bootstrap config -> DNS match -> certbot -> final config -> nginx rebuild."""
    repo_root = _repo(tmp_path)
    dns_check.check_domain_points_here.return_value = DomainCheckResult(
        domain="example.com", resolved_ip="1.2.3.4", server_ip="1.2.3.4"
    )

    run_installation(
        repo_root, form_values={}, domain="example.com", email="a@example.com"
    )

    nginx_setup.write_bootstrap_config.assert_called_once_with(repo_root)
    dns_check.check_domain_points_here.assert_called_once_with("example.com")
    certbot_runner.issue_certificate.assert_called_once()
    nginx_setup.write_final_config.assert_called_once_with(repo_root, "example.com")
    # Full stack up once, then a second, nginx-only rebuild for the new config.
    assert compose_runner.bring_up_stack.call_count == 2
    second_call = compose_runner.bring_up_stack.call_args_list[1]
    assert second_call.kwargs.get("services") == ["nginx"] or second_call.args[-1] == [
        "nginx"
    ]
    marker.write_installed_marker.assert_called_once()
    assert state.get_state().step == "done"


@patch("app.installer.marker")
@patch("app.installer.certbot_runner")
@patch("app.installer.dns_check")
@patch("app.installer.compose_runner")
@patch("app.installer.nginx_setup")
@patch("app.installer.env_writer")
@patch("app.installer.discover_manifests", return_value=[])
@patch("app.installer.load_shared_secrets", return_value={})
def test_dns_mismatch_stops_before_ever_calling_certbot(
    _load_secrets,
    _discover,
    env_writer,
    nginx_setup,
    compose_runner,
    dns_check,
    certbot_runner,
    marker,
    tmp_path: Path,
) -> None:
    """A wrong/stale A record must never burn a Let's Encrypt attempt."""
    repo_root = _repo(tmp_path)
    dns_check.check_domain_points_here.return_value = DomainCheckResult(
        domain="example.com", resolved_ip="9.9.9.9", server_ip="1.2.3.4"
    )

    run_installation(
        repo_root, form_values={}, domain="example.com", email="a@example.com"
    )

    certbot_runner.issue_certificate.assert_not_called()
    marker.write_installed_marker.assert_not_called()
    current = state.get_state()
    assert current.error is not None
    assert "9.9.9.9" in current.error
    assert "1.2.3.4" in current.error


@patch("app.installer.marker")
@patch("app.installer.compose_runner")
@patch("app.installer.nginx_setup")
@patch("app.installer.env_writer")
@patch("app.installer.discover_manifests", return_value=[])
@patch("app.installer.load_shared_secrets", return_value={})
def test_an_exception_anywhere_is_caught_into_state_not_raised(
    _load_secrets,
    _discover,
    env_writer,
    nginx_setup,
    compose_runner,
    marker,
    tmp_path: Path,
) -> None:
    """A background thread with an uncaught exception would die silently."""
    repo_root = _repo(tmp_path)
    compose_runner.bring_up_stack.side_effect = RuntimeError("docker is not running")

    run_installation(repo_root, form_values={}, domain=None, email=None)

    current = state.get_state()
    assert current.error == "docker is not running"
    assert current.running is False
    marker.write_installed_marker.assert_not_called()


@patch("app.installer.marker")
@patch("app.installer.compose_runner")
@patch("app.installer.nginx_setup")
@patch("app.installer.env_writer")
@patch("app.installer.discover_manifests")
@patch("app.installer.load_shared_secrets", return_value={})
def test_form_values_reach_env_writer(
    _load_secrets,
    discover,
    env_writer,
    nginx_setup,
    compose_runner,
    marker,
    tmp_path: Path,
) -> None:
    """The submitted form values are passed straight through to the writer."""
    repo_root = _repo(tmp_path)
    fake_manifests = MagicMock()
    discover.return_value = fake_manifests
    form_values = {"superuser_username": "admin", "superuser_password": "s3cret123"}

    run_installation(repo_root, form_values=form_values, domain=None, email=None)

    env_writer.write_env_files.assert_called_once_with(fake_manifests, {}, form_values)
