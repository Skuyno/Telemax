interface FastApiErrorBody {
  detail?: string | { msg?: string }[]
}

/** Extracts a human-readable message from a FastAPI-style error response (ofetch FetchError). */
export function extractApiErrorMessage(error: unknown, fallback: string): string {
  const data = (error as { data?: FastApiErrorBody } | undefined)?.data

  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (Array.isArray(data?.detail)) {
    const messages = data.detail.map((item) => item.msg).filter(Boolean)
    if (messages.length) return messages.join('; ')
  }

  return fallback
}
