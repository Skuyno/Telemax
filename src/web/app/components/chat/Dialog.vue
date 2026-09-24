<script setup lang="ts">
import type { Chat, Message, PendingUpload } from '~/types/chat'
import { dayKey, formatDateSeparator, formatMessageTime } from '~/utils/chatTime'

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
const { editMessage, deleteMessage, searchMessages, loadUntil } = useChats()
const { uploadFile } = useFiles()

const editing = ref<Message | null>(null)
const pendingRemoval = ref<Message | null>(null)
const isRemoving = ref(false)
const uploads = ref<PendingUpload[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const messageInput = ref<HTMLTextAreaElement | null>(null)

const searchOpen = ref(false)
const searchQuery = ref('')
const searchResults = ref<Message[]>([])
const isSearchingMessages = ref(false)
const searchDone = ref(false)
const highlightedId = ref<string | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | undefined
let highlightTimer: ReturnType<typeof setTimeout> | undefined

const isUploading = computed(() => uploads.value.some((item) => !item.fileId && !item.error))
const readyAttachmentIds = computed(() =>
  uploads.value.flatMap((item) => (item.fileId ? [item.fileId] : [])),
)

const online = computed(() => chatStore.isPeerOnline(props.chat))
const typing = computed(() => chatStore.isPeerTyping(props.chat.id))

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
  if (isSending.value || isUploading.value) return

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

  if (!text && !readyAttachmentIds.value.length) return

  isSending.value = true
  sendError.value = ''
  try {
    await props.send(text, readyAttachmentIds.value)
    draft.value = ''
    uploads.value = []
  } catch (e) {
    // Черновик не очищаем — чтобы можно было отправить ещё раз.
    sendError.value = extractApiErrorMessage(e, 'Не удалось отправить сообщение')
  } finally {
    isSending.value = false
  }
}

function onEnter(event: KeyboardEvent) {
  if (event.ctrlKey || event.metaKey || event.shiftKey) {
    event.preventDefault()
    insertNewline()
    return
  }
  event.preventDefault()
  onSend()
}

function insertNewline() {
  const field = messageInput.value
  if (!field) {
    draft.value += '\n'
    return
  }

  const start = field.selectionStart ?? draft.value.length
  const end = field.selectionEnd ?? start
  draft.value = `${draft.value.slice(0, start)}\n${draft.value.slice(end)}`

  nextTick(() => {
    field.selectionStart = start + 1
    field.selectionEnd = start + 1
    resizeInput()
  })
}

function resizeInput() {
  const field = messageInput.value
  if (!field) return
  field.style.height = 'auto'
  field.style.height = `${Math.min(field.scrollHeight, 160)}px`
}

watch(draft, () => nextTick(resizeInput))

onMounted(() => resizeInput())

function startEdit(message: Message) {
  uploads.value = []
  editing.value = message
  draft.value = message.body
  sendError.value = ''
  nextTick(() => messageInput.value?.focus())
}

function cancelEdit() {
  editing.value = null
  draft.value = ''
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
    pendingRemoval.value = null
  } catch (e) {
    sendError.value = extractApiErrorMessage(e, 'Не удалось удалить сообщение')
    pendingRemoval.value = null
  } finally {
    isRemoving.value = false
  }
}

function onRemovalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') pendingRemoval.value = null
}

watch(pendingRemoval, (message) => {
  if (message) window.addEventListener('keydown', onRemovalKeydown)
  else window.removeEventListener('keydown', onRemovalKeydown)
})

onBeforeUnmount(() => window.removeEventListener('keydown', onRemovalKeydown))

function pickFiles() {
  if (!editing.value) fileInput.value?.click()
}

function onFilesChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''

  for (const file of files) {
    const upload: PendingUpload = {
      key: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      progress: 0,
      fileId: null,
      error: '',
    }
    uploads.value.push(upload)
    const entry = uploads.value.at(-1)!

    uploadFile(props.chat.id, file, (fraction) => {
      entry.progress = fraction
    })
      .then((saved) => {
        entry.progress = 1
        entry.fileId = saved.id
      })
      .catch((e: Error) => {
        entry.error = e.message
      })
  }
}

function removeUpload(key: string) {
  uploads.value = uploads.value.filter((item) => item.key !== key)
}

function toggleSearch() {
  searchOpen.value = !searchOpen.value
  searchQuery.value = ''
  searchResults.value = []
  searchDone.value = false
}

watch(searchQuery, (value) => {
  clearTimeout(searchTimer)
  searchDone.value = false
  const query = value.trim()
  if (!query) {
    searchResults.value = []
    return
  }

  searchTimer = setTimeout(async () => {
    isSearchingMessages.value = true
    try {
      const found = await searchMessages(props.chat.id, query)
      if (searchQuery.value.trim() === query) searchResults.value = found
    } catch {
      searchResults.value = []
    } finally {
      isSearchingMessages.value = false
      searchDone.value = true
    }
  }, 300)
})

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

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  clearTimeout(highlightTimer)
})

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
    editing.value = null
    uploads.value = []
    searchOpen.value = false
    searchQuery.value = ''
    searchResults.value = []
    nextTick(resizeInput)
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
        <UserAvatar v-else :url="chat.avatarUrl" :initials="chat.initials" />
        <span v-if="online" class="dialog__online" />
      </span>
      <span class="dialog__ident">
        <span class="dialog__title">{{ chat.title }}</span>
        <span v-if="chat.isSaved" class="dialog__status">заметки для себя</span>
        <span v-if="typing" class="dialog__status is-active">печатает…</span>
        <span v-else-if="online" class="dialog__status is-active">в сети</span>
      </span>

      <button
        type="button"
        class="dialog__tool"
        :class="{ 'is-active': searchOpen }"
        aria-label="Поиск по сообщениям"
        @click="toggleSearch"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
      </button>
    </header>

    <div v-if="searchOpen" class="dialog__search">
      <label class="dialog__search-field">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          v-model="searchQuery"
          class="dialog__search-input"
          type="search"
          placeholder="Поиск по сообщениям"
          aria-label="Поиск по сообщениям"
          autofocus
        />
      </label>

      <div v-if="searchQuery.trim()" class="dialog__results">
        <button
          v-for="result in searchResults"
          :key="result.id"
          type="button"
          class="dialog__result"
          @click="jumpTo(result)"
        >
          <span class="dialog__result-body">{{ result.body }}</span>
          <span class="dialog__result-time">{{ formatMessageTime(result.createdAt) }}</span>
        </button>
        <p v-if="isSearchingMessages" class="dialog__results-note">Ищем…</p>
        <p v-else-if="searchDone && !searchResults.length" class="dialog__results-note">
          Ничего не нашли
        </p>
      </div>
    </div>

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

    <div v-if="editing" class="dialog__editing">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M4 20h4L19 9l-4-4L4 16v4z" />
        <path d="M14 5l4 4" />
      </svg>
      <span class="dialog__editing-text">
        <span class="dialog__editing-label">Редактирование</span>
        <span class="dialog__editing-body">{{ editing.body }}</span>
      </span>
      <button type="button" class="dialog__chip-remove" aria-label="Отменить" @click="cancelEdit">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 6 6 18" />
          <path d="M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div v-if="uploads.length" class="dialog__uploads">
      <div
        v-for="upload in uploads"
        :key="upload.key"
        class="dialog__chip"
        :class="{ 'is-error': upload.error }"
      >
        <span class="dialog__chip-name">{{ upload.name }}</span>
        <span class="dialog__chip-status">
          {{ upload.error || (upload.fileId ? 'готово' : `${Math.round(upload.progress * 100)}%`) }}
        </span>
        <span
          v-if="!upload.fileId && !upload.error"
          class="dialog__chip-bar"
          :style="{ width: `${upload.progress * 100}%` }"
        />
        <button
          type="button"
          class="dialog__chip-remove"
          aria-label="Убрать файл"
          @click="removeUpload(upload.key)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <footer class="dialog__composer">
      <button
        type="button"
        class="dialog__tool"
        aria-label="Прикрепить файл"
        :disabled="!!editing"
        @click="pickFiles"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 11l-8.5 8.5a4.5 4.5 0 0 1-6.5-6.5L13 4.5a3 3 0 0 1 4.5 4L9 17" />
        </svg>
      </button>
      <input ref="fileInput" class="dialog__file" type="file" multiple @change="onFilesChosen" />

      <textarea
        ref="messageInput"
        v-model="draft"
        class="dialog__input"
        rows="1"
        :placeholder="editing ? 'Новый текст сообщения' : 'Сообщение'"
        aria-label="Сообщение"
        @input="emit('typing')"
        @keydown.enter="onEnter"
        @keydown.esc="cancelEdit"
      />

      <button
        type="button"
        class="dialog__send"
        :aria-label="editing ? 'Сохранить изменения' : 'Отправить'"
        :disabled="isSending || isUploading"
        @click="onSend"
      >
        <svg
          v-if="editing"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          aria-hidden="true"
        >
          <path d="M4 13l5 5 11-12" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M3 20.5 21.5 12 3 3.5l3.4 7.2 8.6 1.3-8.6 1.3z" />
        </svg>
      </button>
    </footer>

    <Teleport to="body">
      <Transition name="confirm">
        <div
          v-if="pendingRemoval"
          class="confirm"
          role="dialog"
          aria-modal="true"
          aria-label="Удаление сообщения"
          @click.self="pendingRemoval = null"
        >
          <div class="confirm__card">
            <h2 class="confirm__title">Удалить сообщение?</h2>
            <p class="confirm__text">Оно пропадёт у всех участников чата. Вернуть его не выйдет.</p>

            <div class="confirm__actions">
              <button type="button" class="confirm__btn" @click="pendingRemoval = null">
                Отмена
              </button>
              <button
                type="button"
                class="confirm__btn is-danger"
                :disabled="isRemoving"
                @click="confirmRemove"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M4 7h16" />
                  <path d="M10 11v6" />
                  <path d="M14 11v6" />
                  <path d="M6 7l1 13h10l1-13" />
                  <path d="M9 7V4h6v3" />
                </svg>
                {{ isRemoving ? 'Удаляем…' : 'Удалить' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
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
  align-items: flex-end;
  gap: 10px;
  flex: none;
  padding: 16px 20px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.dialog__input {
  height: 48px;
  min-height: 48px;
  max-height: 160px;
  flex: 1;
  min-width: 0;
  padding: 14px 18px;
  resize: none;
  overflow-y: auto;
  line-height: 1.5;
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

.dialog__ident {
  flex: 1;
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

.dialog__tool:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dialog__tool svg {
  width: 20px;
  height: 20px;
}

.dialog__file {
  display: none;
}

.dialog__search {
  position: relative;
  flex: none;
  padding: 12px 20px;
  background: var(--color-lift);
  border-bottom: 1px solid var(--chat-line);
}

.dialog__search-field {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 14px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
  color: var(--color-text-dim);
}

.dialog__search-field:focus-within {
  border-color: var(--color-focus);
}

.dialog__search-field svg {
  width: 16px;
  height: 16px;
  flex: none;
}

.dialog__search-input {
  width: 100%;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.dialog__search-input::placeholder {
  color: var(--color-text-dim);
}

.dialog__search-input::-webkit-search-cancel-button {
  display: none;
}

.dialog__results {
  position: absolute;
  top: 100%;
  right: 20px;
  left: 20px;
  z-index: 5;
  max-height: 320px;
  margin-top: 6px;
  overflow-y: auto;
  padding: 6px;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
  box-shadow: var(--shadow-hard);
}

.dialog__result {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  background: none;
  border: none;
  border-radius: var(--chat-radius);
  text-align: left;
  cursor: pointer;
}

.dialog__result:hover {
  background: var(--color-surface);
}

.dialog__result-body {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog__result-time {
  flex: none;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-dim);
}

.dialog__results-note {
  margin: 8px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.dialog__editing {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
  padding: 10px 20px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
  color: var(--color-accent);
}

.dialog__editing > svg {
  width: 18px;
  height: 18px;
  flex: none;
}

.dialog__editing-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
  padding-left: 10px;
  border-left: 2px solid var(--color-accent);
}

.dialog__editing-label {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-accent);
}

.dialog__editing-body {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog__uploads {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: none;
  padding: 10px 20px 0;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.dialog__chip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 260px;
  padding: 8px 8px 8px 12px;
  overflow: hidden;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius);
}

.dialog__chip.is-error {
  border-color: var(--color-error);
}

.dialog__chip-name {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog__chip-status {
  flex: none;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-dim);
}

.dialog__chip.is-error .dialog__chip-status {
  color: var(--color-error);
}

.dialog__chip-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--color-accent);
  transition: width 0.2s ease;
}

.dialog__chip-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex: none;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
}

.dialog__chip-remove:hover {
  color: var(--color-error);
}

.dialog__chip-remove svg {
  width: 14px;
  height: 14px;
}

.confirm {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(7, 11, 28, 0.88);
}

.confirm__card {
  width: 100%;
  max-width: 400px;
  padding: 26px 26px 22px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 18px;
  box-shadow: var(--shadow-hard);
}

.confirm__title {
  margin: 0 0 10px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 18px;
  color: var(--color-text);
}

.confirm__text {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.confirm__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 26px;
}

.confirm__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 46px;
  padding: 0 22px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: 14px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.confirm__btn:hover:not(:disabled) {
  background: var(--color-surface);
  border-color: var(--color-line);
}

.confirm__btn.is-danger {
  background: var(--color-error);
  border-color: var(--color-error);
  color: var(--color-ink);
}

.confirm__btn.is-danger:hover:not(:disabled) {
  background: rgba(255, 107, 94, 0.85);
  border-color: rgba(255, 107, 94, 0.85);
}

.confirm__btn svg {
  width: 17px;
  height: 17px;
  flex: none;
}

.confirm__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.confirm-enter-active {
  transition: opacity 0.18s ease;
}

.confirm-leave-active {
  transition: opacity 0.15s ease;
}

.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}

.confirm-enter-active .confirm__card {
  animation: confirm-pop 0.22s cubic-bezier(0.2, 0.9, 0.3, 1.2);
}

.confirm-leave-active .confirm__card {
  transition:
    transform 0.15s ease,
    opacity 0.15s ease;
}

.confirm-leave-to .confirm__card {
  opacity: 0;
  transform: scale(0.96);
}

@keyframes confirm-pop {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(12px);
  }

  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .confirm-enter-active .confirm__card,
  .confirm-leave-active .confirm__card {
    animation: none;
    transition: none;
  }
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
