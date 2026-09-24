<script setup lang="ts">
import type { Role } from '~/types/auth'

definePageMeta({ layout: false, middleware: 'administration' })

const auth = useAuthStore()
const { checkUsernameAvailable, createAccount } = useAdmin()

const canPickRole = computed(() => auth.user?.role === 'superuser')

const isFormOpen = ref(false)
const username = ref('')
const password = ref('')
const role = ref<Role>('user')
const isSubmitting = ref(false)
const submitError = ref('')
const justCreated = ref('')

type AvailabilityState = 'idle' | 'checking' | 'available' | 'taken' | 'invalid'
const availability = ref<AvailabilityState>('idle')
let usernameCheckTimer: ReturnType<typeof setTimeout> | undefined
let usernameCheckToken = 0

function openForm() {
  isFormOpen.value = true
  submitError.value = ''
  justCreated.value = ''
}

function closeForm() {
  isFormOpen.value = false
  username.value = ''
  password.value = ''
  role.value = 'user'
  availability.value = 'idle'
  submitError.value = ''
}

watch(username, (value) => {
  clearTimeout(usernameCheckTimer)
  const trimmed = value.trim()

  if (trimmed.length < 3) {
    availability.value = trimmed.length ? 'invalid' : 'idle'
    return
  }

  availability.value = 'checking'
  const token = ++usernameCheckToken
  usernameCheckTimer = setTimeout(async () => {
    try {
      const available = await checkUsernameAvailable(trimmed)
      if (token !== usernameCheckToken) return // устарел — пока ждали, юзернейм уже сменился
      availability.value = available ? 'available' : 'taken'
    } catch {
      if (token === usernameCheckToken) availability.value = 'idle'
    }
  }, 350)
})

const canSubmit = computed(
  () =>
    availability.value === 'available' &&
    password.value.length >= 8 &&
    !isSubmitting.value,
)

async function onSubmit() {
  if (!canSubmit.value) return

  isSubmitting.value = true
  submitError.value = ''
  try {
    const created = await createAccount({
      username: username.value.trim(),
      password: password.value,
      role: canPickRole.value ? role.value : 'user',
    })
    justCreated.value = created.username
    closeForm()
  } catch (e) {
    submitError.value = extractApiErrorMessage(e, 'Не удалось создать аккаунт')
  } finally {
    isSubmitting.value = false
  }
}

onBeforeUnmount(() => clearTimeout(usernameCheckTimer))
</script>

<template>
  <div class="admin-page">
    <header class="admin-page__head">
      <NuxtLink to="/administration" class="admin-page__back" aria-label="Назад">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </NuxtLink>
      <h1 class="admin-page__title">Управление пользователями</h1>
    </header>

    <div class="admin-page__body">
      <p v-if="justCreated" class="admin-note is-success">
        Аккаунт @{{ justCreated }} создан
      </p>

      <button v-if="!isFormOpen" type="button" class="admin-primary" @click="openForm">
        <span aria-hidden="true">＋</span> Создать пользователя
      </button>

      <form v-else class="admin-form" @submit.prevent="onSubmit">
        <label class="field">
          <span class="field__label">Логин</span>
          <span
            class="field__control is-editable"
            :class="{ 'is-invalid': availability === 'taken' || availability === 'invalid' }"
          >
            <input
              v-model.trim="username"
              class="field__input"
              type="text"
              minlength="3"
              maxlength="32"
              autocomplete="off"
              :disabled="isSubmitting"
              autofocus
            />
          </span>
          <span
            v-if="availability !== 'idle'"
            class="field__hint"
            :class="{
              'is-error': availability === 'taken' || availability === 'invalid',
              'is-ok': availability === 'available',
            }"
          >
            <template v-if="availability === 'checking'">Проверяем…</template>
            <template v-else-if="availability === 'available'">Логин свободен</template>
            <template v-else-if="availability === 'taken'">Логин уже занят</template>
            <template v-else>Не короче 3 символов</template>
          </span>
        </label>

        <label class="field">
          <span class="field__label">Пароль</span>
          <span class="field__control is-editable">
            <input
              v-model="password"
              class="field__input"
              type="password"
              minlength="8"
              maxlength="256"
              autocomplete="new-password"
              placeholder="Не короче 8 символов"
              :disabled="isSubmitting"
            />
          </span>
        </label>

        <label v-if="canPickRole" class="field">
          <span class="field__label">Роль</span>
          <span class="field__control field__control--select is-editable">
            <select v-model="role" class="field__input field__select" :disabled="isSubmitting">
              <option value="user">Пользователь</option>
              <option value="admin">Администратор</option>
            </select>
            <svg
              class="field__select-arrow"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </span>
        </label>

        <p v-if="submitError" class="admin-note is-error">{{ submitError }}</p>

        <div class="admin-form__actions">
          <button type="submit" class="admin-primary" :disabled="!canSubmit">
            {{ isSubmitting ? 'Создаём…' : 'Создать' }}
          </button>
          <button type="button" class="admin-secondary" :disabled="isSubmitting" @click="closeForm">
            Отмена
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--color-ground);
}

.admin-page__head {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 72px;
  padding: 0 28px;
  border-bottom: 1px solid var(--color-line);
}

.admin-page__back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--color-text-muted);
  transition: color 0.15s ease;
}

.admin-page__back:hover {
  color: var(--color-accent);
}

.admin-page__back svg {
  width: 20px;
  height: 20px;
}

.admin-page__title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 20px;
  color: var(--color-text);
}

.admin-page__body {
  max-width: 420px;
  padding: 28px;
}

.admin-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 26px;
  background: var(--color-accent);
  border: none;
  border-radius: var(--radius);
  box-shadow: 3px 3px 0 var(--color-ink);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-ink);
  cursor: pointer;
}

.admin-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.admin-primary:disabled {
  opacity: 0.5;
  box-shadow: none;
  cursor: not-allowed;
}

.admin-secondary {
  padding: 14px 22px;
  background: none;
  border: 1px solid var(--color-line);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  cursor: pointer;
}

.admin-secondary:hover:not(:disabled) {
  color: var(--color-text);
  border-color: var(--color-text-muted);
}

.admin-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__label {
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}

.field__control {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 14px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: var(--radius);
}

.field__control.is-editable:focus-within {
  border-color: var(--color-focus);
}

.field__control.is-invalid {
  border-color: var(--color-error);
}

.field__control--select {
  position: relative;
  padding-right: 12px;
}

.field__select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 24px;
  cursor: pointer;
  /* color-scheme makes Chromium/Firefox render the native <option> list
     with a dark palette instead of the OS-default white one — the
     control itself is already styled below regardless of browser. */
  color-scheme: dark;
}

.field__select option {
  background: var(--color-lift);
  color: var(--color-text);
}

.field__select-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  width: 16px;
  height: 16px;
  color: var(--color-text-dim);
  pointer-events: none;
  transform: translateY(-50%);
}

.field__input {
  width: 100%;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--color-text);
}

.field__input::placeholder {
  color: var(--color-text-dim);
}

.field__hint {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}

.field__hint.is-ok {
  color: var(--color-success);
}

.field__hint.is-error {
  color: var(--color-error);
}

.admin-form__actions {
  display: flex;
  gap: 14px;
  margin-top: 4px;
}

.admin-note {
  margin: 0 0 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.admin-note.is-error {
  color: var(--color-error);
}

.admin-note.is-success {
  color: var(--color-success);
}
</style>
