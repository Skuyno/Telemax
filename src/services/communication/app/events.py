"""NATS event publisher module."""

import json
import logging

import nats
from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.js.errors import APIError

logger = logging.getLogger(__name__)


class NatsClient:
    """NATS wrapper for JetStream event publishing."""

    def __init__(self):
        """Initialize NATS wrapper with uninitialized connections."""
        self.nc: NATS | None = None
        self.js: JetStreamContext | None = None

    async def connect(self, url: str):
        """Connect to NATS broker and initialize JetStream stream.

        Args:
            url: NATS connection URL

        Raises:
            APIError: If JetStream stream creation is failed unexpectedly.
        """
        logger.info("Connecting to NATS at %s...", url)
        self.nc = await nats.connect(url)
        self.js = self.nc.jetstream()

        subjects = ["chat.message.>", "file.upload.>"]
        try:
            await self.js.add_stream(name="CHATS", subjects=subjects)
            logger.info("Created JetStream stream 'CHATS'")
        except APIError as e:
            if "already in use" in str(e).lower() or e.err_code == 10058:
                # Stream already exists (created by us or file-orchestrator on
                # a previous boot) — make sure its subject list is current.
                await self.js.update_stream(name="CHATS", subjects=subjects)
                logger.info("JetStream stream 'CHATS' exists, subjects refreshed")
            else:
                logger.error("Failed to create stream 'CHATS': %s", e)
                raise e

        logger.info("Succesfully connected to NATS JetStream")

    async def close(self):
        """Gracefully drain and close NATS connection."""
        if self.nc:
            logger.info("Closing NATS connection...")
            await self.nc.drain()
            await self.nc.close()

    async def publish(self, subject: str, data: dict):
        """Publish a event to a NATS JetStream subject.

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
        logger.info("Published event to NATS subject '%s'", subject)


nats_client = NatsClient()
