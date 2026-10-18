<script setup lang="ts">
import type { Message, PendingUpload } from '~/types/chat'

const props = defineProps<{ chatId: string; editing: Message | null; busy?: boolean }>()

const emit = defineEmits<{
  submit: [string, string[]]
  cancelEdit: []
  typing: []
}>()

const { uploadFile } = useFiles()

const draft = ref('')
const uploads = ref<PendingUpload[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const messageInput = ref<HTMLTextAreaElement | null>(null)

const isUploading = computed(() => uploads.value.some((item) => !item.fileId && !item.error))
const readyAttachmentIds = computed(() =>
  uploads.value.flatMap((item) => (item.fileId ? [item.fileId] : [])),
)

function onSubmit() {
  const text = draft.value.trim()
  if (props.busy || isUploading.value) return
  if (!text && !readyAttachmentIds.value.length) return

  emit('submit', text, readyAttachmentIds.value)
}

function reset() {
  draft.value = ''
  uploads.value = []
  nextTick(resizeInput)
}

function focus() {
  nextTick(() => messageInput.value?.focus())
}

defineExpose({ reset, focus })

function onEnter(event: KeyboardEvent) {
  event.preventDefault()
  if (event.ctrlKey || event.metaKey || event.shiftKey) insertNewline()
  else onSubmit()
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

watch(
  () => props.editing,
  (message) => {
    if (!message) return
    uploads.value = []
    draft.value = message.body
    focus()
  },
)

watch(
  () => props.chatId,
  () => reset(),
)

onMounted(() => resizeInput())

function pickFiles() {
  if (!props.editing) fileInput.value?.click()
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

    uploadFile(props.chatId, file, (fraction) => {
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

function onCancelEdit() {
  draft.value = ''
  emit('cancelEdit')
}
</script>

<template>
  <div class="composer">
    <div v-if="editing" class="editing">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M4 20h4L19 9l-4-4L4 16v4z" />
        <path d="M14 5l4 4" />
      </svg>
      <span class="editing__text">
        <span class="editing__label">Редактирование</span>
        <span class="editing__body">{{ editing.body }}</span>
      </span>
      <button type="button" class="chip__remove" aria-label="Отменить" @click="onCancelEdit">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 6 6 18" />
          <path d="M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div v-if="uploads.length" class="uploads">
      <div
        v-for="upload in uploads"
        :key="upload.key"
        class="chip"
        :class="{ 'is-error': upload.error }"
      >
        <span class="chip__name">{{ upload.name }}</span>
        <span class="chip__status">
          {{ upload.error || (upload.fileId ? 'готово' : `${Math.round(upload.progress * 100)}%`) }}
        </span>
        <span
          v-if="!upload.fileId && !upload.error"
          class="chip__bar"
          :style="{ width: `${upload.progress * 100}%` }"
        />
        <button
          type="button"
          class="chip__remove"
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

    <footer class="bar">
      <button
        type="button"
        class="tool"
        aria-label="Прикрепить файл"
        :disabled="!!editing"
        @click="pickFiles"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 11l-8.5 8.5a4.5 4.5 0 0 1-6.5-6.5L13 4.5a3 3 0 0 1 4.5 4L9 17" />
        </svg>
      </button>
      <input ref="fileInput" class="file" type="file" multiple @change="onFilesChosen" />

      <textarea
        ref="messageInput"
        v-model="draft"
        class="input"
        rows="1"
        :placeholder="editing ? 'Новый текст сообщения' : 'Сообщение'"
        aria-label="Сообщение"
        @input="emit('typing')"
        @keydown.enter="onEnter"
        @keydown.esc="onCancelEdit"
      />

      <button
        type="button"
        class="send"
        :aria-label="editing ? 'Сохранить изменения' : 'Отправить'"
        :disabled="busy || isUploading"
        @click="onSubmit"
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
  </div>
</template>

<style scoped>
.composer {
  display: flex;
  flex-direction: column;
  flex: none;
}

.bar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex: none;
  padding: 16px 20px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.input {
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

.input::placeholder {
  color: var(--color-text-dim);
}

.input:focus {
  border-color: var(--color-focus);
}

.send {
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

.send svg {
  width: 20px;
  height: 20px;
}

.send:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.send:active:not(:disabled) {
  background: var(--color-accent-pressed);
}

.send:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tool {
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

.tool:hover:not(:disabled) {
  color: var(--color-accent);
  border-color: var(--chat-accent-soft);
}

.tool:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tool svg {
  width: 20px;
  height: 20px;
}

.file {
  display: none;
}

.editing {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
  padding: 10px 20px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
  color: var(--color-accent);
}

.editing > svg {
  width: 18px;
  height: 18px;
  flex: none;
}

.editing__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
  padding-left: 10px;
  border-left: 2px solid var(--color-accent);
}

.editing__label {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-accent);
}

.editing__body {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uploads {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: none;
  padding: 10px 20px 0;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.chip {
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

.chip.is-error {
  border-color: var(--color-error);
}

.chip__name {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip__status {
  flex: none;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-dim);
}

.chip.is-error .chip__status {
  color: var(--color-error);
}

.chip__bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--color-accent);
  transition: width 0.2s ease;
}

.chip__remove {
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

.chip__remove:hover {
  color: var(--color-error);
}

.chip__remove svg {
  width: 14px;
  height: 14px;
}

@media (max-width: 900px) {
  .bar {
    padding-inline: 14px;
  }
}
</style>
