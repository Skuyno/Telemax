<script setup lang="ts">
import type { PendingUpload } from '~/types/chat'

definePageMeta({ layout: false, middleware: 'administration' })

const { getBroadcastChat, sendBroadcast } = useAdmin()
const { uploadFile } = useFiles()

const chatId = ref('')
const isPreparing = ref(true)
const prepareError = ref('')

const body = ref('')
const uploads = ref<PendingUpload[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const isSending = ref(false)
const sendError = ref('')
const sentTo = ref<number | null>(null)

const isUploading = computed(() => uploads.value.some((item) => !item.fileId && !item.error))
const readyAttachmentIds = computed(() =>
  uploads.value.flatMap((item) => (item.fileId ? [item.fileId] : [])),
)
const canSubmit = computed(
  () =>
    !!chatId.value &&
    !isSending.value &&
    !isUploading.value &&
    (body.value.trim().length > 0 || readyAttachmentIds.value.length > 0),
)

onMounted(async () => {
  try {
    chatId.value = await getBroadcastChat()
  } catch (e) {
    prepareError.value = extractApiErrorMessage(e, 'Не удалось подготовить рассылку')
  } finally {
    isPreparing.value = false
  }
})

function pickFiles() {
  fileInput.value?.click()
}

function onFilesChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  for (const file of files) addUpload(file)
}

function addUpload(file: File) {
  const key = `${file.name}-${file.size}-${Date.now()}-${Math.random()}`
  const item: PendingUpload = { key, name: file.name, size: file.size, progress: 0, fileId: null, error: '' }
  uploads.value.push(item)

  uploadFile(chatId.value, file, (fraction) => {
    item.progress = fraction
  })
    .then((saved) => {
      item.fileId = saved.id
      item.progress = 1
    })
    .catch((e: unknown) => {
      item.error = extractApiErrorMessage(e, 'Не удалось загрузить файл')
    })
}

function removeUpload(key: string) {
  uploads.value = uploads.value.filter((item) => item.key !== key)
}

async function onSubmit() {
  if (!canSubmit.value) return
  isSending.value = true
  sendError.value = ''
  sentTo.value = null
  try {
    sentTo.value = await sendBroadcast({
      body: body.value.trim(),
      attachmentFileIds: readyAttachmentIds.value,
    })
    body.value = ''
    uploads.value = []
  } catch (e) {
    sendError.value = extractApiErrorMessage(e, 'Не удалось отправить рассылку')
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <div class="tmx-page page">
    <AdminHeader title="Рассылка" back="/administration" />

    <main class="stage">
      <div class="card">
        <p class="hint">
          Сообщение получат все пользователи — в их собственном чате «Уведомления». Писать
          в этот чат не сможет никто, кроме рассылки.
        </p>

        <p v-if="isPreparing" class="status">Готовим рассылку…</p>
        <p v-else-if="prepareError" class="error">{{ prepareError }}</p>

        <template v-else>
          <label class="field">
            <span class="label">Текст сообщения</span>
            <textarea
              v-model="body"
              class="textarea"
              rows="6"
              placeholder="О чём хотите сообщить всем пользователям?"
              :disabled="isSending"
            />
          </label>

          <div class="uploads">
            <button type="button" class="btn-attach" :disabled="isSending" @click="pickFiles">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21.44 11.05l-9.19 9.19a5 5 0 0 1-7.07-7.07l9.19-9.19a3 3 0 0 1 4.24 4.24l-9.19 9.19a1 1 0 0 1-1.41-1.41l8.48-8.49" />
              </svg>
              Прикрепить файлы
            </button>
            <input ref="fileInput" type="file" multiple hidden @change="onFilesChosen" />

            <ul v-if="uploads.length" class="upload-list">
              <li v-for="item in uploads" :key="item.key" class="upload-item">
                <span class="upload-name">{{ item.name }}</span>
                <span v-if="item.error" class="upload-error">{{ item.error }}</span>
                <span v-else-if="item.fileId" class="upload-ok">готово</span>
                <span v-else class="upload-progress">{{ Math.round(item.progress * 100) }}%</span>
                <button
                  type="button"
                  class="upload-remove"
                  aria-label="Убрать файл"
                  @click="removeUpload(item.key)"
                >
                  ×
                </button>
              </li>
            </ul>
          </div>

          <p v-if="sendError" class="error">{{ sendError }}</p>
          <p v-if="sentTo !== null" class="success">Отправлено {{ sentTo }} пользователям</p>

          <button type="button" class="btn-primary" :disabled="!canSubmit" @click="onSubmit">
            {{ isSending ? 'Отправляем…' : 'Отправить всем' }}
          </button>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.tmx-page {
  position: relative;
  min-height: 100vh;
}

.page {
  display: flex;
  flex-direction: column;
  background: radial-gradient(900px 520px at 50% 60%, #1a2668 0%, #101a49 45%, var(--color-ink) 100%);
}

.stage {
  display: grid;
  place-items: center;
  flex: 1;
  padding: 44px 24px;
}

.card {
  width: 100%;
  max-width: 560px;
  padding: 28px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 18px;
  box-shadow: var(--shadow-hard);
}

.hint {
  margin: 0 0 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.status {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text-muted);
}

.field {
  display: block;
  margin-bottom: 16px;
}

.label {
  display: block;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}

.textarea {
  width: 100%;
  padding: 12px 14px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  border-radius: 12px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
  resize: vertical;
}

.textarea:focus {
  outline: none;
  border-color: var(--color-focus);
}

.uploads {
  margin-bottom: 16px;
}

.btn-attach {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
  cursor: pointer;
}

.btn-attach svg {
  width: 16px;
  height: 16px;
}

.btn-attach:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-list {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--color-ground);
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}

.upload-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text);
}

.upload-ok {
  color: var(--color-success);
}

.upload-error {
  color: var(--color-error);
}

.upload-remove {
  flex: none;
  width: 18px;
  height: 18px;
  background: none;
  border: none;
  color: var(--color-text-dim);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}

.error {
  margin: 0 0 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-error);
}

.success {
  margin: 0 0 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-success);
}

.btn-primary {
  width: 100%;
  height: 48px;
  background: var(--color-accent);
  border: none;
  border-radius: 12px;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 14px;
  color: var(--color-ink);
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
