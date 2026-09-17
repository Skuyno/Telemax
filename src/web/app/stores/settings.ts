import { defineStore } from 'pinia'
import { createDefaultUserSettings, type UserSettings } from '~/types/settings'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    /** Settings keyed by user id, so each account keeps its own preferences. */
    byUserId: {} as Record<string, UserSettings>,
  }),

  getters: {
    /** Current user's settings, created on first access. */
    current: (state) => {
      const auth = useAuthStore()
      if (!auth.user) return null
      return state.byUserId[auth.user.id] ?? createDefaultUserSettings()
    },
  },

  actions: {
    update(userId: string, patch: Partial<UserSettings>) {
      const existing = this.byUserId[userId] ?? createDefaultUserSettings()
      this.byUserId[userId] = { ...existing, ...patch }
    },
  },
})
