export type Role = 'superuser' | 'admin' | 'user'

export interface User {
  id: string
  username: string
  displayName: string | null
  email: string | null
  avatarUrl: string | null
  createdAt: string
  role: Role
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
}

/** Raw response shape from POST /auth/login and /auth/refresh */
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

/** Raw response shape from GET /me and the /admin/accounts endpoints */
export interface UserResponse {
  id: string
  username: string
  email: string | null
  display_name: string | null
  avatar_url: string | null
  created_at: string
  role: Role
}
