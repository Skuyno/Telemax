"""Tests for the in-memory install progress state machine."""

from app import state


def setup_function() -> None:
    """Reset the shared module-level state before each test."""
    state.reset()


def test_initial_state_is_idle() -> None:
    """A fresh process starts idle, not running."""
    current = state.get_state()
    assert current.step == "idle"
    assert current.running is False


def test_set_step_marks_running_and_clears_any_error() -> None:
    """Advancing a step always marks the run as in progress."""
    state.set_error("boom")

    state.set_step("writing_env", "Запись .env")

    current = state.get_state()
    assert current.step == "writing_env"
    assert current.message == "Запись .env"
    assert current.running is True
    assert current.error is None


def test_set_error_stops_running_without_clearing_the_step() -> None:
    """An error records the message and stops `running`, step stays put."""
    state.set_step("issuing_certificate")

    state.set_error("DNS mismatch")

    current = state.get_state()
    assert current.step == "issuing_certificate"
    assert current.error == "DNS mismatch"
    assert current.running is False


def test_set_done_marks_finished() -> None:
    """Completion sets step to 'done' and stops `running`."""
    state.set_step("finalizing_tls")

    state.set_done()

    current = state.get_state()
    assert current.step == "done"
    assert current.running is False


def test_is_running_reflects_current_state() -> None:
    """is_running tracks set_step/set_error/set_done without a full snapshot."""
    assert state.is_running() is False

    state.set_step("building")
    assert state.is_running() is True

    state.set_done()
    assert state.is_running() is False


def test_get_state_returns_a_snapshot_not_a_live_reference() -> None:
    """Mutating the returned snapshot must not affect the real state."""
    snapshot = state.get_state()
    snapshot.step = "tampered"

    assert state.get_state().step != "tampered"


def test_reset_returns_to_idle() -> None:
    """reset() discards any progress/error from a previous run."""
    state.set_error("previous failure")

    state.reset()

    current = state.get_state()
    assert current.step == "idle"
    assert current.error is None
    assert current.running is False
