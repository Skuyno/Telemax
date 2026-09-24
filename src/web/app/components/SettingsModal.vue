<script setup lang="ts">
import type { UserSettings } from '~/types/settings'

const auth = useAuthStore()
const settingsStore = useSettingsStore()
const { load, update } = useSettings()
const { logout, updateProfile, uploadAvatar, removeAvatar, resetPassword } = useAuth()

const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const AVATAR_MAX_BYTES = 5 * 1024 * 1024

const avatarInput = ref<HTMLInputElement | null>(null)
const isAvatarBusy = ref(false)
const avatarError = ref('')

function pickAvatar() {
  if (!isAvatarBusy.value) avatarInput.value?.click()
}

async function onAvatarChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  avatarError.value = ''
  if (!AVATAR_TYPES.includes(file.type)) {
    avatarError.value = 'Подойдёт картинка в формате JPG, PNG, WEBP или GIF'
    return
  }
  if (file.size > AVATAR_MAX_BYTES) {
    avatarError.value = 'Файл больше 5 МБ — выберите картинку поменьше'
    return
  }

  isAvatarBusy.value = true
  try {
    await uploadAvatar(file)
  } catch (e) {
    avatarError.value = extractApiErrorMessage(e, 'Не удалось загрузить фото')
  } finally {
    isAvatarBusy.value = false
  }
}

async function onAvatarRemove() {
  avatarError.value = ''
  isAvatarBusy.value = true
  try {
    await removeAvatar()
  } catch (e) {
    avatarError.value = extractApiErrorMessage(e, 'Не удалось удалить фото')
  } finally {
    isAvatarBusy.value = false
  }
}

const profile = reactive({ displayName: '', email: '' })

watch(
  () => auth.user,
  (user) => {
    profile.displayName = user?.displayName ?? ''
    profile.email = user?.email ?? ''
  },
  { immediate: true },
)

const nameChanged = computed(() => profile.displayName.trim() !== (auth.user?.displayName ?? ''))
const emailChanged = computed(() => profile.email.trim() !== (auth.user?.email ?? ''))

const profileError = computed(() => {
  if (nameChanged.value && !profile.displayName.trim()) return 'Имя нельзя оставить пустым'
  if (emailChanged.value && !profile.email.trim()) return 'Почту нельзя удалить, только заменить'
  return ''
})

/** Черновик переключателей: на сервер уходит только по кнопке «Сохранить». */
const draft = reactive<UserSettings>({ notificationsEnabled: false, acceptCalls: false })
const isSaving = ref(false)
const saveError = ref('')
const justSaved = ref(false)
let savedTimer: ReturnType<typeof setTimeout> | undefined

onMounted(() => {
  load().catch(() => {})
})

onBeforeUnmount(() => {
  clearTimeout(savedTimer)
  clearTimeout(passwordSavedTimer)
})

watch(
  () => settingsStore.data,
  (data) => {
    if (data) Object.assign(draft, data)
  },
  { immediate: true },
)

const displayName = computed(() => auth.user?.displayName ?? auth.user?.username ?? '')
const initials = computed(() => (displayName.value ? toInitials(displayName.value) : ''))

const registeredAt = computed(() => {
  if (!auth.user) return ''
  return new Date(auth.user.createdAt).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
})

const settingsDirty = computed(() => {
  const saved = settingsStore.data
  if (!saved) return false
  return (
    draft.notificationsEnabled !== saved.notificationsEnabled ||
    draft.acceptCalls !== saved.acceptCalls
  )
})

const isDirty = computed(() => settingsDirty.value || nameChanged.value || emailChanged.value)

async function onSave() {
  if (!isDirty.value || isSaving.value || profileError.value) return

  isSaving.value = true
  saveError.value = ''
  try {
    if (nameChanged.value || emailChanged.value) {
      await updateProfile({
        displayName: nameChanged.value ? profile.displayName.trim() : undefined,
        email: emailChanged.value ? profile.email.trim() : undefined,
      })
    }

    const saved = settingsStore.data
    if (saved && settingsDirty.value) {
      // Отправляем только то, что реально поменяли.
      await update({
        notificationsEnabled:
          draft.notificationsEnabled !== saved.notificationsEnabled
            ? draft.notificationsEnabled
            : undefined,
        acceptCalls: draft.acceptCalls !== saved.acceptCalls ? draft.acceptCalls : undefined,
      })
    }
    justSaved.value = true
    clearTimeout(savedTimer)
    savedTimer = setTimeout(() => (justSaved.value = false), 2000)
  } catch (e) {
    const status = (e as { status?: number }).status
    if (status === 409) saveError.value = 'Эта почта уже занята другим аккаунтом'
    else if (status === 422) saveError.value = 'Проверьте почту — адрес выглядит некорректно'
    else saveError.value = extractApiErrorMessage(e, 'Не удалось сохранить настройки')
  } finally {
    isSaving.value = false
  }
}

/** Отдельный флоу от «Сохранить» выше: своя валидация, своя кнопка, никак
 * не завязан на остальной черновик формы. */
const passwordDraft = reactive({ newPassword: '', confirmPassword: '' })
const isPasswordBusy = ref(false)
const passwordError = ref('')
const passwordSaved = ref(false)
let passwordSavedTimer: ReturnType<typeof setTimeout> | undefined

const passwordFieldsFilled = computed(
  () => passwordDraft.newPassword.length > 0 || passwordDraft.confirmPassword.length > 0,
)

async function onResetPassword() {
  passwordError.value = ''

  if (passwordDraft.newPassword.length < 8) {
    passwordError.value = 'Пароль должен быть не короче 8 символов'
    return
  }
  if (passwordDraft.newPassword !== passwordDraft.confirmPassword) {
    passwordError.value = 'Пароли не совпадают'
    return
  }

  isPasswordBusy.value = true
  try {
    await resetPassword(passwordDraft.newPassword)
    passwordDraft.newPassword = ''
    passwordDraft.confirmPassword = ''
    passwordSaved.value = true
    clearTimeout(passwordSavedTimer)
    passwordSavedTimer = setTimeout(() => (passwordSaved.value = false), 2000)
  } catch (e) {
    passwordError.value = extractApiErrorMessage(e, 'Не удалось сменить пароль')
  } finally {
    isPasswordBusy.value = false
  }
}

function close() {
  navigateTo('/')
}

function onBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) close()
}

async function onLogout() {
  logout()
  await navigateTo('/login')
}
</script>

<template>
  <div class="settings-modal" @click="onBackdropClick">
    <div class="settings-modal__panel">
      <aside class="settings-nav">
        <div class="settings-nav__head">
          <span class="settings-nav__title">Настройки</span>
        </div>

        <nav class="settings-nav__list">
          <button type="button" class="settings-nav__item is-active" aria-current="page">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <circle cx="12" cy="10" r="3" />
              <path d="M6.2 18.4a7 7 0 0 1 11.6 0" />
            </svg>
            Профиль
          </button>
        </nav>

        <p class="settings-nav__footer">Телемакс Web</p>
      </aside>

      <section class="settings-main">
        <header class="settings-main__head">
          <h2 class="settings-main__title">Профиль</h2>
          <button
            type="button"
            class="settings-main__close"
            aria-label="Закрыть настройки"
            @click="close"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 6 6 18" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div class="settings-main__body">
          <div class="profile-card">
            <button
              type="button"
              class="profile-card__avatar"
              :class="{ 'is-busy': isAvatarBusy }"
              aria-label="Сменить фото профиля"
              @click="pickAvatar"
            >
              <UserAvatar :url="auth.user?.avatarUrl" :initials="initials" />
              <span class="profile-card__camera" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
                  <circle cx="12" cy="13" r="3.5" />
                </svg>
              </span>
            </button>
            <input
              ref="avatarInput"
              class="profile-card__file"
              type="file"
              :accept="AVATAR_TYPES.join(',')"
              @change="onAvatarChosen"
            />

            <span class="profile-card__text">
              <span class="profile-card__name">{{ displayName }}</span>
              <span class="profile-card__meta">
                @{{ auth.user?.username }}
                <template v-if="registeredAt"> · на Телемаксе с {{ registeredAt }}</template>
              </span>
              <span class="profile-card__actions">
                <button
                  type="button"
                  class="profile-card__link"
                  :disabled="isAvatarBusy"
                  @click="pickAvatar"
                >
                  {{ isAvatarBusy ? 'Загружаем…' : auth.user?.avatarUrl ? 'Сменить фото' : 'Загрузить фото' }}
                </button>
                <button
                  v-if="auth.user?.avatarUrl"
                  type="button"
                  class="profile-card__link is-danger"
                  :disabled="isAvatarBusy"
                  @click="onAvatarRemove"
                >
                  Удалить фото
                </button>
              </span>
            </span>
          </div>

          <p v-if="avatarError" class="settings-note is-error">{{ avatarError }}</p>

          <div class="fields">
            <label class="field">
              <span class="field__label">Отображаемое имя</span>
              <span class="field__control is-editable">
                <input
                  v-model="profile.displayName"
                  class="field__input"
                  type="text"
                  maxlength="64"
                  :placeholder="auth.user?.username"
                  :disabled="isSaving"
                />
              </span>
            </label>

            <label class="field">
              <span class="field__label">Имя пользователя</span>
              <span class="field__control">
                <span class="field__prefix">@</span>
                <input
                  class="field__input"
                  type="text"
                  :value="auth.user?.username"
                  readonly
                  aria-readonly="true"
                />
              </span>
            </label>

            <label class="field field--wide">
              <span class="field__label">Электронная почта</span>
              <span class="field__control is-editable">
                <input
                  v-model="profile.email"
                  class="field__input"
                  type="email"
                  maxlength="255"
                  placeholder="Не указана"
                  autocomplete="email"
                  :disabled="isSaving"
                />
              </span>
            </label>
          </div>

          <p v-if="profileError" class="settings-note is-error">{{ profileError }}</p>

          <h3 class="settings-section">Уведомления</h3>

          <p v-if="settingsStore.status === 'error'" class="settings-note is-error">
            Не удалось загрузить настройки. Попробуйте открыть настройки ещё раз.
          </p>

          <div v-else-if="settingsStore.data" class="toggles">
            <SettingsToggle
              v-model="draft.notificationsEnabled"
              label="Уведомления"
              hint="Показывать уведомления о новых сообщениях"
              :disabled="isSaving"
            />
            <SettingsToggle
              v-model="draft.acceptCalls"
              label="Звонки на этом устройстве"
              hint="Принимать входящие звонки здесь"
              :disabled="isSaving"
            />
          </div>

          <p v-else class="settings-note">Загрузка…</p>

          <h3 class="settings-section">Пароль</h3>

          <div class="fields">
            <label class="field">
              <span class="field__label">Новый пароль</span>
              <span class="field__control is-editable">
                <input
                  v-model="passwordDraft.newPassword"
                  class="field__input"
                  type="password"
                  minlength="8"
                  maxlength="256"
                  autocomplete="new-password"
                  placeholder="Не короче 8 символов"
                  :disabled="isPasswordBusy"
                />
              </span>
            </label>

            <label class="field">
              <span class="field__label">Повтор пароля</span>
              <span class="field__control is-editable">
                <input
                  v-model="passwordDraft.confirmPassword"
                  class="field__input"
                  type="password"
                  minlength="8"
                  maxlength="256"
                  autocomplete="new-password"
                  :disabled="isPasswordBusy"
                />
              </span>
            </label>
          </div>

          <div class="password-actions">
            <button
              type="button"
              class="save__button"
              :disabled="!passwordFieldsFilled || isPasswordBusy"
              @click="onResetPassword"
            >
              {{ isPasswordBusy ? 'Меняем…' : 'Сменить пароль' }}
            </button>
            <span v-if="passwordError" class="save__status is-error">{{ passwordError }}</span>
            <span v-else-if="passwordSaved" class="save__status">Пароль изменён</span>
          </div>
        </div>

        <footer class="settings-main__footer">
          <div class="save">
            <button
              type="button"
              class="save__button"
              :disabled="!isDirty || isSaving || !!profileError"
              @click="onSave"
            >
              {{ isSaving ? 'Сохраняем…' : 'Сохранить' }}
            </button>
            <span v-if="saveError" class="save__status is-error">{{ saveError }}</span>
            <span v-else-if="justSaved" class="save__status">Сохранено</span>
          </div>

          <button type="button" class="logout" @click="onLogout">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M9 4H5v16h4" />
              <path d="M14 8l4 4-4 4" />
              <path d="M18 12H9" />
            </svg>
            Выйти из аккаунта
          </button>
        </footer>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-modal {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(7, 11, 28, 0.6);
  transition: opacity 0.18s ease-out;
  /* Тонкие производные от --color-line / --color-accent — без новых цветов. */
  --settings-line: rgba(61, 79, 156, 0.6);
  --settings-accent-soft: rgba(255, 204, 46, 0.45);
}

.settings-modal__panel {
  display: flex;
  width: min(80vw, 1100px);
  height: min(90vh, 760px);
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  box-shadow: var(--shadow-hard);
  transition:
    opacity 0.18s ease-out,
    transform 0.18s ease-out;
}

.settings-modal-enter-from,
.settings-modal-leave-to {
  opacity: 0;
}

.settings-modal-enter-from .settings-modal__panel,
.settings-modal-leave-to .settings-modal__panel {
  opacity: 0;
  transform: scale(0.96) translateY(8px);
}

.settings-modal-leave-active {
  transition-duration: 0.14s;
}

.settings-modal-leave-active .settings-modal__panel {
  transition-duration: 0.14s;
}


/* ── Левая колонка ── */

.settings-nav {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex: none;
  background: var(--color-lift);
  border-right: 1px solid var(--settings-line);
}

.settings-nav__head {
  display: flex;
  align-items: center;
  height: 72px;
  flex: none;
  padding: 0 22px;
  border-bottom: 2px solid var(--color-accent);
}

.settings-nav__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-accent);
}

.settings-nav__list {
  flex: 1;
  padding: 12px 10px;
}

.settings-nav__item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  background: none;
  border: none;
  border-left: 2px solid transparent;
  border-radius: var(--radius);
  font-family: var(--font-heading);
  font-size: 15px;
  color: var(--color-text-muted);
  text-align: left;
  cursor: pointer;
}

.settings-nav__item.is-active {
  background: var(--color-surface);
  border-left-color: var(--color-accent);
  font-weight: 600;
  color: var(--color-text);
}

.settings-nav__item svg {
  width: 20px;
  height: 20px;
  flex: none;
}

.settings-nav__footer {
  margin: 0;
  padding: 14px 22px;
  border-top: 1px solid var(--settings-line);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}


/* ── Правая колонка ── */

.settings-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.settings-main__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
  flex: none;
  padding: 0 28px;
  border-bottom: 1px solid var(--settings-line);
}

.settings-main__title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 22px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.settings-main__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 0.15s ease;
}

.settings-main__close:hover {
  color: var(--color-accent);
}

.settings-main__close svg {
  width: 20px;
  height: 20px;
}

.settings-main__body {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 22px;
  background: var(--color-lift);
  border: 1px solid var(--settings-line);
}

.profile-card__avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  flex: none;
  padding: 0;
  background: var(--color-surface);
  border: 1px solid var(--settings-accent-soft);
  border-radius: var(--radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 24px;
  color: var(--color-accent);
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.profile-card__avatar:hover {
  border-color: var(--color-accent);
}

.profile-card__avatar.is-busy {
  opacity: 0.6;
  cursor: wait;
}

.profile-card__camera {
  position: absolute;
  right: -6px;
  bottom: -6px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-accent);
  border: 2px solid var(--color-lift);
  color: var(--color-ink);
}

.profile-card__camera svg {
  width: 15px;
  height: 15px;
}

.profile-card__file {
  display: none;
}

.profile-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 4px;
}

.profile-card__link {
  padding: 0;
  background: none;
  border: none;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-accent);
  cursor: pointer;
}

.profile-card__link:hover:not(:disabled) {
  color: var(--color-accent-hover);
}

.profile-card__link.is-danger {
  color: var(--color-error);
}

.profile-card__link:disabled {
  opacity: 0.6;
  cursor: wait;
}

.profile-card__text {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.profile-card__name {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 22px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-card__meta {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 22px;
  margin-top: 28px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.field--wide {
  grid-column: 1 / -1;
}

.field__label,
.settings-section {
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
  background: var(--color-ground);
  border: 1px solid var(--settings-line);
  border-radius: var(--radius);
}

.field__control.is-editable:focus-within {
  border-color: var(--color-focus);
}

.field__input::placeholder {
  color: var(--color-text-dim);
}

.field__prefix {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--color-text-dim);
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

.settings-section {
  margin: 32px 0 4px;
}

.password-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 20px;
}

.toggles > :deep(.toggle-row) {
  border-bottom: 1px solid var(--settings-line);
}

.settings-note {
  margin: 12px 0 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.settings-note.is-error {
  color: var(--color-error);
}

.settings-main__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  flex: none;
  padding: 20px 28px;
  border-top: 1px solid var(--settings-line);
}

.save {
  display: flex;
  align-items: center;
  gap: 14px;
}

.save__button {
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

.save__button:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.save__button:active:not(:disabled) {
  background: var(--color-accent-pressed);
}

.save__button:disabled {
  opacity: 0.5;
  box-shadow: none;
  cursor: not-allowed;
}

.save__status {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-success);
}

.save__status.is-error {
  color: var(--color-error);
}

.logout {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  background: none;
  border: 1px solid var(--color-error);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-error);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.logout:hover {
  background: var(--color-error);
  color: var(--color-ink);
}

.logout svg {
  width: 18px;
  height: 18px;
}


/* ── Узкие экраны: навигация сверху, панель на весь экран ── */

@media (max-width: 900px) {
  .settings-modal {
    padding: 0;
  }

  .settings-modal__panel {
    flex-direction: column;
    width: 100vw;
    height: 100vh;
  }

  .settings-nav {
    width: 100%;
    border-right: none;
  }

  .settings-nav__head {
    height: 56px;
  }

  .settings-nav__list {
    display: flex;
    padding: 8px;
  }

  .settings-nav__footer {
    display: none;
  }

  .settings-main__body,
  .settings-main__footer {
    padding-inline: 18px;
  }

  .fields {
    grid-template-columns: 1fr;
  }
}
</style>
