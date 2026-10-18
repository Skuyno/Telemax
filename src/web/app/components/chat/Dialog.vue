<script setup lang="ts">
import type { Chat, Message } from '~/types/chat'
import { dayKey, formatDateSeparator } from '~/utils/chatTime'

const props = defineProps<{
  chat: Chat
  messages: Message[]
  meId: string
  send: (text: string, attachmentIds: string[]) => Promise<void>
  loadError?: string
}>()

const emit = defineEmits<{ back: []; loadOlder: []; typing: [] }>()

const auth = useAuthStore()
const chatStore = useChatStore()
const { editMessage, deleteMessage, loadUntil } = useChats()

const composer = ref<{ reset: () => void; focus: () => void } | null>(null)
const editing = ref<Message | null>(null)
const pendingRemoval = ref<Message | null>(null)
const isRemoving = ref(false)
const isSending = ref(false)
const sendError = ref('')
const feed = ref<HTMLElement | null>(null)

const searchOpen = ref(false)
const highlightedId = ref<string | null>(null)
let highlightTimer: ReturnType<typeof setTimeout> | undefined

const online = computed(() => props.chat.type === 'direct' && chatStore.isPeerOnline(props.chat))
const typing = computed(() => chatStore.isPeerTyping(props.chat.id))

const memberCountLabel = computed(() => {
  const count = props.chat.memberCount ?? 0
  const tail = count % 10
  const teens = count % 100
  if (tail === 1 && teens !== 11) return `${count} участник`
  if (tail >= 2 && tail <= 4 && (teens < 12 || teens > 14)) return `${count} участника`
  return `${count} участников`
})

const myInitials = computed(() => {
  const name = auth.user?.displayName ?? auth.user?.username ?? ''
  return name ? toInitials(name) : ''
})

/** Лента, разбитая на группы по дням — под разделители дат. */
const groups = computed(() => {
  const result: { key: string; date: string; items: Message[] }[] = []

  for (const message of props.messages) {
    if (message.isDeleted) continue
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

async function onSubmit(text: string, attachmentIds: string[]) {
  if (isSending.value) return

  if (editing.value) {
    if (!text) return
    isSending.value = true
    sendError.value = ''
    try {
      if (text !== editing.value.body) await editMessage(props.chat.id, editing.value.id, text)
      cancelEdit()
    } catch (e) {
      sendError.value = extractApiErrorMessage(e, 'Не удалось изменить сообщение')
    } finally {
      isSending.value = false
    }
    return
  }

  isSending.value = true
  sendError.value = ''
  try {
    await props.send(text, attachmentIds)
    composer.value?.reset()
  } catch (e) {
    // Черновик не очищаем — чтобы можно было отправить ещё раз.
    sendError.value = extractApiErrorMessage(e, 'Не удалось отправить сообщение')
  } finally {
    isSending.value = false
  }
}

function startEdit(message: Message) {
  editing.value = message
  sendError.value = ''
}

function cancelEdit() {
  editing.value = null
  composer.value?.reset()
}

function onRemove(message: Message) {
  pendingRemoval.value = message
}

async function confirmRemove() {
  const message = pendingRemoval.value
  if (!message || isRemoving.value) return

  isRemoving.value = true
  sendError.value = ''
  try {
    await deleteMessage(props.chat.id, message.id)
    if (editing.value?.id === message.id) cancelEdit()
  } catch (e) {
    sendError.value = extractApiErrorMessage(e, 'Не удалось удалить сообщение')
  } finally {
    pendingRemoval.value = null
    isRemoving.value = false
  }
}

async function jumpTo(message: Message) {
  const found = await loadUntil(props.chat.id, message.id)
  if (!found) return

  await nextTick()
  const target = feed.value?.querySelector(`[data-message-id="${message.id}"]`)
  target?.scrollIntoView({ block: 'center', behavior: 'smooth' })

  highlightedId.value = message.id
  clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => (highlightedId.value = null), 2000)
}

function onScroll() {
  if (feed.value && feed.value.scrollTop < 40) emit('loadOlder')
}

onBeforeUnmount(() => clearTimeout(highlightTimer))

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
    sendError.value = ''
    editing.value = null
    searchOpen.value = false
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

      <span class="dialog__avatar">
        <ChatSavedIcon v-if="chat.isSaved" />
        <ChatGroupIcon v-else-if="chat.type === 'group'" />
        <UserAvatar v-else :url="chat.avatarUrl" :initials="chat.initials" />
        <span v-if="online" class="dialog__online" />
      </span>
      <span class="dialog__ident">
        <span class="dialog__title">{{ chat.title }}</span>
        <span v-if="chat.isSaved" class="dialog__status">заметки для себя</span>
        <span v-else-if="chat.type === 'group'" class="dialog__status">
          {{ memberCountLabel }}
        </span>
        <span v-if="typing" class="dialog__status is-active">печатает…</span>
        <span v-else-if="online" class="dialog__status is-active">в сети</span>
      </span>

      <button
        type="button"
        class="dialog__tool"
        :class="{ 'is-active': searchOpen }"
        aria-label="Поиск по сообщениям"
        @click="searchOpen = !searchOpen"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
      </button>
    </header>

    <ChatMessageSearch v-if="searchOpen" :chat-id="chat.id" @jump="jumpTo" />

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
          :avatar-url="message.senderId === meId ? auth.user?.avatarUrl : chat.avatarUrl"
          :read="chatStore.isMessageRead(message)"
          :hide-status="chat.isSaved"
          :highlighted="highlightedId === message.id"
          @edit="startEdit(message)"
          @remove="onRemove(message)"
        />
      </div>

      <p v-if="loadError" class="dialog__no-messages is-error">{{ loadError }}</p>
      <p v-else-if="!messages.length && chat.isSaved" class="dialog__no-messages">
        Сохраняйте сюда заметки, ссылки и файлы — их видите только вы.
      </p>
      <p v-else-if="!messages.length" class="dialog__no-messages">
        Сообщений пока нет — напишите первым.
      </p>
    </div>

    <p v-if="typing" class="dialog__typing">
      печатает
      <span class="dialog__dots" aria-hidden="true"><i /><i /><i /></span>
    </p>

    <p v-if="sendError" class="dialog__error">{{ sendError }}</p>

    <ChatComposer
      ref="composer"
      :chat-id="chat.id"
      :editing="editing"
      :busy="isSending"
      @submit="onSubmit"
      @cancel-edit="cancelEdit"
      @typing="emit('typing')"
    />

    <ChatDeleteConfirm
      :open="!!pendingRemoval"
      :busy="isRemoving"
      @confirm="confirmRemove"
      @cancel="pendingRemoval = null"
    />
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
  position: relative;
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

.dialog__online {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 12px;
  height: 12px;
  background: var(--color-focus);
  border: 2px solid var(--color-lift);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--color-focus);
}

.dialog__ident {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.dialog__status {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.dialog__status.is-active {
  color: var(--color-focus);
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

.dialog__tool {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex: none;
  padding: 0;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--chat-radius);
  color: var(--color-text-muted);
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}

.dialog__tool:hover:not(:disabled),
.dialog__tool.is-active {
  color: var(--color-accent);
  border-color: var(--chat-accent-soft);
}

.dialog__tool svg {
  width: 20px;
  height: 20px;
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

.dialog__no-messages.is-error {
  color: var(--color-error);
}

.dialog__typing {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  margin: 0;
  padding: 0 20px 8px 62px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-focus);
}

.dialog__dots {
  display: inline-flex;
  gap: 4px;
}

.dialog__dots i {
  width: 5px;
  height: 5px;
  background: var(--color-focus);
  border-radius: 50%;
  animation: dialog-dot 1.2s infinite ease-in-out;
}

.dialog__dots i:nth-child(2) {
  animation-delay: 0.15s;
}

.dialog__dots i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes dialog-dot {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }

  40% {
    opacity: 1;
  }
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

  .dialog__feed {
    padding-inline: 14px;
  }
}
</style>
