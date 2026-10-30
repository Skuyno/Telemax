"""Orchestrates one end-to-end installation run in a background thread.

Runs step by step through app.state so the form page can poll /status while
it waits — `docker compose build/up` (and, with a domain, certbot) can take
minutes, far too long to hold open a single HTTP request.
"""

from pathlib import Path

from app import (
    certbot_runner,
    compose_runner,
    dns_check,
    env_writer,
    marker,
    nginx_setup,
    state,
)
from app.discovery import discover_manifests, load_shared_secrets

_SHARED_SECRETS_PATH = Path(__file__).resolve().parent.parent / "shared_secrets.yml"


def run_installation(
    repo_root: Path,
    form_values: dict[str, str],
    domain: str | None,
    email: str | None,
) -> None:
    """Run the full install flow: write .env, bring up the stack, TLS.

    Any failure at any step is recorded in app.state (via set_error) instead
    of propagating — this runs in a background thread with nothing to catch
    an uncaught exception, so letting one escape would just kill the thread
    silently and leave the UI polling forever.

    Args:
        repo_root: absolute path to the repository root.
        form_values: submitted form field -> value.
        domain: the domain to issue a certificate for, or None to skip TLS.
        email: contact email for Let's Encrypt — required when domain is set.
    """
    deploy_dir = repo_root / "deploy"
    try:
        state.set_step("writing_env", "Генерация секретов и запись .env")
        manifests = discover_manifests(repo_root)
        shared_secrets = load_shared_secrets(_SHARED_SECRETS_PATH)
        env_writer.write_env_files(manifests, shared_secrets, form_values)

        state.set_step("writing_nginx_config", "Настройка nginx")
        if domain:
            nginx_setup.write_bootstrap_config(repo_root)
        else:
            nginx_setup.write_plain_config(repo_root)

        use_main_override = (deploy_dir / "docker-compose-main.yml").exists()

        state.set_step("building", "Сборка и запуск контейнеров")
        compose_runner.bring_up_stack(deploy_dir, use_main_override)

        state.set_step("waiting_healthy", "Ожидание готовности сервисов")
        compose_runner.wait_until_healthy(deploy_dir, use_main_override)

        if domain:
            _issue_tls(deploy_dir, repo_root, domain, email or "", use_main_override)
            if state.get_state().error:
                return

        version = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
        marker.write_installed_marker(repo_root, version)
        state.set_done()
    except Exception as exc:
        state.set_error(str(exc))


def _issue_tls(
    deploy_dir: Path, repo_root: Path, domain: str, email: str, use_main_override: bool
) -> None:
    """Run the domain-verification and certificate-issuance sub-flow.

    Args:
        deploy_dir: the `deploy/` directory holding the compose files.
        repo_root: absolute path to the repository root.
        domain: the domain to verify and issue a certificate for.
        email: contact email for Let's Encrypt.
        use_main_override: whether docker-compose-main.yml should be applied
            when rebuilding nginx.
    """
    state.set_step("checking_dns", "Проверка DNS")
    result = dns_check.check_domain_points_here(domain)
    if not result.matches:
        state.set_error(
            f"Домен {domain} указывает на {result.resolved_ip}, а сервер "
            f"отвечает за {result.server_ip}. Проверьте DNS-запись и "
            "повторите установку."
        )
        return

    state.set_step("issuing_certificate", "Выпуск сертификата Let's Encrypt")
    certbot_runner.issue_certificate(deploy_dir, domain, email)

    state.set_step("finalizing_tls", "Переключение на HTTPS")
    nginx_setup.write_final_config(repo_root, domain)
    compose_runner.bring_up_stack(deploy_dir, use_main_override, services=["nginx"])
