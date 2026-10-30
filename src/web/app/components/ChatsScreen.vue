<script setup lang="ts">
const chatStore = useChatStore()
const {
  loadChats,
  loadMessages,
  loadOlderMessages,
  sendMessage,
  handleRealtimeEvent,
  resync,
  markRead,
  sendTyping,
} = useChats()
const ws = useWs({ onMessage: handleRealtimeEvent, onReconnect: resync })

const isNarrow = ref(false)
const showDialogOnNarrow = ref(false)
const messagesError = ref('')
const isRestoring = computed(() => chatStore.isLoadingChats)
let clock: ReturnType<typeof setInterval> | undefined

function onTyping() {
  if (chatStore.activeChatId) sendTyping(chatStore.activeChatId)
}

function onPageReturn() {
  if (document.visibilityState !== 'visible' || !document.hasFocus()) return
  if (chatStore.activeChatId) markRead(chatStore.activeChatId)
}

function onSelect() {
  showDialogOnNarrow.value = true
}

const SIDEBAR_WIDTH_KEY = 'telemax.sidebarWidth'
const SIDEBAR_DEFAULT = 300
const SIDEBAR_MIN = 240
const SIDEBAR_MAX = 640
const SIDEBAR_COMPACT = 84
const SIDEBAR_COMPACT_SNAP = 170
const DIALOG_MIN = 420

const sidebarWidth = ref(SIDEBAR_DEFAULT)
const isResizing = ref(false)
const isCompact = computed(() => !isNarrow.value && sidebarWidth.value === SIDEBAR_COMPACT)

function clampSidebar(width: number): number {
  if (width < SIDEBAR_COMPACT_SNAP) return SIDEBAR_COMPACT
  const max = Math.min(SIDEBAR_MAX, window.innerWidth - DIALOG_MIN)
  return Math.round(Math.min(Math.max(width, SIDEBAR_MIN), Math.max(max, SIDEBAR_MIN)))
}

function setSidebarWidth(width: number) {
  sidebarWidth.value = clampSidebar(width)
  try {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
  } catch {}
}

function onResizeStart(event: PointerEvent) {
  if (event.button !== 0) return
  event.preventDefault()
  const handle = event.currentTarget as HTMLElement
  handle.setPointerCapture(event.pointerId)
  isResizing.value = true
  const startX = event.clientX
  const startWidth = sidebarWidth.value

  function onMove(moveEvent: PointerEvent) {
    sidebarWidth.value = clampSidebar(startWidth + moveEvent.clientX - startX)
  }

  function onUp() {
    isResizing.value = false
    handle.removeEventListener('pointermove', onMove)
    handle.removeEventListener('pointerup', onUp)
    handle.removeEventListener('pointercancel', onUp)
    setSidebarWidth(sidebarWidth.value)
  }

  handle.addEventListener('pointermove', onMove)
  handle.addEventListener('pointerup', onUp)
  handle.addEventListener('pointercancel', onUp)
}

function onResizeKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft') {
    setSidebarWidth(sidebarWidth.value <= SIDEBAR_MIN ? SIDEBAR_COMPACT : sidebarWidth.value - 20)
  } else if (event.key === 'ArrowRight') {
    setSidebarWidth(isCompact.value ? SIDEBAR_MIN : sidebarWidth.value + 20)
  } else if (event.key === 'Home') setSidebarWidth(SIDEBAR_COMPACT)
  else if (event.key === 'End') setSidebarWidth(SIDEBAR_MAX)
  else return
  event.preventDefault()
}

function onWindowResize() {
  sidebarWidth.value = clampSidebar(sidebarWidth.value)
}

function onBack() {
  showDialogOnNarrow.value = false
  chatStore.setActiveChat(null)
}

async function send(text: string, attachmentIds: string[]) {
  if (chatStore.activeChatId) await sendMessage(chatStore.activeChatId, text, attachmentIds)
}

function onLoadOlder() {
  if (chatStore.activeChatId) loadOlderMessages(chatStore.activeChatId).catch(() => {})
}

watch(
  () => chatStore.activeChatId,
  async (chatId) => {
    messagesError.value = ''
    if (!chatId) return
    try {
      await loadMessages(chatId)
      markRead(chatId)
    } catch (e) {
      messagesError.value = extractApiErrorMessage(e, 'Не удалось загрузить сообщения')
    }
  },
)

watch(
  () => chatStore.chats.map((chat) => chat.peerId).join(),
  (next, prev) => {
    if (prev !== undefined && next !== prev) ws.send({ type: 'presence.sync' })
  },
)

onMounted(() => {
  // Экран монтируется заново при каждом входе — данные прошлого пользователя не должны остаться.
  chatStore.reset()
  loadChats().then(() => {
    chatStore.restoreActiveChat()
    if (chatStore.activeChatId) showDialogOnNarrow.value = true
  })
  // Новые сообщения приходят сразу, без F5.
  ws.connect()
  clock = setInterval(() => chatStore.tick(), 1000)
  window.addEventListener('focus', onPageReturn)
  document.addEventListener('visibilitychange', onPageReturn)
  window.addEventListener('resize', onWindowResize)

  try {
    const saved = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY))
    if (saved) sidebarWidth.value = clampSidebar(saved)
  } catch {}

  const media = window.matchMedia('(max-width: 900px)')
  isNarrow.value = media.matches
  media.addEventListener('change', (event) => {
    isNarrow.value = event.matches
  })
})

// Экран размонтируется при выходе из аккаунта — сокет старого пользователя закрываем.
onBeforeUnmount(() => {
  ws.disconnect()
  clearInterval(clock)
  window.removeEventListener('focus', onPageReturn)
  document.removeEventListener('visibilitychange', onPageReturn)
  window.removeEventListener('resize', onWindowResize)
})

const showSidebar = computed(() => !isNarrow.value || !showDialogOnNarrow.value)
const showDialog = computed(() => !isNarrow.value || showDialogOnNarrow.value)
</script>

<template>
  <div
    class="chats"
    :class="{ 'is-resizing': isResizing }"
    :style="isNarrow ? undefined : { '--sidebar-width': `${sidebarWidth}px` }"
  >
    <ChatSidebar
      v-if="showSidebar"
      :compact="isCompact"
      @select="onSelect"
      @expand="setSidebarWidth(SIDEBAR_DEFAULT)"
    />

    <div
      v-if="!isNarrow"
      class="chats__resizer"
      role="separator"
      aria-orientation="vertical"
      aria-label="Ширина списка чатов"
      :aria-valuemin="SIDEBAR_COMPACT"
      :aria-valuemax="SIDEBAR_MAX"
      :aria-valuenow="sidebarWidth"
      tabindex="0"
      title="Потяните, чтобы изменить ширину"
      @pointerdown="onResizeStart"
      @keydown="onResizeKeydown"
      @dblclick="setSidebarWidth(SIDEBAR_DEFAULT)"
    />

    <template v-if="showDialog">
      <ChatDialog
        v-if="chatStore.activeChat && chatStore.meId"
        :chat="chatStore.activeChat"
        :messages="chatStore.activeMessages"
        :me-id="chatStore.meId"
        :send="send"
        :load-error="messagesError"
        @load-older="onLoadOlder"
        @typing="onTyping"
        @back="onBack"
      />
      <ChatSkeletonDialog v-else-if="isRestoring" />
      <ChatEmpty v-else :has-chats="chatStore.chats.length > 0 || chatStore.isLoadingChats" />
    </template>
  </div>
</template>

<style scoped>
.chats {
  display: flex;
  height: 100%;
  --chat-line: rgba(61, 79, 156, 0.6);
  --chat-line-soft: rgba(61, 79, 156, 0.5);
  --chat-accent-soft: rgba(255, 204, 46, 0.45);
  /* Скругления только внутри экрана чатов — глобальный --radius остаётся нулевым. */
  --chat-radius: 10px;
  --chat-radius-lg: 14px;
  /* Та же сетка, что на странице входа. */
  --chat-grid:
    linear-gradient(to right, rgba(120, 150, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(120, 150, 255, 0.06) 1px, transparent 1px);
}

.chats.is-resizing {
  cursor: col-resize;
  user-select: none;
}

.chats__resizer {
  position: relative;
  z-index: 5;
  width: 8px;
  flex: none;
  margin: 0 -4px;
  cursor: col-resize;
  touch-action: none;
}

.chats__resizer::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 3px;
  width: 2px;
  background: transparent;
  transition: background 0.15s ease;
}

.chats__resizer:hover::after,
.chats__resizer:focus-visible::after,
.chats.is-resizing .chats__resizer::after {
  background: var(--color-accent);
}

.chats__resizer:focus-visible {
  outline: none;
}

@media (prefers-reduced-motion: reduce) {
  .chats__resizer::after {
    transition: none;
  }
}
</style>
