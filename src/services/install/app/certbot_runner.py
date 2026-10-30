"""Runs a one-off certbot container to issue a Let's Encrypt certificate.

Issued the same way as the manual deploy process this automates: a
throwaway `certbot/certbot` container sharing the webroot and
certificate-storage volumes already declared in docker-compose.yml.
"""

import subprocess
from pathlib import Path


class CertbotError(Exception):
    """Raised when the certbot invocation fails."""


def _volume_name(deploy_dir: Path, suffix: str) -> str:
    """Build a Compose-managed volume's full, real name.

    Docker Compose names a volume `<project>_<suffix>` by default, where
    the project is the basename of the directory holding the compose file
    — not whatever name someone assumes (this bit a manual certbot run
    earlier in the project for exactly that reason).

    Args:
        deploy_dir: the `deploy/` directory holding the compose files.
        suffix: the volume's name as declared under `volumes:` in compose.

    Returns:
        str: the volume's actual name as Docker sees it.
    """
    return f"{deploy_dir.name}_{suffix}"


def issue_certificate(deploy_dir: Path, domain: str, email: str) -> None:
    """Obtain a certificate for `domain` via the HTTP-01 webroot challenge.

    This is the authoritative proof that the domain really points here —
    unlike dns_check.py's pre-check, this request travels over the real
    internet to this server's port 80.

    Args:
        deploy_dir: the `deploy/` directory holding the compose files (used
            to derive the shared volumes' real names).
        domain: the domain to issue a certificate for.
        email: contact address Let's Encrypt associates with the cert.

    Raises:
        CertbotError: if certbot exits non-zero (e.g. DNS doesn't actually
            point here yet, or Let's Encrypt's rate limit was hit).
    """
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{_volume_name(deploy_dir, 'certbot_www')}:/var/www/certbot",
        "-v",
        f"{_volume_name(deploy_dir, 'certbot_conf')}:/etc/letsencrypt",
        "certbot/certbot",
        "certonly",
        "--webroot",
        "-w",
        "/var/www/certbot",
        "-d",
        domain,
        "--email",
        email,
        "--agree-tos",
        "--non-interactive",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise CertbotError(result.stderr or result.stdout)
