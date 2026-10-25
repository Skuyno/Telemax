"""Tests for the domain-points-here pre-check — network calls are mocked."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from app.dns_check import (
    DnsCheckError,
    check_domain_points_here,
    get_public_ip,
    resolve_a_record,
)


def _fake_response(body: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_resolve_a_record_returns_the_ip() -> None:
    """A resolvable domain's address is returned as-is."""
    with patch("app.dns_check.socket.gethostbyname", return_value="203.0.113.5"):
        assert resolve_a_record("example.com") == "203.0.113.5"


def test_resolve_a_record_raises_on_unresolvable_domain() -> None:
    """A domain that doesn't resolve fails with a clear, named error."""
    with patch(
        "app.dns_check.socket.gethostbyname",
        side_effect=socket.gaierror("not found"),
    ):
        with pytest.raises(DnsCheckError, match="example.invalid"):
            resolve_a_record("example.invalid")


def test_get_public_ip_strips_whitespace() -> None:
    """The echo service's response is trimmed before use."""
    with patch("app.dns_check.urlopen", return_value=_fake_response(b"203.0.113.9\n")):
        assert get_public_ip() == "203.0.113.9"


def test_get_public_ip_raises_when_echo_service_is_unreachable() -> None:
    """A network failure reaching the echo service becomes a DnsCheckError."""
    with patch("app.dns_check.urlopen", side_effect=OSError("timed out")):
        with pytest.raises(DnsCheckError):
            get_public_ip()


def test_check_domain_points_here_true_when_ips_match() -> None:
    """Matching A record and public IP reports matches=True."""
    with (
        patch("app.dns_check.resolve_a_record", return_value="203.0.113.5"),
        patch("app.dns_check.get_public_ip", return_value="203.0.113.5"),
    ):
        result = check_domain_points_here("example.com")

    assert result.matches is True


def test_check_domain_points_here_false_when_ips_differ() -> None:
    """A stale/wrong A record reports matches=False, with both IPs available."""
    with (
        patch("app.dns_check.resolve_a_record", return_value="203.0.113.5"),
        patch("app.dns_check.get_public_ip", return_value="198.51.100.1"),
    ):
        result = check_domain_points_here("example.com")

    assert result.matches is False
    assert result.resolved_ip == "203.0.113.5"
    assert result.server_ip == "198.51.100.1"
