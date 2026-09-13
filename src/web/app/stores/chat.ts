import { defineStore } from 'pinia'
import type { Chat, Message } from '~/types/chat'

export const useChatStore = defineStore('chat', {
  state: () => ({
    chats: [] as Chat[],
    messagesByChatId: {} as Record<string, Message[]>,
    activeChatId: null as string | null,
  }),

  getters: {
    activeMessages: (state) =>
      state.activeChatId ? state.messagesByChatId[state.activeChatId] ?? [] : [],
  },

  actions: {
    setChats(chats: Chat[]) {
      this.chats = chats
    },

    setActiveChat(chatId: string) {
      this.activeChatId = chatId
    },

    addMessage(message: Message) {
      const list = this.messagesByChatId[message.chatId] ?? []
      list.push(message)
      this.messagesByChatId[message.chatId] = list
    },
  },
})
