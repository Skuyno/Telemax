"""Data access layer for chats."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.models import Chat, ChatMember, DirectChat, Message


async def get_direct_chat(db: AsyncSession, user_a: UUID, user_b: UUID) -> Chat | None:
    """Look up an existing direct chat between two users.

    Args:
        db: Async database session.
        user_a: One of the two participants, in either order.
        user_b: The other participant, in either order.

    Returns:
        Chat | None: The chat if found, otherwise None.
    """
    user_lo, user_hi = sorted([user_a, user_b])
    result = await db.execute(
        select(Chat)
        .join(DirectChat, Chat.id == DirectChat.chat_id)
        .where(DirectChat.user_lo == user_lo, DirectChat.user_hi == user_hi)
    )
    return result.scalar_one_or_none()


async def create_direct_chat(
    db: AsyncSession,
    creator_id: UUID,
    peer_id: UUID,
) -> Chat:
    """Create a chat with its direct-chat and membership rows in one transaction.

    Args:
        db: Async database session.
        creator_id: User initiating the chat.
        peer_id: The other participant (equal to creator_id for a self-chat).

    Returns:
        Chat: The newly created chat.

    Raises:
        IntegrityError: If a direct chat between this pair already exists.
    """
    user_lo, user_hi = sorted([creator_id, peer_id])
    chat = Chat(created_by=creator_id)
    db.add(chat)
    await db.flush()
    if creator_id == peer_id:
        members = [ChatMember(chat_id=chat.id, user_id=creator_id)]
    else:
        members = [
            ChatMember(chat_id=chat.id, user_id=creator_id),
            ChatMember(chat_id=chat.id, user_id=peer_id),
        ]
    db.add_all(
        [*members, DirectChat(chat_id=chat.id, user_lo=user_lo, user_hi=user_hi)]
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    return chat


async def list_user_chats(
    db: AsyncSession,
    user_id: UUID,
) -> Sequence[Chat]:
    """Look up all chats the given user is a member of.

    Args:
        db: Async database session.
        user_id: Id of the user to look up chats for.

    Returns:
        Sequence[Chat]: All chats the user is a member of.
    """
    result = await db.execute(
        select(Chat)
        .join(ChatMember, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == user_id)
    )

    return result.scalars().all()


async def get_last_messages(
    db: AsyncSession, chat_ids: Sequence[UUID]
) -> dict[UUID, Message]:
    """Look up the most recent message for each of the given chats.

    Args:
        db: Async database session.
        chat_ids: Chats to look up the last message for.

    Returns:
        dict[UUID, Message]: Latest message per chat id; chats with no
        messages yet are simply absent from the dict.
    """
    result = await db.execute(
        select(Message)
        .where(Message.chat_id.in_(chat_ids))
        .distinct(Message.chat_id)
        .order_by(Message.chat_id, Message.created_at.desc())
    )
    return {message.chat_id: message for message in result.scalars().all()}

