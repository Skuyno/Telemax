/** Per-user app settings. Fields will grow as settings UI is built out. */
export interface UserSettings {
  theme: 'system' | 'light' | 'dark'
}

export function createDefaultUserSettings(): UserSettings {
  return {
    theme: 'system',
  }
}
