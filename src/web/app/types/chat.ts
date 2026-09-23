export interface ChatPreview {
  body: string
  createdAt: string
  authorLabel?: string
}

export interface Chat {
  id: string
  title: string
  initials: string
  peerId: string
  avatarUrl: string | null
  unreadCount: number
  isSaved?: boolean
  lastMessage?: ChatPreview
}

export interface Message {
  id: string
  chatId: string
  senderId: string
  body: string
  createdAt: string
  editedAt: string | null
  isDeleted: boolean
  attachmentIds: string[]
}

export interface Attachment {
  id: string
  name: string
  type: string
  size: number
  url: string
}

export interface PendingUpload {
  key: string
  name: string
  size: number
  progress: number
  fileId: string | null
  error: string
}

/** Пользователь из поиска — чтобы начать с ним чат. */
export interface UserSearchResult {
  id: string
  username: string
  title: string
  initials: string
  avatarUrl: string | null
}

/** Raw response shape from GET /chats */
export interface ChatResponse {
  id: string
  unread_count: number
  last_message: {
    body: string
    sender_id: string
    created_at: string
  } | null
}

/** Raw response shape from GET /chats/{id}/members */
export interface ChatMemberResponse {
  user_id: string
  role: string
  joined_at: string
}

/** Raw response shape from GET/POST /chats/{id}/messages */
export interface MessageResponse {
  id: string
  chat_id: string
  sender_id: string
  body: string
  edited_at: string | null
  is_deleted: boolean
  created_at: string
  attachment_file_ids: string[]
}

export interface FileResponse {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  status: string
}

/**
 * Событие из ws-gateway о новом сообщении.
 * Внимание: id здесь называется `message_id`, а не `id`, как в REST.
 */
export interface MessageCreatedEvent {
  type: 'message.created'
  data: {
    message_id: string
    chat_id: string
    sender_id: string
    body: string
    created_at: string
  }
}

export interface PresenceEvent {
  type: 'presence'
  data: {
    user_id: string
    status: 'online' | 'offline'
  }
}

export interface TypingEvent {
  type: 'typing'
  data: {
    chat_id: string
    user_id: string
  }
}

export interface MessageReadEvent {
  type: 'message.read'
  data: {
    chat_id: string
    user_id: string
    last_read_message_id: string
  }
}

export interface MessageUpdatedEvent {
  type: 'message.updated'
  data: {
    message_id: string
    chat_id: string
    sender_id: string
    body: string
    edited_at: string | null
    created_at: string
  }
}

export interface MessageDeletedEvent {
  type: 'message.deleted'
  data: {
    message_id: string
    chat_id: string
    sender_id: string
  }
}

export type WsEvent =
  | MessageCreatedEvent
  | MessageUpdatedEvent
  | MessageDeletedEvent
  | PresenceEvent
  | TypingEvent
  | MessageReadEvent
