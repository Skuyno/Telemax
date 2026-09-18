/** Global user settings, mirrors GET/PATCH /me/settings on the identity service. */
export interface UserSettings {
  notificationsEnabled: boolean
  acceptCalls: boolean
}

/** Raw response shape from GET/PATCH /me/settings */
export interface UserSettingsResponse {
  user_id: string
  notifications_enabled: boolean
  accept_calls: boolean
}

export interface UserSettingsUpdate {
  notificationsEnabled?: boolean
  acceptCalls?: boolean
}
