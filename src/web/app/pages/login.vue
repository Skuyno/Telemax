<script setup lang="ts">
definePageMeta({ layout: 'auth' })

type Mode = 'login' | 'register'

const mode = ref<Mode>('login')
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const { login, register } = useAuth()

function switchMode(next: Mode) {
  if (mode.value === next) return
  mode.value = next
  errorMessage.value = ''
  passwordConfirm.value = ''
}

async function onSubmit() {
  errorMessage.value = ''

  if (mode.value === 'register' && password.value !== passwordConfirm.value) {
    errorMessage.value = 'Пароли не совпадают'
    return
  }

  isSubmitting.value = true
  try {
    if (mode.value === 'login') {
      await login(username.value, password.value)
    } else {
      await register(username.value, password.value)
    }
    await navigateTo('/')
  } catch (e) {
    errorMessage.value = mapAuthErrorMessage(
      e,
      mode.value === 'login' ? 'Неверный логин или пароль' : 'Не удалось создать аккаунт',
    )
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-page__grid" aria-hidden="true" />

    <div class="auth-page__layout">
      <div class="auth-brand">
        <span class="auth-brand__logo">Телемакс</span>
        <h1 class="auth-brand__title">Личные и групповые чаты, звонки и файлы.</h1>
        <p class="auth-brand__subtitle">Один аккаунт — вся команда на связи.</p>
      </div>

      <div class="auth-card">
        <h2 class="auth-card__title">{{ mode === 'login' ? 'Вход' : 'Регистрация' }}</h2>

        <div class="auth-tabs" role="tablist">
          <button
            type="button"
            class="auth-tabs__item"
            :class="{ 'is-active': mode === 'login' }"
            role="tab"
            :aria-selected="mode === 'login'"
            @click="switchMode('login')"
          >
            Войти
          </button>
          <button
            type="button"
            class="auth-tabs__item"
            :class="{ 'is-active': mode === 'register' }"
            role="tab"
            :aria-selected="mode === 'register'"
            @click="switchMode('register')"
          >
            Регистрация
          </button>
        </div>

        <form class="auth-form" @submit.prevent="onSubmit">
          <label class="auth-field">
            <span class="auth-field__label">Логин</span>
            <input
              v-model.trim="username"
              class="auth-field__input"
              :class="{ 'is-invalid': errorMessage }"
              type="text"
              autocomplete="username"
              minlength="3"
              maxlength="32"
              required
            />
          </label>

          <label class="auth-field">
            <span class="auth-field__label">Пароль</span>
            <input
              v-model="password"
              class="auth-field__input"
              :class="{ 'is-invalid': errorMessage }"
              type="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              minlength="8"
              required
            />
          </label>

          <label v-if="mode === 'register'" class="auth-field">
            <span class="auth-field__label">Повтор пароля</span>
            <input
              v-model="passwordConfirm"
              class="auth-field__input"
              :class="{ 'is-invalid': errorMessage }"
              type="password"
              autocomplete="new-password"
              minlength="8"
              required
            />
          </label>

          <button class="auth-submit" type="submit" :disabled="isSubmitting">
            <span aria-hidden="true">▶</span>
            {{
              isSubmitting
                ? 'Подождите…'
                : mode === 'login'
                  ? 'Войти'
                  : 'Создать аккаунт'
            }}
          </button>

          <p v-if="errorMessage" class="auth-error">{{ errorMessage }}</p>
        </form>

        <p class="auth-switch">
          <template v-if="mode === 'login'">
            Нет аккаунта?
            <button type="button" class="auth-switch__link" @click="switchMode('register')">
              Создать
            </button>
          </template>
          <template v-else>
            Уже есть аккаунт?
            <button type="button" class="auth-switch__link" @click="switchMode('login')">
              Войти
            </button>
          </template>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  overflow: hidden;
}

.auth-page__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, rgba(120, 150, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(120, 150, 255, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
  -webkit-mask-image: linear-gradient(to bottom, transparent 50%, #000 100%);
  mask-image: linear-gradient(to bottom, transparent 50%, #000 100%);
  pointer-events: none;
}

.auth-page__layout {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1040px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}

@media (max-width: 860px) {
  .auth-page__layout {
    grid-template-columns: 1fr;
    gap: 40px;
  }
}

.auth-brand__logo {
  display: inline-block;
  margin-bottom: 48px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 32px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-accent);
}

.auth-brand__title {
  margin: 0 0 12px;
  max-width: 26ch;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 28px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.auth-brand__subtitle {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.auth-card {
  background: var(--color-lift);
  border: 1px solid rgba(61, 79, 156, 0.6);
  border-radius: var(--radius);
  box-shadow: var(--shadow-hard);
  padding: 32px;
}

.auth-card__title {
  margin: 0 0 20px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 18px;
  color: var(--color-text);
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  margin-bottom: 24px;
  border: 1px solid rgba(61, 79, 156, 0.6);
  border-radius: var(--radius);
  overflow: hidden;
}

.auth-tabs__item {
  padding: 10px;
  background: transparent;
  border: none;
  border-left: 1px solid rgba(61, 79, 156, 0.6);
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text-dim);
  cursor: pointer;
}

.auth-tabs__item:first-child {
  border-left: none;
}

.auth-tabs__item.is-active {
  background: var(--color-surface);
  color: var(--color-text);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.auth-field__label {
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}

.auth-field__input {
  padding: 10px 12px;
  background: var(--color-ground);
  border: 1px solid rgba(61, 79, 156, 0.6);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.auth-field__input::placeholder {
  color: var(--color-text-dim);
}

.auth-field__input:focus {
  outline: none;
  border-color: var(--color-focus);
}

.auth-field__input.is-invalid {
  border-color: var(--color-error);
}

.auth-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
  padding: 12px;
  background: var(--color-accent);
  color: var(--color-ink);
  border: none;
  border-radius: var(--radius);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  cursor: pointer;
}

.auth-submit:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.auth-submit:active:not(:disabled) {
  background: var(--color-accent-pressed);
}

.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-error);
}

.auth-switch {
  margin: 20px 0 0;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.auth-switch__link {
  padding: 0;
  background: none;
  border: none;
  font: inherit;
  color: var(--color-accent);
  cursor: pointer;
}

.auth-switch__link:hover {
  color: var(--color-accent-hover);
}
</style>
