"""Tests for writing nginx.conf across its three install-flow states."""

from pathlib import Path

from app.nginx_setup import (
    write_bootstrap_config,
    write_final_config,
    write_plain_config,
)


def _nginx_dir(repo_root: Path) -> Path:
    nginx_dir = repo_root / "src" / "services" / "nginx"
    nginx_dir.mkdir(parents=True)
    return nginx_dir


def test_write_plain_config_copies_the_no_domain_example(tmp_path: Path) -> None:
    """No domain -> nginx.conf is exactly nginx.local.conf.example's content."""
    nginx_dir = _nginx_dir(tmp_path)
    (nginx_dir / "nginx.local.conf.example").write_text(
        "server { listen 80; server_name _; }\n", encoding="utf-8"
    )

    write_plain_config(tmp_path)

    assert (nginx_dir / "nginx.conf").read_text(encoding="utf-8") == (
        "server { listen 80; server_name _; }\n"
    )


def test_write_bootstrap_config_copies_the_acme_challenge_example(
    tmp_path: Path,
) -> None:
    """Mid-issuance -> nginx.conf is exactly nginx.bootstrap.conf.example's content."""
    nginx_dir = _nginx_dir(tmp_path)
    (nginx_dir / "nginx.bootstrap.conf.example").write_text(
        "server { listen 80; location /.well-known/acme-challenge/ { } }\n",
        encoding="utf-8",
    )

    write_bootstrap_config(tmp_path)

    assert "acme-challenge" in (nginx_dir / "nginx.conf").read_text(encoding="utf-8")


def test_write_final_config_substitutes_every_domain_placeholder(
    tmp_path: Path,
) -> None:
    """Every YOUR_DOMAIN occurrence (bare and www.-prefixed) is replaced."""
    nginx_dir = _nginx_dir(tmp_path)
    (nginx_dir / "nginx.conf.example").write_text(
        "server_name YOUR_DOMAIN www.YOUR_DOMAIN;\n"
        "ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;\n",
        encoding="utf-8",
    )

    write_final_config(tmp_path, domain="telemx.mooo.com")

    rendered = (nginx_dir / "nginx.conf").read_text(encoding="utf-8")
    assert "YOUR_DOMAIN" not in rendered
    assert "server_name telemx.mooo.com www.telemx.mooo.com;" in rendered
    assert "/etc/letsencrypt/live/telemx.mooo.com/fullchain.pem" in rendered
