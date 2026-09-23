import { defineStore } from 'pinia'
import type { UserSettings } from '~/types/settings'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    data: null as UserSettings | null,
    status: 'idle' as 'idle' | 'loading' | 'error',
  }),

  actions: {
    setSettings(settings: UserSettings) {
      this.data = settings
      this.status = 'idle'
    },

    reset() {
      this.data = null
      this.status = 'idle'
    },
  },
})
