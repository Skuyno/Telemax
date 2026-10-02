<script setup lang="ts">
import type { Role } from '~/types/auth'

definePageMeta({ layout: false, middleware: 'administration' })

const auth = useAuthStore()
const { checkUsernameAvailable, createAccount } = useAdmin()

const canPickRole = computed(() => auth.user?.role === 'superuser')

const ring = [
  { icon: 'user', tone: 'neutral', angle: -90, radius: 210 },
  { icon: 'shield', tone: 'accent', angle: -30, radius: 210 },
  { icon: 'profile', tone: 'signal', angle: 30, radius: 210 },
  { icon: 'user', tone: 'neutral', angle: 90, radius: 210 },
  { icon: 'key', tone: 'accent', angle: 150, radius: 210 },
  { icon: 'at', tone: 'signal', angle: 210, radius: 210 },
] as const

const isFormOpen = ref(false)
const username = ref('')
const password = ref('')
const role = ref<Role>('user')
const isSubmitting = ref(false)
const submitError = ref('')
const justCreated = ref('')
const isPasswordVisible = ref(false)

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
  isPasswordVisible.value = false
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
  () => availability.value === 'available' && password.value.length >= 8 && !isSubmitting.value,
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
  <div class="tmx-page page">
    <AdminHeader title="Управление пользователями" back="/administration" />

    <main class="stage">
      <div v-if="!isFormOpen" class="orbit">
        <span class="o o1" aria-hidden="true" />
        <span class="o o2" aria-hidden="true" />
        <span class="o o3" aria-hidden="true" />
        <AdminOrbitTile v-for="(tile, index) in ring" :key="index" v-bind="tile" />

        <div class="center">
          <span class="core" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <circle cx="10" cy="8" r="3.6" />
              <path d="M3.6 19.5a6.4 6.4 0 0 1 12.8 0z" />
              <path d="M18 9.5v5M15.5 12h5" stroke="currentColor" stroke-width="2" />
            </svg>
          </span>
          <p v-if="justCreated" class="created">Аккаунт @{{ justCreated }} создан</p>
          <button type="button" class="btn-create" @click="openForm">
            <span aria-hidden="true">+</span> Создать пользователя
          </button>
        </div>
      </div>

      <form v-else class="card" @submit.prevent="onSubmit">
        <div class="art" aria-hidden="true">
          <span class="art-grid" />
          <span class="art-ring art-ring--outer" />
          <span class="art-ring" />
          <span class="art-glow" />
          <span class="art-core">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <circle cx="10" cy="8" r="3.6" />
              <path d="M3.6 19.5a6.4 6.4 0 0 1 12.8 0z" />
              <path d="M18 9.5v5M15.5 12h5" stroke="currentColor" stroke-width="2" />
            </svg>
          </span>
          <AdminOrbitTile icon="at" tone="signal" :angle="-135" :radius="120" :size="38" />
          <AdminOrbitTile icon="lock" tone="accent" :angle="-45" :radius="120" :size="38" />
          <AdminOrbitTile icon="shield" tone="accent" :angle="45" :radius="120" :size="38" />
          <AdminOrbitTile icon="user" tone="neutral" :angle="135" :radius="120" :size="38" />
          <AdminOrbitTile icon="key" tone="neutral" :angle="0" :radius="153" :size="32" />
          <AdminOrbitTile icon="profile" tone="signal" :angle="180" :radius="153" :size="32" />
          <span class="art-label">Новый аккаунт</span>
        </div>

        <div class="fields">
          <label class="field">
            <span class="label">Логин</span>
            <span
              class="input"
              :class="{ 'is-invalid': availability === 'taken' || availability === 'invalid' }"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M16 8v5a3 3 0 0 0 5-2 9 9 0 1 0-3.5 7" />
              </svg>
              <input
                v-model.trim="username"
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
              class="hint"
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
            <span class="label">Пароль</span>
            <span class="input">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <rect x="5" y="11" width="14" height="9" rx="2" />
                <path d="M8 11V8a4 4 0 0 1 8 0v3" />
              </svg>
              <input
                v-model="password"
                :type="isPasswordVisible ? 'text' : 'password'"
                minlength="8"
                maxlength="256"
                autocomplete="new-password"
                placeholder="Не короче 8 символов"
                :disabled="isSubmitting"
              />
              <button
                type="button"
                class="eye"
                :aria-label="isPasswordVisible ? 'Скрыть пароль' : 'Показать пароль'"
                @click="isPasswordVisible = !isPasswordVisible"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                  <path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6z" />
                  <circle cx="12" cy="12" r="3" />
                  <path v-if="isPasswordVisible" d="M4 20 20 4" />
                </svg>
              </button>
            </span>
          </label>

          <label v-if="canPickRole" class="field">
            <span class="label">Роль</span>
            <span class="input input--select">
              <select v-model="role" class="select" :disabled="isSubmitting">
                <option value="user">Пользователь</option>
                <option value="admin">Администратор</option>
              </select>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </span>
          </label>

          <p v-if="submitError" class="error">{{ submitError }}</p>

          <div class="actions">
            <button type="button" class="btn-ghost" :disabled="isSubmitting" @click="closeForm">
              Отмена
            </button>
            <button type="submit" class="btn-primary" :disabled="!canSubmit">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                <path d="M4 13l5 5 11-12" />
              </svg>
              {{ isSubmitting ? 'Создаём…' : 'Создать' }}
            </button>
          </div>
        </div>
      </form>
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

.page::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(120, 150, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 150, 255, 0.05) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(circle at 50% 60%, #000, transparent 70%);
}

.stage {
  position: relative;
  display: grid;
  place-items: center;
  flex: 1;
  padding: 48px 16px;
}

.orbit {
  position: relative;
  display: grid;
  place-items: center;
  width: 420px;
  height: 420px;
}

.o {
  position: absolute;
  border-radius: 50%;
}

.o1 {
  inset: 0;
  box-shadow: inset 0 0 0 1px rgba(61, 79, 156, 0.45);
}

.o2 {
  inset: 70px;
  box-shadow: inset 0 0 0 1px rgba(255, 204, 46, 0.22);
}

.o3 {
  inset: 130px;
  background: radial-gradient(circle, rgba(255, 204, 46, 0.16), transparent 70%);
}

.center {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
}

.core {
  display: grid;
  place-items: center;
  width: 88px;
  height: 88px;
  background: linear-gradient(140deg, var(--color-accent), var(--color-accent-pressed));
  border-radius: 26px;
  box-shadow: 0 0 60px rgba(255, 204, 46, 0.4);
  color: var(--color-ink);
}

.core svg {
  width: 40px;
  height: 40px;
}

.created {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-success);
}

.btn-create {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: none;
  height: 48px;
  padding: 0 24px;
  background: var(--color-lift);
  border: none;
  border-radius: 13px;
  box-shadow:
    inset 0 0 0 1px var(--color-accent),
    0 12px 30px rgba(0, 0, 0, 0.35);
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 14.5px;
  white-space: nowrap;
  color: var(--color-accent);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.btn-create:hover {
  background: var(--color-accent);
  color: var(--color-ink);
}

.card {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  width: 100%;
  max-width: 880px;
  overflow: hidden;
  background: var(--color-lift);
  border-radius: 20px;
  box-shadow:
    inset 0 0 0 1px rgba(61, 79, 156, 0.75),
    0 24px 60px rgba(0, 0, 0, 0.45);
}

.art {
  position: relative;
  min-height: 440px;
  padding-bottom: 36px;
  overflow: hidden;
  background: linear-gradient(160deg, #27347e, #1a2566 60%, #141e58);
}

.art-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 204, 46, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 204, 46, 0.07) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(circle at 50% 50%, #000, transparent 70%);
}

.art-ring,
.art-glow,
.art-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.art-ring {
  width: 240px;
  height: 240px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(255, 204, 46, 0.25);
}

.art-ring--outer {
  width: 306px;
  height: 306px;
  border: 1px dashed rgba(79, 216, 255, 0.22);
  box-shadow: none;
  animation: art-spin 70s linear infinite;
}

.art-glow {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 204, 46, 0.22), transparent 70%);
  animation: art-pulse 5s ease-in-out infinite;
}

@keyframes art-spin {
  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

@keyframes art-pulse {
  0%,
  100% {
    opacity: 0.75;
    transform: translate(-50%, -50%) scale(1);
  }

  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.12);
  }
}

@media (prefers-reduced-motion: reduce) {
  .art-ring--outer,
  .art-glow {
    animation: none;
  }
}

.art-core {
  display: grid;
  place-items: center;
  width: 92px;
  height: 92px;
  background: linear-gradient(140deg, var(--color-accent), var(--color-accent-pressed));
  border-radius: 26px;
  box-shadow: 0 0 50px rgba(255, 204, 46, 0.45);
  color: var(--color-ink);
}

.art-core svg {
  width: 42px;
  height: 42px;
}

.art-label {
  position: absolute;
  right: 0;
  bottom: 30px;
  left: 0;
  text-shadow: 0 0 22px rgba(255, 204, 46, 0.35);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.04em;
  text-align: center;
  text-transform: uppercase;
  color: var(--color-accent);
}

.fields {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 22px;
  padding: 40px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.label {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.input {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 50px;
  padding: 0 16px;
  background: var(--color-ink);
  border-radius: 13px;
  box-shadow: inset 0 0 0 1px rgba(61, 79, 156, 0.75);
  transition: box-shadow 0.15s ease;
}

.input > svg {
  width: 18px;
  height: 18px;
  flex: none;
  color: var(--color-text-muted);
}

.input:focus-within {
  box-shadow:
    inset 0 0 0 1px var(--color-focus),
    0 0 0 4px rgba(79, 216, 255, 0.12);
}

.input:focus-within > svg {
  color: var(--color-focus);
}

.input.is-invalid {
  box-shadow: inset 0 0 0 1px var(--color-error);
}

.input input {
  flex: 1;
  min-width: 0;
  height: 100%;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--color-text);
  caret-color: var(--color-focus);
}

.input input::placeholder {
  color: var(--color-text-dim);
}

.input--select {
  position: relative;
}

.input--select > svg {
  position: absolute;
  right: 16px;
  width: 16px;
  height: 16px;
  color: var(--color-text-dim);
  pointer-events: none;
}

.select {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding-right: 24px;
  appearance: none;
  -webkit-appearance: none;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
  /* color-scheme makes Chromium/Firefox render the native <option> list
     with a dark palette instead of the OS-default white one — the
     control itself is already styled below regardless of browser. */
  color-scheme: dark;
}

.select option {
  background: var(--color-lift);
  color: var(--color-text);
}

.eye {
  display: grid;
  place-items: center;
  flex: none;
  padding: 4px;
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
}

.eye:hover {
  color: var(--color-text);
}

.eye svg {
  width: 18px;
  height: 18px;
}

.hint {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}

.hint.is-ok {
  color: var(--color-success);
}

.hint.is-error {
  color: var(--color-error);
}

.error {
  margin: -8px 0 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-error);
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.btn-ghost,
.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  height: 50px;
  border-radius: 13px;
  font-family: var(--font-heading);
  font-size: 14px;
  cursor: pointer;
}

.btn-ghost {
  flex: 1;
  background: none;
  border: none;
  box-shadow: inset 0 0 0 1px rgba(61, 79, 156, 0.75);
  font-weight: 600;
  color: var(--color-text-muted);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--color-surface);
  color: var(--color-text);
}

.btn-primary {
  flex: 1.5;
  background: var(--color-accent);
  border: none;
  box-shadow: 0 10px 26px rgba(255, 204, 46, 0.28);
  font-weight: 700;
  color: var(--color-ink);
  transition:
    background 0.15s ease,
    opacity 0.15s ease;
}

.btn-primary svg {
  width: 17px;
  height: 17px;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.btn-primary:active:not(:disabled) {
  background: var(--color-accent-pressed);
}

.btn-primary:disabled {
  opacity: 0.45;
  box-shadow: none;
  cursor: default;
}

.btn-ghost:disabled {
  opacity: 0.45;
  cursor: default;
}

@media (max-width: 760px) {
  .card {
    grid-template-columns: 1fr;
  }

  .art {
    display: none;
  }

  .stage {
    padding: 24px 16px;
  }

  .fields {
    padding: 28px 22px;
  }
}

@media (max-width: 480px) {
  .orbit {
    width: 100%;
    height: auto;
  }

  .o,
  .orbit :deep(.tile) {
    display: none;
  }
}
</style>
