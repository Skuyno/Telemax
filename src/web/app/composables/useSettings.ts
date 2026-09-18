import type { UserSettings, UserSettingsResponse, UserSettingsUpdate } from '~/types/settings'

function fromResponse(res: UserSettingsResponse): UserSettings {
  return {
    notificationsEnabled: res.notifications_enabled,
    acceptCalls: res.accept_calls,
  }
}

export function useSettings() {
  const api = useApi()
  const store = useSettingsStore()

  async function load() {
    store.status = 'loading'
    try {
      const res = await api<UserSettingsResponse>('/me/settings')
      store.setSettings(fromResponse(res))
    } catch (e) {
      store.status = 'error'
      throw e
    }
  }

  async function update(patch: UserSettingsUpdate) {
    const body: Record<string, boolean> = {}
    if (patch.notificationsEnabled !== undefined) {
      body.notifications_enabled = patch.notificationsEnabled
    }
    if (patch.acceptCalls !== undefined) {
      body.accept_calls = patch.acceptCalls
    }

    const res = await api<UserSettingsResponse>('/me/settings', {
      method: 'PATCH',
      body,
    })
    store.setSettings(fromResponse(res))
  }

  return { load, update }
}
