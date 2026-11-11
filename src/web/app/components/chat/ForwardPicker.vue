<script setup lang="ts">
import type { Chat, Message } from '~/types/chat'

const props = defineProps<{ message: Message }>()

const emit = defineEmits<{ close: []; forwarded: [string] }>()

const chatStore = useChatStore()
const { forwardMessage } = useChats()

const query = ref('')
const sendingTo = ref<string | null>(null)
const error = ref('')

const targets = computed(() => {
  const search = query.value.trim().replace(/^@/, '').toLowerCase()
  return chatStore.chats.filter(
    (chat) =>
      chat.type !== 'notifications' && (!search || chat.title.toLowerCase().includes(search)),
  )
})

async function onPick(chat: Chat) {
  if (sendingTo.value) return

  sendingTo.value = chat.id
  error.value = ''
  try {
    await forwardMessage(chat.id, props.message)
    emit('forwarded', chat.id)
  } catch (e) {
    error.value = extractApiErrorMessage(e, 'Не удалось переслать сообщение')
  } finally {
    sendingTo.value = null
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      class="overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Переслать сообщение"
      @click.self="emit('close')"
    >
      <div class="card">
        <h2 class="card__title">Переслать</h2>

        <input
          v-model="query"
          class="field__input"
          type="search"
          placeholder="Поиск чата"
          aria-label="Поиск чата"
          autofocus
        />

        <div class="results">
          <button
            v-for="chat in targets"
            :key="chat.id"
            type="button"
            class="results__item"
            :disabled="!!sendingTo"
            @click="onPick(chat)"
          >
            <span class="results__avatar">
              <ChatSavedIcon v-if="chat.isSaved" />
              <ChatGroupIcon v-else-if="chat.type === 'group'" />
              <UserAvatar v-else :url="chat.avatarUrl" :initials="chat.initials" />
            </span>
            <span class="results__name">{{ chat.title }}</span>
            <span v-if="sendingTo === chat.id" class="results__note">Пересылаем…</span>
          </button>

          <p v-if="!targets.length" class="results__empty">Ничего не нашли</p>
        </div>

        <p v-if="error" class="card__error">{{ error }}</p>

        <div class="card__actions">
          <button type="button" class="btn" @click="emit('close')">Отмена</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(7, 11, 28, 0.88);
}

.card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 420px;
  max-height: 100%;
  padding: 26px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
}

.card__title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 18px;
  color: var(--color-text);
}

.field__input {
  height: 46px;
  flex: none;
  padding: 0 16px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  border-radius: 12px;
  outline: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.field__input:focus {
  border-color: var(--color-focus);
}

.field__input::placeholder {
  color: var(--color-text-dim);
}

.field__input::-webkit-search-cancel-button {
  display: none;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  max-height: 320px;
  overflow-y: auto;
}

.results__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background: none;
  border: none;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
}

.results__item:hover:not(:disabled) {
  background: var(--color-surface);
}

.results__item:disabled {
  cursor: default;
}

.results__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: 10px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-accent);
}

.results__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.results__note {
  flex: none;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.results__empty {
  margin: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.card__error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-error);
}

.card__actions {
  display: flex;
  justify-content: flex-end;
}

.btn {
  height: 44px;
  padding: 0 22px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  border-radius: 14px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
}

.btn:hover {
  background: var(--color-surface);
}
</style>
