/** Resolves a relative "/ws" base (behind nginx) against the current page's origin. */
function resolveWsBase(base: string): string {
  if (!base.startsWith('/')) return base
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}${base}`
}

/** Паузы между попытками переподключения: 1с, 2с, 4с… но не дольше 15с. */
const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 15000

interface UseWsOptions {
  /** Каждое входящее событие, уже разобранное из JSON. */
  onMessage?: (event: unknown) => void
  /** Соединение восстановилось после обрыва — пока его не было, события могли потеряться. */
  onReconnect?: () => void
}

export function useWs(options: UseWsOptions = {}) {
  const config = useRuntimeConfig()
  const auth = useAuthStore()
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)

  let closedManually = false
  let attempt = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined

  function scheduleReconnect() {
    const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS)
    attempt++
    reconnectTimer = setTimeout(connect, delay)
  }

  function connect() {
    if (socket.value || !auth.accessToken) return
    closedManually = false

    const url = `${resolveWsBase(config.public.wsBase)}?token=${auth.accessToken}`
    const ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
      const wasReconnect = attempt > 0
      attempt = 0
      if (wasReconnect) options.onReconnect?.()
    }
    ws.onmessage = (event) => {
      try {
        options.onMessage?.(JSON.parse(event.data))
      } catch {
        // Не JSON — от ws-gateway такого не приходит, просто пропускаем.
      }
    }
    ws.onclose = () => {
      isConnected.value = false
      socket.value = null
      if (!closedManually) scheduleReconnect()
    }

    socket.value = ws
  }

  function disconnect() {
    closedManually = true
    clearTimeout(reconnectTimer)
    attempt = 0
    socket.value?.close()
    socket.value = null
  }

  function send(payload: unknown) {
    if (socket.value?.readyState !== WebSocket.OPEN) return
    socket.value.send(JSON.stringify(payload))
  }

  return { socket, isConnected, connect, disconnect, send }
}
