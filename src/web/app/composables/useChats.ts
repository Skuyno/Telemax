import type { UserResponse } from '~/types/auth'
import type {
  Chat,
  ChatMemberResponse,
  ChatResponse,
  Message,
  MessageResponse,
  UserSearchResult,
  WsEvent,
} from '~/types/chat'

const PAGE_SIZE = 50
const SEARCH_LIMIT = 20
const TYPING_THROTTLE_MS = 2500
const SAVED_TITLE = 'Избранное'

const lastTypingSentByChatId = new Map<string, number>()

/** Чаты, для которых уже идёт подгрузка старых сообщений, — чтобы скролл не слал дубли. */
const loadingOlder = new Set<string>()
/** Номер последнего поискового запроса: ответы на устаревшие запросы отбрасываем. */
let searchSeq = 0

function toMessage(raw: MessageResponse): Message {
  return {
    id: raw.id,
    chatId: raw.chat_id,
    senderId: raw.sender_id,
    body: raw.body,
    createdAt: raw.created_at,
    editedAt: raw.edited_at,
    isDeleted: raw.is_deleted,
    attachmentIds: raw.attachment_file_ids ?? [],
  }
}

function isPageActive(): boolean {
  return document.visibilityState === 'visible' && document.hasFocus()
}

function displayName(user: UserResponse): string {
  return user.display_name ?? user.username
}

export function useChats() {
  const api = useApi()
  const chatStore = useChatStore()

  async function loadChats() {
    const me = chatStore.meId
    if (!me) return

    chatStore.isLoadingChats = true
    chatStore.chatsError = ''
    try {
      const chats = await api<ChatResponse[]>('/chats')

      // Бэкенд не отдаёт собеседника в списке: берём участников каждого чата отдельно.
      const members = await Promise.all(
        chats.map((chat) => api<ChatMemberResponse[]>(`/chats/${chat.id}/members`)),
      )
      // Чат с самим собой — единственный участник это я.
      const peerIds = members.map(
        (list) => list.find((member) => member.user_id !== me)?.user_id ?? me,
      )

      const uniqueIds = [...new Set(peerIds)]
      const users = uniqueIds.length
        ? await api<UserResponse[]>('/users', { query: { ids: uniqueIds } })
        : []
      const userById = new Map(users.map((user) => [user.id, user]))

      chatStore.setChats(
        chats.map((chat, index): Chat => {
          const peer = userById.get(peerIds[index]!)
          const isSaved = peerIds[index] === me
          const title = isSaved
            ? SAVED_TITLE
            : peer
              ? displayName(peer)
              : 'Неизвестный пользователь'
          const last = chat.last_message
          return {
            id: chat.id,
            title,
            initials: toInitials(title),
            peerId: peerIds[index]!,
            avatarUrl: isSaved ? null : (peer?.avatar_url ?? null),
            unreadCount: chat.unread_count,
            isSaved,
            lastMessage: last
              ? {
                  body: last.body,
                  createdAt: last.created_at,
                  authorLabel: last.sender_id === me && !isSaved ? 'Вы' : undefined,
                }
              : undefined,
          }
        }),
      )
    } catch (e) {
      chatStore.chatsError = extractApiErrorMessage(e, 'Не удалось загрузить чаты')
    } finally {
      chatStore.isLoadingChats = false
    }
  }

  /** Последние сообщения чата. Бэкенд отдаёт новые→старые, в ленте нужно наоборот. */
  async function loadMessages(chatId: string) {
    const page = await api<MessageResponse[]>(`/chats/${chatId}/messages`, {
      query: { limit: PAGE_SIZE },
    })
    chatStore.setMessages(chatId, page.map(toMessage).reverse(), page.length === PAGE_SIZE)
  }

  async function loadOlderMessages(chatId: string) {
    const oldest = chatStore.messagesByChatId[chatId]?.[0]
    if (!oldest || !chatStore.hasMoreByChatId[chatId] || loadingOlder.has(chatId)) return

    loadingOlder.add(chatId)
    try {
      const page = await api<MessageResponse[]>(`/chats/${chatId}/messages`, {
        query: { limit: PAGE_SIZE, before_msg_id: oldest.id },
      })
      chatStore.prependMessages(chatId, page.map(toMessage).reverse(), page.length === PAGE_SIZE)
    } finally {
      loadingOlder.delete(chatId)
    }
  }

  async function sendMessage(chatId: string, body: string, attachmentIds: string[] = []) {
    const text = body.trim()
    if (!text && !attachmentIds.length) return

    const saved = await api<MessageResponse>(`/chats/${chatId}/messages`, {
      method: 'POST',
      // client_msg_id — ключ идемпотентности: повтор запроса не создаст дубль.
      body: { body: text, client_msg_id: crypto.randomUUID(), attachment_file_ids: attachmentIds },
    })
    chatStore.addMessage(toMessage(saved))
  }

  async function editMessage(chatId: string, messageId: string, body: string) {
    const saved = await api<MessageResponse>(`/chats/${chatId}/messages/${messageId}`, {
      method: 'PATCH',
      body: { body: body.trim() },
    })
    chatStore.patchMessage(chatId, messageId, toMessage(saved))
  }

  async function deleteMessage(chatId: string, messageId: string) {
    await api(`/chats/${chatId}/messages/${messageId}`, { method: 'DELETE' })
    chatStore.patchMessage(chatId, messageId, { isDeleted: true, body: '', attachmentIds: [] })
  }

  async function searchMessages(chatId: string, query: string): Promise<Message[]> {
    const found = await api<MessageResponse[]>(`/chats/${chatId}/messages/search`, {
      query: { query, limit: SEARCH_LIMIT },
    })
    return found.map(toMessage)
  }

  async function loadUntil(chatId: string, messageId: string): Promise<boolean> {
    for (let page = 0; page < 20; page++) {
      if (chatStore.messagesByChatId[chatId]?.some((item) => item.id === messageId)) return true
      if (!chatStore.hasMoreByChatId[chatId]) return false
      await loadOlderMessages(chatId)
    }
    return false
  }

  /** Поиск людей по началу username; себя из выдачи убираем. */
  async function searchUsers(raw: string) {
    const tag = raw.trim().replace(/^@/, '')
    const seq = ++searchSeq

    if (!tag) {
      chatStore.userResults = []
      chatStore.isSearchingUsers = false
      return
    }

    chatStore.isSearchingUsers = true
    try {
      const users = await api<UserResponse[]>('/users/search', {
        method: 'POST',
        body: { tag, limit: SEARCH_LIMIT },
      })
      if (seq !== searchSeq) return

      chatStore.userResults = users
        .filter((user) => user.id !== chatStore.meId)
        .map((user) => {
          const title = displayName(user)
          return {
            id: user.id,
            username: user.username,
            title,
            initials: toInitials(title),
            avatarUrl: user.avatar_url,
          }
        })
    } catch {
      if (seq === searchSeq) chatStore.userResults = []
    } finally {
      if (seq === searchSeq) chatStore.isSearchingUsers = false
    }
  }

  /** Открывает личный чат с человеком: бэкенд вернёт существующий или создаст новый. */
  async function openChatWith(user: UserSearchResult) {
    const chat = await api<{ id: string }>('/chats/direct', {
      method: 'POST',
      body: { peer_user_id: user.id },
    })

    if (!chatStore.chats.some((item) => item.id === chat.id)) {
      chatStore.setChats([
        ...chatStore.chats,
        {
          id: chat.id,
          title: user.title,
          initials: user.initials,
          peerId: user.id,
          avatarUrl: user.avatarUrl,
          unreadCount: 0,
        },
      ])
    }

    chatStore.setSearch('')
    chatStore.userResults = []
    chatStore.setActiveChat(chat.id)
  }

  async function openSavedChat() {
    const me = chatStore.meId
    if (!me) return

    const existing = chatStore.chats.find((item) => item.isSaved)
    if (existing) {
      chatStore.setActiveChat(existing.id)
      return
    }

    const chat = await api<{ id: string }>('/chats/direct', {
      method: 'POST',
      body: { peer_user_id: me },
    })

    if (!chatStore.chats.some((item) => item.id === chat.id)) {
      chatStore.setChats([
        ...chatStore.chats,
        {
          id: chat.id,
          title: SAVED_TITLE,
          initials: toInitials(SAVED_TITLE),
          peerId: me,
          avatarUrl: null,
          unreadCount: 0,
          isSaved: true,
        },
      ])
    }

    chatStore.setActiveChat(chat.id)
  }

  /**
   * Новое сообщение из ws-gateway. Приходит всем участникам чата, в том числе
   * отправителю: своё сообщение уже добавлено после REST-ответа, addMessage
   * отсеет дубль по id.
   */
  function handleRealtimeEvent(raw: unknown) {
    const event = raw as WsEvent | null
    if (!event?.type) return

    switch (event.type) {
      case 'message.created': {
        const { data } = event
        const isKnownChat = chatStore.chats.some((chat) => chat.id === data.chat_id)
        chatStore.addMessage({
          id: data.message_id,
          chatId: data.chat_id,
          senderId: data.sender_id,
          body: data.body,
          createdAt: data.created_at,
          editedAt: null,
          isDeleted: false,
          attachmentIds: [],
        })
        if (data.chat_id === chatStore.activeChatId && data.sender_id !== chatStore.meId) {
          syncAttachments(data.chat_id)
        }

        // Написал человек, с которым чата ещё нет в списке, — подтягиваем список заново.
        if (!isKnownChat) loadChats()
        else if (data.sender_id !== chatStore.meId) chatStore.stopTyping(data.chat_id)

        if (
          data.chat_id === chatStore.activeChatId &&
          data.sender_id !== chatStore.meId &&
          isPageActive()
        ) {
          markRead(data.chat_id, data.message_id)
        }
        break
      }
      case 'message.updated':
        chatStore.patchMessage(event.data.chat_id, event.data.message_id, {
          body: event.data.body,
          editedAt: event.data.edited_at,
        })
        break
      case 'message.deleted':
        chatStore.patchMessage(event.data.chat_id, event.data.message_id, {
          isDeleted: true,
          body: '',
          attachmentIds: [],
        })
        break
      case 'presence':
        chatStore.setOnline(event.data.user_id, event.data.status === 'online')
        break
      case 'typing':
        if (event.data.user_id !== chatStore.meId) chatStore.markTyping(event.data.chat_id)
        break
      case 'message.read':
        if (event.data.user_id !== chatStore.meId) {
          chatStore.setPeerRead(event.data.chat_id, event.data.last_read_message_id)
        }
        break
    }
  }

  async function syncAttachments(chatId: string) {
    const recent = await api<MessageResponse[]>(`/chats/${chatId}/messages`, {
      query: { limit: 20 },
    }).catch(() => [])
    for (const raw of recent) {
      if (raw.attachment_file_ids?.length) {
        chatStore.patchMessage(chatId, raw.id, { attachmentIds: raw.attachment_file_ids })
      }
    }
  }

  async function markRead(chatId: string, lastMessageId?: string) {
    const messageId = lastMessageId ?? chatStore.messagesByChatId[chatId]?.at(-1)?.id
    if (!messageId) return

    chatStore.clearUnread(chatId)
    await api(`/chats/${chatId}/read`, {
      method: 'POST',
      body: { last_read_message_id: messageId },
    }).catch(() => {})
  }

  function sendTyping(chatId: string) {
    const now = Date.now()
    if (now - (lastTypingSentByChatId.get(chatId) ?? 0) < TYPING_THROTTLE_MS) return

    lastTypingSentByChatId.set(chatId, now)
    api(`/chats/${chatId}/typing`, { method: 'POST' }).catch(() => {})
  }

  /** Пока сокет был оборван, сообщения могли прийти мимо нас — перечитываем с сервера. */
  async function resync() {
    await loadChats()
    const chatId = chatStore.activeChatId
    if (chatId) await loadMessages(chatId).catch(() => {})
  }

  return {
    loadChats,
    loadMessages,
    loadOlderMessages,
    sendMessage,
    searchUsers,
    openChatWith,
    openSavedChat,
    handleRealtimeEvent,
    resync,
    markRead,
    sendTyping,
    editMessage,
    deleteMessage,
    searchMessages,
    loadUntil,
  }
}
