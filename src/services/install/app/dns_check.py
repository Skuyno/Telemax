"""Checks whether a domain actually points at this server before issuing a cert.

This is a friendly early filter, not the authoritative proof — a typo'd
domain or DNS that hasn't propagated yet fails here with a clear message
instead of burning one of Let's Encrypt's limited attempts per domain/day.
The real proof is the HTTP-01 challenge itself in certbot_runner.py, which
travels over the real internet to this server's port 80.
"""

import socket
from dataclasses import dataclass
from urllib.request import urlopen

_PUBLIC_IP_SERVICE = "https://api.ipify.org"
_TIMEOUT_SECONDS = 5


class DnsCheckError(Exception):
    """Raised when the domain or this server's own public IP can't be found."""


@dataclass
class DomainCheckResult:
    """Outcome of comparing a domain's A record to this server's public IP."""

    domain: str
    resolved_ip: str
    server_ip: str

    @property
    def matches(self) -> bool:
        """Whether the domain's A record actually points at this server.

        Returns:
            bool: True if the resolved IP equals the server's public IP.
        """
        return self.resolved_ip == self.server_ip


def resolve_a_record(domain: str) -> str:
    """Resolve a domain's IPv4 (A record) address.

    Args:
        domain: the hostname to resolve.

    Returns:
        str: its IPv4 address.

    Raises:
        DnsCheckError: if the domain doesn't resolve at all.
    """
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror as exc:
        raise DnsCheckError(f"could not resolve {domain}: {exc}") from exc


def get_public_ip() -> str:
    """Determine this server's own public IP address.

    A container can't read its public IP off a local network interface (it
    only sees a private/NAT'd address), so this asks an external echo
    service for the address it was reached from instead.

    Returns:
        str: the server's public IPv4 address.

    Raises:
        DnsCheckError: if the echo service can't be reached.
    """
    try:
        with urlopen(_PUBLIC_IP_SERVICE, timeout=_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8").strip()
    except OSError as exc:
        message = f"could not determine this server's public IP: {exc}"
        raise DnsCheckError(message) from exc


def check_domain_points_here(domain: str) -> DomainCheckResult:
    """Compare a domain's A record against this server's own public IP.

    Args:
        domain: the hostname the user claims points at this server.

    Returns:
        DomainCheckResult: resolved vs. actual IP, and whether they match.

    Raises:
        DnsCheckError: if either lookup fails.
    """
    resolved_ip = resolve_a_record(domain)
    server_ip = get_public_ip()
    return DomainCheckResult(
        domain=domain, resolved_ip=resolved_ip, server_ip=server_ip
    )
