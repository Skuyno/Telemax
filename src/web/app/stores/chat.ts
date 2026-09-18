import { defineStore } from 'pinia'
import type { Chat, Message } from '~/types/chat'

/*
  Стор пустой по умолчанию: данные появятся, когда будет готов бэкенд.
  Никаких моков — страница показывает честное пустое состояние.

  Точки подключения (всё через gateway, useApi уже шлёт Bearer):
    loadChats()    → GET /chats              → [{ id, last_message }]
                     GET /chats/{id}/members → user_id участников
                     GET /users?ids=…        → имена участников (title/initials)
    loadMessages() → GET /chats/{id}/messages?limit=50&before_msg_id=… (новые→старые, развернуть)
    sendMessage()  → POST /chats/{id}/messages { body, client_msg_id: uuid }

  Чего на бэкенде пока нет, поэтому нет и в UI: непрочитанные, групповые чаты,
  закреплённые сообщения, статусы прочтения, presence/«печатает», поиск людей.
*/
export const useChatStore = defineStore('chat', {
  state: () => ({
    chats: [] as Chat[],
    messagesByChatId: {} as Record<string, Message[]>,
    activeChatId: null as string | null,
    search: '',
  }),

  getters: {
    /** Локальная фильтрация уже загруженного списка: поиска людей на бэкенде нет. */
    visibleChats: (state): Chat[] => {
      const query = state.search.trim().toLowerCase()
      if (!query) return state.chats
      return state.chats.filter((chat) => chat.title.toLowerCase().includes(query))
    },

    activeChat: (state): Chat | null =>
      state.chats.find((chat) => chat.id === state.activeChatId) ?? null,

    activeMessages: (state): Message[] =>
      state.activeChatId ? (state.messagesByChatId[state.activeChatId] ?? []) : [],

    /** Кто «я» — по нему сообщение считается исходящим. */
    meId(): string | null {
      return useAuthStore().user?.id ?? null
    },
  },

  actions: {
    setChats(chats: Chat[]) {
      this.chats = chats
    },

    setMessages(chatId: string, messages: Message[]) {
      this.messagesByChatId[chatId] = messages
    },

    setSearch(search: string) {
      this.search = search
    },

    setActiveChat(chatId: string | null) {
      this.activeChatId = chatId
    },

    addMessage(message: Message) {
      const list = this.messagesByChatId[message.chatId] ?? []
      list.push(message)
      this.messagesByChatId[message.chatId] = list
    },

    /** Пока только локально добавляет сообщение в ленту; отправка на сервер — позже. */
    sendMessage(body: string) {
      const chatId = this.activeChatId
      const senderId = this.meId
      const text = body.trim()
      if (!chatId || !senderId || !text) return

      const message: Message = {
        id: `local-${Date.now()}`,
        chatId,
        senderId,
        body: text,
        createdAt: new Date().toISOString(),
      }
      this.addMessage(message)

      const chat = this.chats.find((item) => item.id === chatId)
      if (chat) {
        chat.lastMessage = { body: text, createdAt: message.createdAt, authorLabel: 'Вы' }
      }
    },
  },
})
