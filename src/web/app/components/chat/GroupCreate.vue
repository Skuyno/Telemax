<script setup lang="ts">
import type { UserSearchResult } from '~/types/chat'

const emit = defineEmits<{ close: []; created: [string] }>()

const chatStore = useChatStore()
const { searchUsers, createGroupChat } = useChats()

const title = ref('')
const query = ref('')
const picked = ref<UserSearchResult[]>([])
const isSubmitting = ref(false)
const error = ref('')

const canSubmit = computed(
  () => title.value.trim().length > 0 && picked.value.length > 0 && !isSubmitting.value,
)

const results = computed(() =>
  chatStore.userResults.filter((user) => !picked.value.some((item) => item.id === user.id)),
)

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(query, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => searchUsers(value), 300)
})

function pick(user: UserSearchResult) {
  picked.value = [...picked.value, user]
  query.value = ''
  chatStore.userResults = []
}

function unpick(id: string) {
  picked.value = picked.value.filter((user) => user.id !== id)
}

async function onSubmit() {
  if (!canSubmit.value) return

  isSubmitting.value = true
  error.value = ''
  try {
    const chatId = await createGroupChat(title.value, picked.value)
    emit('created', chatId)
  } catch (e) {
    error.value = extractApiErrorMessage(e, 'Не удалось создать группу')
  } finally {
    isSubmitting.value = false
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  chatStore.userResults = []
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div
      class="overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Новая группа"
      @click.self="emit('close')"
    >
      <div class="card">
        <h2 class="card__title">Новая группа</h2>

        <label class="field">
          <span class="field__label">Название</span>
          <input
            v-model="title"
            class="field__input"
            type="text"
            maxlength="128"
            placeholder="Например, Команда Телемакс"
            :disabled="isSubmitting"
            autofocus
          />
        </label>

        <div v-if="picked.length" class="picked">
          <span v-for="user in picked" :key="user.id" class="picked__chip">
            {{ user.title }}
            <button
              type="button"
              class="picked__remove"
              :aria-label="`Убрать ${user.title}`"
              @click="unpick(user.id)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M18 6 6 18" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </span>
        </div>

        <label class="field">
          <span class="field__label">Участники</span>
          <input
            v-model="query"
            class="field__input"
            type="search"
            placeholder="Поиск по @username"
            :disabled="isSubmitting"
          />
        </label>

        <div v-if="query.trim()" class="results">
          <button
            v-for="user in results"
            :key="user.id"
            type="button"
            class="results__item"
            @click="pick(user)"
          >
            <UserAvatar :url="user.avatarUrl" :initials="user.initials" />
            <span class="results__text">
              <span class="results__name">{{ user.title }}</span>
              <span class="results__tag">@{{ user.username }}</span>
            </span>
          </button>

          <p v-if="chatStore.isSearchingUsers" class="results__note">Ищем…</p>
          <p v-else-if="!results.length" class="results__note">Никого не нашли</p>
        </div>

        <p v-if="error" class="card__error">{{ error }}</p>

        <div class="card__actions">
          <button type="button" class="btn" :disabled="isSubmitting" @click="emit('close')">
            Отмена
          </button>
          <button type="button" class="btn is-primary" :disabled="!canSubmit" @click="onSubmit">
            {{ isSubmitting ? 'Создаём…' : 'Создать' }}
          </button>
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

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__label {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.field__input {
  height: 46px;
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

.picked {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.picked__chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px 6px 12px;
  background: var(--color-surface);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
}

.picked__remove {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
}

.picked__remove:hover {
  color: var(--color-error);
}

.picked__remove svg {
  width: 13px;
  height: 13px;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 220px;
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

.results__item:hover {
  background: var(--color-surface);
}

.results__item > :first-child {
  width: 36px;
  height: 36px;
  flex: none;
}

.results__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.results__name {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
}

.results__tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.results__note {
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
  gap: 12px;
  margin-top: 4px;
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

.btn:hover:not(:disabled) {
  background: var(--color-surface);
}

.btn.is-primary {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-ink);
}

.btn.is-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
