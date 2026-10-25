"""Tests for the docker compose wrapper — subprocess.run is mocked throughout.

No real Docker daemon is involved: these only verify the arguments we build
and how we interpret docker compose's own output/exit code.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.compose_runner import (
    ComposeError,
    bring_up_stack,
    list_service_health,
    wait_until_healthy,
)

_RUN = "app.compose_runner.subprocess.run"


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _ps_line(service: str, health: str, state: str = "running") -> str:
    return json.dumps({"Service": service, "State": state, "Health": health})


def test_bring_up_stack_runs_up_with_build_and_detach(tmp_path: Path) -> None:
    """The base compose file alone is used when no override is requested."""
    with patch(_RUN, return_value=_completed()) as run:
        bring_up_stack(tmp_path)

    args = run.call_args.args[0]
    assert args[:2] == ["docker", "compose"]
    assert args[-3:] == ["up", "-d", "--build"]
    assert str(tmp_path / "docker-compose.yml") in args
    assert str(tmp_path / "docker-compose-main.yml") not in args


def test_bring_up_stack_includes_main_override_when_requested(tmp_path: Path) -> None:
    """The prod override is appended as a second -f, not instead of the base file."""
    with patch(_RUN, return_value=_completed()) as run:
        bring_up_stack(tmp_path, use_main_override=True)

    args = run.call_args.args[0]
    assert str(tmp_path / "docker-compose.yml") in args
    assert str(tmp_path / "docker-compose-main.yml") in args


def test_bring_up_stack_scopes_to_given_services(tmp_path: Path) -> None:
    """Passing services=["nginx"] rebuilds only nginx, not the whole stack.

    Used after swapping nginx.conf mid-install — no reason to rebuild every
    other, unrelated service just to pick up a config file change.
    """
    with patch(_RUN, return_value=_completed()) as run:
        bring_up_stack(tmp_path, services=["nginx"])

    args = run.call_args.args[0]
    assert args[-1] == "nginx"


def test_bring_up_stack_raises_on_nonzero_exit(tmp_path: Path) -> None:
    """A failed `docker compose up` surfaces its stderr, not a generic failure."""
    failed = _completed(returncode=1, stderr="build failed: boom")
    with patch(_RUN, return_value=failed), pytest.raises(ComposeError, match="boom"):
        bring_up_stack(tmp_path)


def test_list_service_health_reads_health_field_when_present(tmp_path: Path) -> None:
    """A service with a healthcheck reports its Health field."""
    stdout = _ps_line("identity", health="healthy")
    with patch(_RUN, return_value=_completed(stdout=stdout)):
        statuses = list_service_health(tmp_path)

    assert statuses == {"identity": "healthy"}


def test_list_service_health_falls_back_to_state_without_a_healthcheck(
    tmp_path: Path,
) -> None:
    """A service with no healthcheck (empty Health) reports its raw State."""
    stdout = _ps_line("web", health="")
    with patch(_RUN, return_value=_completed(stdout=stdout)):
        statuses = list_service_health(tmp_path)

    assert statuses == {"web": "running"}


def test_list_service_health_parses_one_json_object_per_line(tmp_path: Path) -> None:
    """`docker compose ps --format json` emits newline-delimited JSON, not an array."""
    stdout = "\n".join(
        [_ps_line("identity", health="healthy"), _ps_line("db", health="healthy")]
    )
    with patch(_RUN, return_value=_completed(stdout=stdout)):
        statuses = list_service_health(tmp_path)

    assert statuses == {"identity": "healthy", "db": "healthy"}


def test_wait_until_healthy_returns_once_everything_is_healthy(tmp_path: Path) -> None:
    """A single healthy snapshot is enough — no need to poll further."""
    stdout = _ps_line("identity", health="healthy")
    with patch(_RUN, return_value=_completed(stdout=stdout)):
        statuses = wait_until_healthy(tmp_path, poll_interval_seconds=0)

    assert statuses == {"identity": "healthy"}


def test_wait_until_healthy_raises_immediately_on_unhealthy(tmp_path: Path) -> None:
    """An unhealthy service is a hard failure — no point waiting out the timeout."""
    stdout = _ps_line("identity", health="unhealthy")
    with patch(_RUN, return_value=_completed(stdout=stdout)):
        with pytest.raises(ComposeError, match="unhealthy"):
            wait_until_healthy(tmp_path, timeout_seconds=5, poll_interval_seconds=0)


def test_wait_until_healthy_times_out_while_stuck_starting(tmp_path: Path) -> None:
    """A service stuck on 'starting' forever must not hang the installer."""
    stdout = _ps_line("identity", health="starting")
    with patch(_RUN, return_value=_completed(stdout=stdout)):
        with pytest.raises(ComposeError, match="timed out"):
            wait_until_healthy(
                tmp_path, timeout_seconds=0.05, poll_interval_seconds=0.0
            )
