import { defineStore } from 'pinia'
import type { AuthTokens, User } from '~/types/auth'

// 30 days: how long a web session survives without the user logging in
// again, as long as the refresh token itself hasn't been invalidated
// (e.g. by a password change, which bumps token_version server-side).
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30

function tokenCookie(name: 'access_token' | 'refresh_token') {
  return useCookie<string | null>(`telemax_${name}`, {
    maxAge: COOKIE_MAX_AGE,
    sameSite: 'lax',
    default: () => null,
  })
}

export const useAuthStore = defineStore('auth', {
  state: () => {
    // Read from cookies (not localStorage) so the very first server-rendered
    // page already knows about an existing session — no flash of the login
    // screen while the client catches up after a reload.
    const accessToken = tokenCookie('access_token')
    const refreshToken = tokenCookie('refresh_token')
    return {
      user: null as User | null,
      accessToken: accessToken.value,
      refreshToken: refreshToken.value,
    }
  },

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },

  actions: {
    setTokens(tokens: AuthTokens) {
      this.accessToken = tokens.accessToken
      this.refreshToken = tokens.refreshToken
      tokenCookie('access_token').value = tokens.accessToken
      tokenCookie('refresh_token').value = tokens.refreshToken
    },

    setUser(user: User) {
      this.user = user
    },

    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      tokenCookie('access_token').value = null
      tokenCookie('refresh_token').value = null
    },
  },
})
