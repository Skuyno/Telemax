/**
 * Repopulates `auth.user` after a page reload.
 *
 * Tokens survive a reload on their own (persisted in cookies by the auth
 * store), but the user profile itself doesn't — it's only ever fetched
 * right after a fresh login. Without this, a returning session would
 * count as authenticated (middleware lets it through) but show no
 * username/avatar until something else happened to call fetchMe().
 *
 * Client-only: no need to duplicate this fetch on the server render too,
 * and GET /me needs a real network round trip we'd rather not block SSR on.
 */
export default defineNuxtPlugin(async () => {
  const auth = useAuthStore()
  if (!auth.isAuthenticated) return

  const { fetchMe } = useAuth()
  try {
    await fetchMe()
  } catch {
    // A 401 here already triggers useApi's own refresh-or-logout flow.
  }
})
