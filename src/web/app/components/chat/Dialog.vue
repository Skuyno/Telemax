<script setup lang="ts">
import type { Chat, Message } from '~/types/chat'
import { dayKey, formatDateSeparator } from '~/utils/chatTime'

const props = defineProps<{ chat: Chat; messages: Message[]; meId: string }>()

const emit = defineEmits<{ send: [string]; back: [] }>()

const draft = ref('')
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

function onSend() {
  const text = draft.value.trim()
  if (!text) return
  emit('send', text)
  draft.value = ''
  scrollToBottom()
}

watch(() => props.chat.id, scrollToBottom, { immediate: true })
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

    <div ref="feed" class="dialog__feed">
      <div v-for="group in groups" :key="group.key" class="dialog__group">
        <div class="dialog__date">
          <span class="dialog__date-line" />
          <span class="dialog__date-label">{{ group.date }}</span>
          <span class="dialog__date-line" />
        </div>

        <ChatMessage
          v-for="message in group.items"
          :key="message.id"
          :message="message"
          :own="message.senderId === meId"
        />
      </div>

      <p v-if="!messages.length" class="dialog__no-messages">
        Сообщений пока нет — напишите первым.
      </p>
    </div>

    <footer class="dialog__composer">
      <input
        v-model="draft"
        class="dialog__input"
        type="text"
        placeholder="Сообщение"
        aria-label="Сообщение"
        @keydown.enter="onSend"
      />

      <button type="button" class="dialog__send" @click="onSend">
        <span aria-hidden="true">▶</span>
        Отправить
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
  gap: 10px;
  height: 60px;
  flex: none;
  padding: 0 14px;
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
  width: 36px;
  height: 36px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-accent-soft);
  border-radius: var(--radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-text);
}

.dialog__title {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 15px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog__feed {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.dialog__group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dialog__date {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 6px 0 2px;
}

.dialog__date-line {
  flex: 1;
  height: 1px;
  background: var(--chat-line-soft);
}

.dialog__date-label {
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
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
  gap: 8px;
  height: 60px;
  flex: none;
  padding: 0 14px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.dialog__input {
  height: 40px;
  flex: 1;
  min-width: 0;
  padding: 0 12px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--radius);
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
  gap: 8px;
  height: 40px;
  flex: none;
  padding: 0 16px;
  background: var(--color-accent);
  border: none;
  border-radius: var(--radius);
  box-shadow: 3px 3px 0 var(--color-ink);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-ink);
  cursor: pointer;
}

.dialog__send:hover {
  background: var(--color-accent-hover);
}

.dialog__send:active {
  background: var(--color-accent-pressed);
}

@media (max-width: 900px) {
  .dialog__back {
    display: flex;
  }

  .dialog__send span {
    display: none;
  }

  .dialog__send {
    padding: 0 12px;
  }
}
</style>
