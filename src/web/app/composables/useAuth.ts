import type { TokenResponse, UserResponse } from '~/types/auth'

export function useAuth() {
  const api = useApi()
  const auth = useAuthStore()

  async function fetchMe() {
    const me = await api<UserResponse>('/me')
    auth.setUser({
      id: me.id,
      username: me.username,
      displayName: me.display_name,
      email: me.email,
    })
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
  }

  return { login, register, logout, fetchMe }
}
