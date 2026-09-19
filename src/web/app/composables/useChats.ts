import type { UserResponse } from '~/types/auth'
import type {
  Chat,
  ChatMemberResponse,
  ChatResponse,
  Message,
  MessageCreatedEvent,
  MessageResponse,
  UserSearchResult,
} from '~/types/chat'

const PAGE_SIZE = 50
const SEARCH_LIMIT = 20

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
  }
}

function isMessageCreated(event: unknown): event is MessageCreatedEvent {
  return (event as MessageCreatedEvent | null)?.type === 'message.created'
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
      const nameById = new Map(users.map((user) => [user.id, displayName(user)]))

      chatStore.setChats(
        chats.map((chat, index): Chat => {
          const title = nameById.get(peerIds[index]!) ?? 'Неизвестный пользователь'
          const last = chat.last_message
          return {
            id: chat.id,
            title,
            initials: toInitials(title),
            lastMessage: last
              ? {
                  body: last.body,
                  createdAt: last.created_at,
                  authorLabel: last.sender_id === me ? 'Вы' : undefined,
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

  async function sendMessage(chatId: string, body: string) {
    const text = body.trim()
    if (!text) return

    const saved = await api<MessageResponse>(`/chats/${chatId}/messages`, {
      method: 'POST',
      // client_msg_id — ключ идемпотентности: повтор запроса не создаст дубль.
      body: { body: text, client_msg_id: crypto.randomUUID() },
    })
    chatStore.addMessage(toMessage(saved))
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
          return { id: user.id, username: user.username, title, initials: toInitials(title) }
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
        { id: chat.id, title: user.title, initials: user.initials },
      ])
    }

    chatStore.setSearch('')
    chatStore.userResults = []
    chatStore.setActiveChat(chat.id)
  }

  /**
   * Новое сообщение из ws-gateway. Приходит всем участникам чата, в том числе
   * отправителю: своё сообщение уже добавлено после REST-ответа, addMessage
   * отсеет дубль по id.
   */
  function handleRealtimeEvent(event: unknown) {
    if (!isMessageCreated(event)) return
    const { data } = event

    const isKnownChat = chatStore.chats.some((chat) => chat.id === data.chat_id)
    chatStore.addMessage({
      id: data.message_id,
      chatId: data.chat_id,
      senderId: data.sender_id,
      body: data.body,
      createdAt: data.created_at,
    })

    // Написал человек, с которым чата ещё нет в списке, — подтягиваем список заново.
    if (!isKnownChat) loadChats()
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
    handleRealtimeEvent,
    resync,
  }
}
