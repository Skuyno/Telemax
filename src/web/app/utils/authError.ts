/**
 * Backend detail strings for /auth/* that have a specific Russian message.
 * Login intentionally returns the same "Invalid credentials" for both a
 * wrong password and an unknown username (anti-enumeration) — both map to
 * one generic message here for the same reason, not shown separately.
 */
const AUTH_ERROR_MESSAGES: Record<string, string> = {
  'Invalid credentials': 'Неверный логин или пароль',
  'Username already taken': 'Данный логин уже используется в системе',
}

/** Like extractApiErrorMessage, but translates known /auth/* detail strings to Russian. */
export function mapAuthErrorMessage(error: unknown, fallback: string): string {
  const raw = extractApiErrorMessage(error, fallback)
  return AUTH_ERROR_MESSAGES[raw] ?? raw
}
