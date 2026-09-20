<script setup lang="ts">
import type { Chat, Message } from '~/types/chat'
import { dayKey, formatDateSeparator } from '~/utils/chatTime'

const props = defineProps<{
  chat: Chat
  messages: Message[]
  meId: string
  send: (text: string) => Promise<void>
  loadError?: string
}>()

const emit = defineEmits<{ back: []; loadOlder: [] }>()

const auth = useAuthStore()

const myInitials = computed(() => {
  const name = auth.user?.displayName ?? auth.user?.username ?? ''
  return name ? toInitials(name) : ''
})

const draft = ref('')
const isSending = ref(false)
const sendError = ref('')
const feed = ref<HTMLElement | null>(null)

/** Лента, разбитая на группы по дням — под разделители дат. */
const groups = computed(() => {
  const result: { key: string; date: string; items: Message[] }[] = []

  for (const message of props.messages) {
    const key = dayKey(message.createdAt)
    const last = result.at(-1)
    if (last?.key === key) last.items.push(message)
    else result.push({ key, date: formatDateSeparator(message.createdAt), items: [message] })
  }

  return result
})

async function scrollToBottom() {
  await nextTick()
  if (feed.value) feed.value.scrollTop = feed.value.scrollHeight
}

async function onSend() {
  const text = draft.value.trim()
  if (!text || isSending.value) return

  isSending.value = true
  sendError.value = ''
  try {
    await props.send(text)
    draft.value = ''
  } catch (e) {
    // Черновик не очищаем — чтобы можно было отправить ещё раз.
    sendError.value = extractApiErrorMessage(e, 'Не удалось отправить сообщение')
  } finally {
    isSending.value = false
  }
}

function onScroll() {
  if (feed.value && feed.value.scrollTop < 40) emit('loadOlder')
}

/** Новое сообщение внизу — прокручиваем к нему; старые подгрузились сверху — держим позицию. */
watch(
  () => ({
    chatId: props.chat.id,
    count: props.messages.length,
    firstId: props.messages[0]?.id,
  }),
  async (next, prev) => {
    const el = feed.value
    const prependedOlder =
      next.chatId === prev?.chatId &&
      prev.count > 0 &&
      next.count > prev.count &&
      next.firstId !== prev.firstId
    if (!el || !prependedOlder) return scrollToBottom()

    const fromBottom = el.scrollHeight - el.scrollTop
    await nextTick()
    el.scrollTop = el.scrollHeight - fromBottom
  },
)

watch(
  () => props.chat.id,
  () => {
    draft.value = ''
    sendError.value = ''
    scrollToBottom()
  },
  { immediate: true },
)
</script>

<template>
  <section class="dialog">
    <header class="dialog__head">
      <button type="button" class="dialog__back" aria-label="К списку чатов" @click="emit('back')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 5l-7 7 7 7" />
        </svg>
      </button>

      <span class="dialog__avatar">{{ chat.initials }}</span>
      <span class="dialog__title">{{ chat.title }}</span>
    </header>

    <div ref="feed" class="dialog__feed" @scroll="onScroll">
      <div v-for="group in groups" :key="group.key" class="dialog__group">
        <div class="dialog__date">
          <span class="dialog__date-label">{{ group.date }}</span>
        </div>

        <ChatMessage
          v-for="message in group.items"
          :key="message.id"
          :message="message"
          :own="message.senderId === meId"
          :initials="message.senderId === meId ? myInitials : chat.initials"
        />
      </div>

      <p v-if="loadError" class="dialog__no-messages is-error">{{ loadError }}</p>
      <p v-else-if="!messages.length" class="dialog__no-messages">
        Сообщений пока нет — напишите первым.
      </p>
    </div>

    <p v-if="sendError" class="dialog__error">{{ sendError }}</p>

    <footer class="dialog__composer">
      <input
        v-model="draft"
        class="dialog__input"
        type="text"
        placeholder="Сообщение"
        aria-label="Сообщение"
        @keydown.enter="onSend"
      />

      <button
        type="button"
        class="dialog__send"
        aria-label="Отправить"
        :disabled="isSending"
        @click="onSend"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M3 20.5 21.5 12 3 3.5l3.4 7.2 8.6 1.3-8.6 1.3z" />
        </svg>
      </button>
    </footer>
  </section>
</template>

<style scoped>
.dialog {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: var(--color-ground);
}

.dialog__head {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 72px;
  flex: none;
  padding: 0 20px;
  background: var(--color-lift);
  border-bottom: 1px solid var(--chat-line);
}

.dialog__back {
  display: none;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
}

.dialog__back svg {
  width: 18px;
  height: 18px;
}

.dialog__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-accent-soft);
  border-radius: var(--chat-radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-accent);
}

.dialog__title {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 17px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog__feed {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-image: var(--chat-grid);
  background-size: 48px 48px;
}

.dialog__group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog__date {
  display: flex;
  justify-content: center;
  margin: 10px 0 4px;
}

.dialog__date-label {
  padding: 5px 14px;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-muted);
}

.dialog__no-messages {
  margin: 24px 0;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.dialog__composer {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
  padding: 16px 20px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.dialog__input {
  height: 48px;
  flex: 1;
  min-width: 0;
  padding: 0 18px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
  outline: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.dialog__input::placeholder {
  color: var(--color-text-dim);
}

.dialog__input:focus {
  border-color: var(--color-focus);
}

.dialog__send {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex: none;
  padding: 0;
  background: var(--color-accent);
  border: none;
  border-radius: var(--chat-radius-lg);
  color: var(--color-ink);
  cursor: pointer;
}

.dialog__send svg {
  width: 20px;
  height: 20px;
}

.dialog__send:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.dialog__send:active:not(:disabled) {
  background: var(--color-accent-pressed);
}

.dialog__send:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dialog__no-messages.is-error {
  color: var(--color-error);
}

.dialog__error {
  margin: 0;
  flex: none;
  padding: 6px 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-error);
}

@media (max-width: 900px) {
  .dialog__back {
    display: flex;
  }

  .dialog__feed,
  .dialog__composer {
    padding-inline: 14px;
  }
}
</style>
