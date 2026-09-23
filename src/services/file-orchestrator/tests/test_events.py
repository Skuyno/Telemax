"""Tests for NatsClient's ack/nak behavior on the subscribe handler."""

import json
from unittest.mock import AsyncMock, MagicMock

from app.events import NatsClient


async def _subscribe_and_capture_callback(client: NatsClient, handler):
    """Wire a fake js.subscribe that just captures the callback it's given."""
    captured = {}

    async def fake_subscribe(subject, durable, cb):
        captured["cb"] = cb

    client.js = MagicMock()
    client.js.subscribe = fake_subscribe
    await client.subscribe("some.subject", handler)
    return captured["cb"]


def _fake_message() -> MagicMock:
    msg = MagicMock()
    msg.data = json.dumps({"foo": "bar"}).encode("utf-8")
    msg.subject = "some.subject"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    return msg


async def test_subscribe_acks_after_a_successful_handler():
    """A message is ack'd once the handler completes without error."""
    handler = AsyncMock()
    on_message = await _subscribe_and_capture_callback(NatsClient(), handler)

    msg = _fake_message()
    await on_message(msg)

    handler.assert_awaited_once_with({"foo": "bar"})
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_called()


async def test_subscribe_naks_instead_of_acking_on_handler_failure():
    """A failing handler must nak, not silently ack and drop the message.

    E.g. a blob delete that couldn't reach storage.
    """
    handler = AsyncMock(side_effect=RuntimeError("storage unreachable"))
    on_message = await _subscribe_and_capture_callback(NatsClient(), handler)

    msg = _fake_message()
    await on_message(msg)

    msg.nak.assert_awaited_once()
    msg.ack.assert_not_called()
