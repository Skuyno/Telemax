"""NATS event publisher/subscriber for file-orchestrator.

Shares the "CHATS" JetStream stream with communication: this service
publishes file.upload.* events onto it (relayed onward by ws-gateway) and
subscribes to chat.message.deleted to garbage-collect attachment blobs.
"""

import json
import logging
from collections.abc import Awaitable, Callable

import nats
from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.js.errors import APIError

logger = logging.getLogger(__name__)

STREAM_SUBJECTS = ["chat.message.>", "file.upload.>"]


class NatsClient:
    """NATS wrapper for JetStream event publishing and subscribing."""

    def __init__(self):
        """Initialize NATS wrapper with uninitialized connections."""
        self.nc: NATS | None = None
        self.js: JetStreamContext | None = None

    async def connect(self, url: str):
        """Connect to NATS broker and ensure the shared JetStream stream exists.

        Args:
            url: NATS connection URL.

        Raises:
            APIError: If JetStream stream creation fails unexpectedly.
        """
        logger.info("Connecting to NATS at %s...", url)
        self.nc = await nats.connect(url)
        self.js = self.nc.jetstream()

        try:
            await self.js.add_stream(name="CHATS", subjects=STREAM_SUBJECTS)
            logger.info("Created JetStream stream 'CHATS'")
        except APIError as e:
            if "already in use" in str(e).lower() or e.err_code == 10058:
                await self.js.update_stream(name="CHATS", subjects=STREAM_SUBJECTS)
                logger.info("JetStream stream 'CHATS' exists, subjects refreshed")
            else:
                logger.error("Failed to create stream 'CHATS': %s", e)
                raise e

        logger.info("Successfully connected to NATS JetStream")

    async def close(self):
        """Gracefully drain and close NATS connection."""
        if self.nc:
            logger.info("Closing NATS connection...")
            await self.nc.drain()
            await self.nc.close()

    async def publish(self, subject: str, data: dict):
        """Publish an event to a NATS JetStream subject.

        Args:
            subject: Target NATS subject.
            data: Event payload dictionary.

        Raises:
            RuntimeError: If JetStream is not initialized.
        """
        if not self.js:
            logger.error("Cannot publish: JetStream is not initialized")
            raise RuntimeError("NATS JetStream is not connected")

        payload = json.dumps(data).encode("utf-8")
        await self.js.publish(subject, payload)

    async def subscribe(self, subject: str, handler: Callable[[dict], Awaitable[None]]):
        """Subscribe to a subject with a durable consumer, acking after handling.

        Args:
            subject: NATS subject to subscribe to.
            handler: Async callback invoked with the decoded JSON payload.
        """

        async def _on_message(msg):
            try:
                await handler(json.loads(msg.data))
            except Exception:
                logger.exception("Failed to handle NATS message on %s", msg.subject)
            finally:
                await msg.ack()

        await self.js.subscribe(
            subject, durable="file-orchestrator", cb=_on_message
        )


nats_client = NatsClient()
