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

  /** GET /admin/accounts — the full account list for the management screen. */
  async function listAccounts(): Promise<UserResponse[]> {
    return api<UserResponse[]>('/admin/accounts', { query: { limit: 200 } })
  }

  async function deleteAccount(accountId: string): Promise<void> {
    await api(`/admin/accounts/${accountId}`, { method: 'DELETE' })
  }

  async function blockAccount(accountId: string): Promise<UserResponse> {
    return api<UserResponse>(`/admin/accounts/${accountId}/block`, { method: 'POST' })
  }

  async function unblockAccount(accountId: string): Promise<UserResponse> {
    return api<UserResponse>(`/admin/accounts/${accountId}/unblock`, { method: 'POST' })
  }

  /** Admin-initiated reset — no current password needed, unlike the self-service one. */
  async function resetAccountPassword(
    accountId: string,
    newPassword: string,
  ): Promise<UserResponse> {
    return api<UserResponse>(`/admin/accounts/${accountId}/password`, {
      method: 'POST',
      body: { new_password: newPassword },
    })
  }

  /** Ensures the caller's own "Уведомления" chat exists — call before uploading attachments. */
  async function getBroadcastChat(): Promise<string> {
    const resp = await api<{ chat_id: string }>('/admin/broadcast/chat', { method: 'POST' })
    return resp.chat_id
  }

  /** Sends body + already-uploaded attachments to every user's own "Уведомления" chat. */
  async function sendBroadcast(data: {
    body: string
    attachmentFileIds: string[]
  }): Promise<number> {
    const resp = await api<{ recipient_count: number }>('/admin/broadcast', {
      method: 'POST',
      body: { body: data.body, attachment_file_ids: data.attachmentFileIds },
    })
    return resp.recipient_count
  }

  return {
    checkUsernameAvailable,
    createAccount,
    listAccounts,
    deleteAccount,
    blockAccount,
    unblockAccount,
    resetAccountPassword,
    getBroadcastChat,
    sendBroadcast,
  }
}
