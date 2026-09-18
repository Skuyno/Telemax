export interface User {
  id: string
  username: string
  displayName: string | null
  email: string | null
  createdAt: string
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

/** Raw response shape from GET /me */
export interface UserResponse {
  id: string
  username: string
  email: string | null
  display_name: string | null
  created_at: string
}
