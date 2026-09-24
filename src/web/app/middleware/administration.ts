/**
 * Guards /administration/* pages: only admin/superuser get in.
 *
 * Client-only: `apiBase` is a relative path ("/api", resolved by the
 * browser against the current origin) — Node's fetch on the server has
 * no origin to resolve it against, so a server-side fetchMe() call here
 * wouldn't fail loudly, it'd just quietly hit the wrong thing (same
 * reason app/plugins/auth.client.ts is client-only). The real access
 * boundary is the backend's own role check on every request anyway;
 * this only avoids showing the page shell to someone who can't use it.
 *
 * Doesn't just read `auth.user` off the bat — on a hard reload the
 * profile hasn't necessarily been re-fetched yet (tokens survive via
 * cookie, but the user object itself doesn't), so this fetches it first
 * when missing, then decides. Avoids bouncing a legitimate admin off a
 * false negative during that race.
 */
export default defineNuxtRouteMiddleware(async () => {
  if (import.meta.server) return

  const auth = useAuthStore()

  if (!auth.user) {
    const { fetchMe } = useAuth()
    try {
      await fetchMe()
    } catch {
      return navigateTo('/login')
    }
  }

  if (auth.user?.role !== 'admin' && auth.user?.role !== 'superuser') {
    return navigateTo('/')
  }
})
