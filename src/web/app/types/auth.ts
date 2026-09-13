export interface User {
  id: string
  username: string
  displayName: string
  avatarUrl?: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
}
