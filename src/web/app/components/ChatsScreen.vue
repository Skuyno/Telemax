<script setup lang="ts">
const chatStore = useChatStore()
const {
  loadChats,
  loadMessages,
  loadOlderMessages,
  sendMessage,
  handleRealtimeEvent,
  resync,
} = useChats()
const ws = useWs({ onMessage: handleRealtimeEvent, onReconnect: resync })

const isNarrow = ref(false)
const showDialogOnNarrow = ref(false)
const messagesError = ref('')

function onSelect() {
  showDialogOnNarrow.value = true
}

async function send(text: string) {
  if (chatStore.activeChatId) await sendMessage(chatStore.activeChatId, text)
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
    } catch (e) {
      messagesError.value = extractApiErrorMessage(e, 'Не удалось загрузить сообщения')
    }
  },
)

onMounted(() => {
  // Экран монтируется заново при каждом входе — данные прошлого пользователя не должны остаться.
  chatStore.reset()
  loadChats()
  // Новые сообщения приходят сразу, без F5.
  ws.connect()

  const media = window.matchMedia('(max-width: 900px)')
  isNarrow.value = media.matches
  media.addEventListener('change', (event) => {
    isNarrow.value = event.matches
  })
})

// Экран размонтируется при выходе из аккаунта — сокет старого пользователя закрываем.
onBeforeUnmount(() => ws.disconnect())

const showSidebar = computed(() => !isNarrow.value || !showDialogOnNarrow.value)
const showDialog = computed(() => !isNarrow.value || showDialogOnNarrow.value)
</script>

<template>
  <div class="chats">
    <ChatSidebar v-if="showSidebar" @select="onSelect" />

    <template v-if="showDialog">
      <ChatDialog
        v-if="chatStore.activeChat && chatStore.meId"
        :chat="chatStore.activeChat"
        :messages="chatStore.activeMessages"
        :me-id="chatStore.meId"
        :send="send"
        :load-error="messagesError"
        @load-older="onLoadOlder"
        @back="showDialogOnNarrow = false"
      />
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
}
</style>
