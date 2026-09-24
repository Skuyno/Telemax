import type { TokenResponse } from '~/types/auth'

// Module-level, not per-call: several requests can 401 around the same
// time (e.g. right after a reload, before the access token's been
// refreshed), and they must all wait on the same in-flight refresh instead
// of each firing their own POST /auth/refresh.
let refreshPromise: Promise<string | null> | null = null

async function performRefresh(): Promise<string | null> {
  const auth = useAuthStore()
  const config = useRuntimeConfig()
  if (!auth.refreshToken) return null

  try {
    const tokens = await $fetch<TokenResponse>('/auth/refresh', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { refresh_token: auth.refreshToken },
    })
    auth.setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token })
    return tokens.access_token
  } catch {
    // The refresh token itself is invalid/expired (or the account's
    // token_version moved on, e.g. a password change elsewhere) — nothing
    // left to try, the session is really over.
    auth.logout()
    return null
  }
}

/** Refreshes the access token, de-duplicating concurrent callers. */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export function useApi() {
  const config = useRuntimeConfig()
  const auth = useAuthStore()

  const api = $fetch.create({
    baseURL: config.public.apiBase,
    // Retried request re-runs onRequest too, so it picks up whatever
    // access token refreshAccessToken() just stored — no need to patch
    // this attempt's headers by hand.
    retry: 1,
    retryStatusCodes: [401],
    onRequest({ options }) {
      if (auth.accessToken) {
        options.headers.set('Authorization', `Bearer ${auth.accessToken}`)
      }
    },
    async onResponseError({ response }) {
      if (response.status !== 401) return

      // A failed refresh call reaching here would otherwise recurse into
      // refreshing forever; there's nothing to refresh from at that point.
      if (response.url.includes('/auth/refresh')) {
        auth.logout()
        await navigateTo('/login')
        return
      }

      const newToken = await refreshAccessToken()
      if (!newToken) {
        await navigateTo('/login')
      }
    },
  })

  return api
}
