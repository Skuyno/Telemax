import { defineStore } from 'pinia'
import type { AuthTokens, User } from '~/types/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    accessToken: null as string | null,
    refreshToken: null as string | null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },

  actions: {
    setTokens(tokens: AuthTokens) {
      this.accessToken = tokens.accessToken
      this.refreshToken = tokens.refreshToken
    },

    setUser(user: User) {
      this.user = user
    },

    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
    },
  },
})
