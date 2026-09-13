export function useApi() {
  const config = useRuntimeConfig()
  const auth = useAuthStore()

  const api = $fetch.create({
    baseURL: config.public.apiBase,
    onRequest({ options }) {
      if (auth.accessToken) {
        options.headers.set('Authorization', `Bearer ${auth.accessToken}`)
      }
    },
    onResponseError({ response }) {
      if (response.status === 401) {
        auth.logout()
        navigateTo('/login')
      }
    },
  })

  return api
}
