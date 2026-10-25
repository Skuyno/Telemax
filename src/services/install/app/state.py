"""Tracks progress of the one background installation run.

A single process, single concurrent install — module-level state guarded by
a lock is enough; no database or per-session concept is needed here.
"""

import threading
from dataclasses import dataclass


@dataclass
class InstallState:
    """A snapshot of the install flow's current progress."""

    step: str = "idle"
    message: str = ""
    error: str | None = None
    running: bool = False


_lock = threading.Lock()
_state = InstallState()


def get_state() -> InstallState:
    """Return a snapshot of the current install state.

    Returns:
        InstallState: a copy, safe to read without holding the lock.
    """
    with _lock:
        return InstallState(**vars(_state))


def set_step(step: str, message: str = "") -> None:
    """Advance the state machine to a new step.

    Args:
        step: the step's machine-readable name (e.g. "writing_env").
        message: an optional human-readable detail for the UI.
    """
    with _lock:
        _state.step = step
        _state.message = message
        _state.running = True
        _state.error = None


def set_error(message: str) -> None:
    """Record a failure, stopping the run without crashing the process.

    Args:
        message: the error text to show the user.
    """
    with _lock:
        _state.error = message
        _state.running = False


def set_done() -> None:
    """Mark the install flow as finished successfully."""
    with _lock:
        _state.step = "done"
        _state.running = False


def is_running() -> bool:
    """Whether a background installation is currently in progress.

    Returns:
        bool: True if a background run is currently in progress.
    """
    with _lock:
        return _state.running


def reset() -> None:
    """Reset to the idle state — used before starting a new run."""
    global _state
    with _lock:
        _state = InstallState()
