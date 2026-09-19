export interface ChatPreview {
  body: string
  createdAt: string
  authorLabel?: string
}

export interface Chat {
  id: string
  title: string
  initials: string
  lastMessage?: ChatPreview
}

export interface Message {
  id: string
  chatId: string
  senderId: string
  body: string
  createdAt: string
}

/** Пользователь из поиска — чтобы начать с ним чат. */
export interface UserSearchResult {
  id: string
  username: string
  title: string
  initials: string
}

/** Raw response shape from GET /chats */
export interface ChatResponse {
  id: string
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

/** Raw response shape from GET/POST /chats/{id}/messages */
export interface MessageResponse {
  id: string
  chat_id: string
  sender_id: string
  body: string
  created_at: string
}
