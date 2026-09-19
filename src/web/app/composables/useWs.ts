/** Resolves a relative "/ws" base (behind nginx) against the current page's origin. */
function resolveWsBase(base: string): string {
  if (!base.startsWith('/')) return base
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}${base}`
}

export function useWs() {
  const config = useRuntimeConfig()
  const auth = useAuthStore()
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)

  function connect() {
    if (socket.value || !auth.accessToken) return

    const url = `${resolveWsBase(config.public.wsBase)}?token=${auth.accessToken}`
    const ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
    }
    ws.onclose = () => {
      isConnected.value = false
      socket.value = null
    }

    socket.value = ws
  }

  function disconnect() {
    socket.value?.close()
    socket.value = null
  }

  function send(payload: unknown) {
    socket.value?.send(JSON.stringify(payload))
  }

  return { socket, isConnected, connect, disconnect, send }
}
