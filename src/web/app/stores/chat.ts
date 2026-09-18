import { defineStore } from 'pinia'
import type { Chat, Message, UserSearchResult } from '~/types/chat'

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

    /** Добавляет сообщение в ленту и поднимает чат наверх списка. */
    addMessage(message: Message) {
      const list = this.messagesByChatId[message.chatId] ?? []
      if (list.some((item) => item.id === message.id)) return
      list.push(message)
      this.messagesByChatId[message.chatId] = [...list]

      const chat = this.chats.find((item) => item.id === message.chatId)
      if (chat) {
        chat.lastMessage = {
          body: message.body,
          createdAt: message.createdAt,
          authorLabel: message.senderId === this.meId ? 'Вы' : undefined,
        }
        this.setChats(this.chats)
      }
    },

    reset() {
      this.$reset()
    },
  },
})
