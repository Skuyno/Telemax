import type { TokenResponse, UserResponse } from '~/types/auth'

export function useAuth() {
  const api = useApi()
  const auth = useAuthStore()

  function applyUser(me: UserResponse) {
    auth.setUser({
      id: me.id,
      username: me.username,
      displayName: me.display_name,
      email: me.email,
      avatarUrl: me.avatar_url,
      createdAt: me.created_at,
    })
  }

  async function fetchMe() {
    applyUser(await api<UserResponse>('/me'))
  }

  async function updateProfile(patch: { displayName?: string; email?: string }) {
    const body: Record<string, string> = {}
    if (patch.displayName !== undefined) body.display_name = patch.displayName
    if (patch.email !== undefined) body.email = patch.email
    if (!Object.keys(body).length) return

    applyUser(await api<UserResponse>('/me', { method: 'PATCH', body }))
  }

  async function uploadAvatar(file: File) {
    applyUser(
      await api<UserResponse>('/me/avatar', {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type },
      }),
    )
  }

  async function removeAvatar() {
    applyUser(await api<UserResponse>('/me/avatar', { method: 'DELETE' }))
  }

  async function login(username: string, password: string) {
    const tokens = await api<TokenResponse>('/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    auth.setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token })
    await fetchMe()
  }

  async function register(username: string, password: string) {
    await api('/auth/register', {
      method: 'POST',
      body: { username, password },
    })
    // Registration only creates the account; log in right after to get tokens.
    await login(username, password)
  }

  function logout() {
    auth.logout()
    useSettingsStore().reset()
  }

  return { login, register, logout, fetchMe, updateProfile, uploadAvatar, removeAvatar }
}
