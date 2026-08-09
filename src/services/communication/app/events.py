import json
import logging

import nats
from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.js.errors import APIError

logger = logging.getLogger(__name__)


class NatsClient:
    def __init__(self):
        self.nc: NATS | None = None
        self.js: JetStreamContext | None = None

    async def connect(self, url: str):
        logger.info("Connecting to NATS at %s...", url)
        self.nc = await nats.connect(url)
        self.js = self.nc.jetstream()

        try:
            await self.js.add_stream(name="CHATS", subjects=["chat.message.>"])
            logger.info("Created JetStream stream 'CHATS'")
        except APIError as e:
            if "already in use" in str(e).lower() or e.err_code == 10058:
                logger.info("JetStream stream 'CHATS' already exists")
            else:
                logger.error("Failed to create stream 'CHATS': %s", e)
                raise e

        logger.info("Succesfully connected to NATS JetStream")

    async def close(self):
        if self.nc:
            logger.info("Closing NATS connection...")
            await self.nc.drain()
            await self.nc.close()

    async def publish(self, subject: str, data: dict):
        if not self.js:
            logger.error("Cannot publish: JetStream is not initialized")
            raise RuntimeError("NATS JetStream is not connected")

        payload = json.dumps(data).encode("utf-8")
        await self.js.publish(subject, payload)
        logger.info("Published event to NATS subject '%s'", subject)


nats_client = NatsClient()
