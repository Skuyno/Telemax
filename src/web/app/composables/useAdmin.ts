import type { Role, UserResponse } from '~/types/auth'

export function useAdmin() {
  const api = useApi()

  /** GET /admin/accounts/username-available — for real-time validation while typing. */
  async function checkUsernameAvailable(username: string): Promise<boolean> {
    const resp = await api<{ available: boolean }>('/admin/accounts/username-available', {
      query: { username },
    })
    return resp.available
  }

  async function createAccount(data: {
    username: string
    password: string
    role: Role
  }): Promise<UserResponse> {
    return api<UserResponse>('/admin/accounts', {
      method: 'POST',
      body: data,
    })
  }

  return { checkUsernameAvailable, createAccount }
}
