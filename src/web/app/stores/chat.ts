import { defineStore } from 'pinia'
import type { Chat, Message, UserSearchResult } from '~/types/chat'

const TYPING_TTL_MS = 4000

function lastActivity(chat: Chat): string {
  return chat.lastMessage?.createdAt ?? ''
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    chats: [] as Chat[],
    messagesByChatId: {} as Record<string, Message[]>,
    /** Есть ли у чата сообщения старше уже загруженных. */
    hasMoreByChatId: {} as Record<string, boolean>,
    activeChatId: null as string | null,
    search: '',
    isLoadingChats: false,
    chatsError: '',
    /** Люди из POST /users/search по текущей строке поиска. */
    userResults: [] as UserSearchResult[],
    isSearchingUsers: false,
    /** Растёт при «Новый чат» — сайдбар по нему ставит фокус в поиск. */
    searchFocusTick: 0,
    onlineByUserId: {} as Record<string, boolean>,
    typingUntilByChatId: {} as Record<string, number>,
    peerReadMessageIdByChatId: {} as Record<string, string>,
    now: Date.now(),
  }),

  getters: {
    visibleChats: (state): Chat[] => {
      const query = state.search.trim().replace(/^@/, '').toLowerCase()
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

    isPeerOnline: (state) => (chat: Chat) =>
      !chat.isSaved && Boolean(state.onlineByUserId[chat.peerId]),

    isPeerTyping: (state) => (chatId: string) =>
      !state.chats.find((chat) => chat.id === chatId)?.isSaved &&
      (state.typingUntilByChatId[chatId] ?? 0) > state.now,

    isMessageRead: (state) => (message: Message) => {
      const readId = state.peerReadMessageIdByChatId[message.chatId]
      return Boolean(readId && message.id <= readId)
    },
  },

  actions: {
    /** Бэкенд отдаёт чаты без сортировки — сверху те, где писали последними. */
    setChats(chats: Chat[]) {
      this.chats = [...chats].sort((a, b) => lastActivity(b).localeCompare(lastActivity(a)))
    },

    setMessages(chatId: string, messages: Message[], hasMore: boolean) {
      this.messagesByChatId[chatId] = messages
      this.hasMoreByChatId[chatId] = hasMore
    },

    prependMessages(chatId: string, older: Message[], hasMore: boolean) {
      this.messagesByChatId[chatId] = [...older, ...(this.messagesByChatId[chatId] ?? [])]
      this.hasMoreByChatId[chatId] = hasMore
    },

    setSearch(search: string) {
      this.search = search
    },

    setActiveChat(chatId: string | null) {
      this.activeChatId = chatId
    },

    requestSearchFocus() {
      this.searchFocusTick++
    },

    setOnline(userId: string, online: boolean) {
      this.onlineByUserId[userId] = online
    },

    markTyping(chatId: string) {
      this.typingUntilByChatId[chatId] = Date.now() + TYPING_TTL_MS
      this.now = Date.now()
    },

    stopTyping(chatId: string) {
      delete this.typingUntilByChatId[chatId]
    },

    setPeerRead(chatId: string, messageId: string) {
      const current = this.peerReadMessageIdByChatId[chatId]
      if (!current || messageId > current) this.peerReadMessageIdByChatId[chatId] = messageId
    },

    clearUnread(chatId: string) {
      const chat = this.chats.find((item) => item.id === chatId)
      if (chat) chat.unreadCount = 0
    },

    tick() {
      this.now = Date.now()
    },

    /** Добавляет сообщение в ленту и поднимает чат наверх списка. */
    addMessage(message: Message) {
      const list = this.messagesByChatId[message.chatId] ?? []
      const existing = list.find((item) => item.id === message.id)
      if (existing) {
        if (message.attachmentIds.length && !existing.attachmentIds.length) {
          this.patchMessage(message.chatId, message.id, { attachmentIds: message.attachmentIds })
        }
        return
      }
      list.push(message)
      this.messagesByChatId[message.chatId] = [...list]

      const chat = this.chats.find((item) => item.id === message.chatId)
      if (chat) {
        chat.lastMessage = {
          body: message.body,
          createdAt: message.createdAt,
          authorLabel: message.senderId === this.meId && !chat.isSaved ? 'Вы' : undefined,
        }
        if (message.senderId !== this.meId && message.chatId !== this.activeChatId) {
          chat.unreadCount += 1
        }
        this.setChats(this.chats)
      }
    },

    patchMessage(chatId: string, messageId: string, patch: Partial<Message>) {
      const list = this.messagesByChatId[chatId]
      if (!list) return
      const index = list.findIndex((item) => item.id === messageId)
      if (index === -1) return

      const next = [...list]
      next[index] = { ...next[index]!, ...patch }
      this.messagesByChatId[chatId] = next

      const chat = this.chats.find((item) => item.id === chatId)
      if (chat && index === list.length - 1) {
        const updated = next[index]!
        chat.lastMessage = {
          body: updated.isDeleted ? 'Сообщение удалено' : updated.body,
          createdAt: updated.createdAt,
          authorLabel: updated.senderId === this.meId && !chat.isSaved ? 'Вы' : undefined,
        }
      }
    },

    reset() {
      this.$reset()
    },
  },
})
