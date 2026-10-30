"""Writes nginx.conf for each state the install flow passes through.

nginx.conf is gitignored and COPYed into the nginx image at build time (not
bind-mounted at runtime) — on a fresh clone it doesn't exist at all yet, so
*some* version of it must be written before the stack can even build,
regardless of whether a domain/TLS is ever used. Three states:

- no domain: plain HTTP, same as the hand-maintained local config this
  replaces.
- issuing a certificate: a temporary HTTP-only config (ACME-challenge
  location only, no 443 block — nginx won't start at all if a 443 block
  references a certificate file that doesn't exist yet).
- done: the final HTTPS config, domain substituted in.
"""

from pathlib import Path

_DOMAIN_PLACEHOLDER = "YOUR_DOMAIN"


def _nginx_dir(repo_root: Path) -> Path:
    """Locate the nginx service directory inside the repo.

    Args:
        repo_root: absolute path to the repository root.

    Returns:
        Path: `<repo_root>/src/services/nginx`.
    """
    return repo_root / "src" / "services" / "nginx"


def write_plain_config(repo_root: Path) -> None:
    """Write the no-domain, plain-HTTP nginx.conf.

    Args:
        repo_root: absolute path to the repository root.
    """
    nginx_dir = _nginx_dir(repo_root)
    content = (nginx_dir / "nginx.local.conf.example").read_text(encoding="utf-8")
    (nginx_dir / "nginx.conf").write_text(content, encoding="utf-8")


def write_bootstrap_config(repo_root: Path) -> None:
    """Write the temporary HTTP-only config used while a certificate is issued.

    Args:
        repo_root: absolute path to the repository root.
    """
    nginx_dir = _nginx_dir(repo_root)
    content = (nginx_dir / "nginx.bootstrap.conf.example").read_text(encoding="utf-8")
    (nginx_dir / "nginx.conf").write_text(content, encoding="utf-8")


def write_final_config(repo_root: Path, domain: str) -> None:
    """Write the final HTTPS config once a certificate has been issued.

    Args:
        repo_root: absolute path to the repository root.
        domain: the domain the certificate was issued for.
    """
    nginx_dir = _nginx_dir(repo_root)
    content = (nginx_dir / "nginx.conf.example").read_text(encoding="utf-8")
    rendered = content.replace(_DOMAIN_PLACEHOLDER, domain)
    (nginx_dir / "nginx.conf").write_text(rendered, encoding="utf-8")
