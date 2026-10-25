"""Drives `docker compose` for the full stack via the host's Docker socket.

This service never runs its own Docker daemon — it talks to the HOST's
daemon through the bind-mounted /var/run/docker.sock (Docker-outside-of-
-Docker). Health is read from `docker compose ps`, not HTTP: install_service
has no reason to share a network with the stack it brings up.
"""

import json
import subprocess
import time
from pathlib import Path

_HEALTHY_STATES = {"healthy", "running"}


class ComposeError(Exception):
    """Raised when a docker compose invocation fails or times out."""


def _compose_files(deploy_dir: Path, use_main_override: bool) -> list[str]:
    """Build the -f arguments shared by every compose invocation.

    Args:
        deploy_dir: the `deploy/` directory holding the compose files.
        use_main_override: whether to also apply docker-compose-main.yml,
            the production-only override (closed ports, etc).

    Returns:
        list[str]: alternating "-f", "<path>" arguments, in the order
            `docker compose` expects (base file first, override second —
            flags before the subcommand, never after it).
    """
    args = ["-f", str(deploy_dir / "docker-compose.yml")]
    if use_main_override:
        args += ["-f", str(deploy_dir / "docker-compose-main.yml")]
    return args


def bring_up_stack(
    deploy_dir: Path,
    use_main_override: bool = False,
    services: list[str] | None = None,
) -> None:
    """Build and start services defined in the compose files.

    Args:
        deploy_dir: the `deploy/` directory holding the compose files.
        use_main_override: whether to also apply docker-compose-main.yml.
        services: service names to limit the build/up to (e.g. `["nginx"]`
            to rebuild just nginx after swapping its config — see
            app/nginx_setup.py). None rebuilds and starts everything.

    Raises:
        ComposeError: if the `docker compose up` invocation fails.
    """
    command = [
        "docker",
        "compose",
        *_compose_files(deploy_dir, use_main_override),
        "up",
        "-d",
        "--build",
        *(services or []),
    ]
    result = subprocess.run(command, cwd=deploy_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise ComposeError(result.stderr or result.stdout)


def list_service_health(
    deploy_dir: Path, use_main_override: bool = False
) -> dict[str, str]:
    """Report each service's current health or run state.

    Args:
        deploy_dir: the `deploy/` directory holding the compose files.
        use_main_override: whether to also apply docker-compose-main.yml.

    Returns:
        dict[str, str]: service name -> "healthy"/"unhealthy"/"starting" for
            a service with a healthcheck, or its raw run state (e.g.
            "running") for one without.

    Raises:
        ComposeError: if the `docker compose ps` invocation fails.
    """
    command = [
        "docker",
        "compose",
        *_compose_files(deploy_dir, use_main_override),
        "ps",
        "--format",
        "json",
    ]
    result = subprocess.run(command, cwd=deploy_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise ComposeError(result.stderr or result.stdout)
    statuses = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        health_or_state = entry.get("Health") or entry.get("State", "unknown")
        statuses[entry["Service"]] = health_or_state
    return statuses


def wait_until_healthy(
    deploy_dir: Path,
    use_main_override: bool = False,
    timeout_seconds: float = 180,
    poll_interval_seconds: float = 2.0,
) -> dict[str, str]:
    """Poll service health until everything is healthy or running.

    Args:
        deploy_dir: the `deploy/` directory holding the compose files.
        use_main_override: whether to also apply docker-compose-main.yml.
        timeout_seconds: give up and raise once this much time has passed.
        poll_interval_seconds: delay between polls.

    Returns:
        dict[str, str]: the final status snapshot, once every service is
            healthy or running.

    Raises:
        ComposeError: if any service reports "unhealthy", or the timeout is
            reached first.
    """
    deadline = time.monotonic() + timeout_seconds
    while True:
        statuses = list_service_health(deploy_dir, use_main_override)
        if any(status == "unhealthy" for status in statuses.values()):
            raise ComposeError(f"a service reported unhealthy: {statuses}")
        if all(status in _HEALTHY_STATES for status in statuses.values()):
            return statuses
        if time.monotonic() >= deadline:
            raise ComposeError(f"timed out waiting for services: {statuses}")
        time.sleep(poll_interval_seconds)
