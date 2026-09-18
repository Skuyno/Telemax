<script setup lang="ts">
const auth = useAuthStore()
const settingsStore = useSettingsStore()
const { load, update } = useSettings()
const { logout } = useAuth()

const isSavingNotifications = ref(false)
const isSavingCalls = ref(false)

onMounted(() => {
  load().catch(() => {})
})

const registeredAt = computed(() => {
  if (!auth.user) return ''
  return new Date(auth.user.createdAt).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
})

async function onToggleNotifications(value: boolean) {
  isSavingNotifications.value = true
  try {
    await update({ notificationsEnabled: value })
  } finally {
    isSavingNotifications.value = false
  }
}

async function onToggleCalls(value: boolean) {
  isSavingCalls.value = true
  try {
    await update({ acceptCalls: value })
  } finally {
    isSavingCalls.value = false
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
      <header class="settings-modal__head">
        <span class="settings-modal__title">Настройки</span>
        <button
          type="button"
          class="settings-modal__close"
          aria-label="Закрыть настройки"
          @click="close"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="M6 6l12 12" />
          </svg>
        </button>
      </header>

      <div class="settings-modal__body">
        <section class="settings-section">
          <h3 class="settings-section__title">Профиль</h3>
          <div class="profile-card">
            <span class="profile-card__username">{{ auth.user?.username }}</span>
            <span v-if="registeredAt" class="profile-card__meta">
              На Telemax с {{ registeredAt }}
            </span>
          </div>
        </section>

        <section class="settings-section">
          <h3 class="settings-section__title">Уведомления</h3>

          <p v-if="settingsStore.status === 'error'" class="settings-error">
            Не удалось загрузить настройки. Попробуйте открыть настройки ещё раз.
          </p>

          <template v-else-if="settingsStore.data">
            <SettingsToggle
              :model-value="settingsStore.data.notificationsEnabled"
              label="Уведомления"
              hint="Показывать уведомления о новых сообщениях"
              :disabled="isSavingNotifications"
              @update:model-value="onToggleNotifications"
            />
            <SettingsToggle
              :model-value="settingsStore.data.acceptCalls"
              label="Звонки на этом устройстве"
              hint="Принимать входящие звонки здесь"
              :disabled="isSavingCalls"
              @update:model-value="onToggleCalls"
            />
          </template>

          <p v-else class="settings-loading">Загрузка…</p>
        </section>

        <section class="settings-section">
          <button type="button" class="logout-button" @click="onLogout">Выйти из аккаунта</button>
        </section>
      </div>
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
  background: rgba(7, 11, 28, 0.6);
}

.settings-modal__panel {
  display: flex;
  flex-direction: column;
  width: 80vw;
  height: 90vh;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  box-shadow: var(--shadow-hard);
}

.settings-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
  height: 60px;
  padding: 0 16px;
  border-bottom: 2px solid var(--color-accent);
}

.settings-modal__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-accent);
}

.settings-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 0.15s ease;
}

.settings-modal__close:hover {
  color: var(--color-accent);
}

.settings-modal__close svg {
  width: 18px;
  height: 18px;
}

.settings-modal__body {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  background: var(--color-ground);
}

.settings-section {
  max-width: 480px;
  margin: 0 auto 32px;
}

.settings-section__title {
  margin: 0 0 12px;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}

.settings-section > :deep(.toggle-row) + :deep(.toggle-row) {
  border-top: 1px solid var(--color-line);
}

.profile-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
}

.profile-card__username {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 16px;
  color: var(--color-text);
}

.profile-card__meta {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}

.settings-loading,
.settings-error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.settings-error {
  color: var(--color-error);
}

.logout-button {
  width: 100%;
  padding: 12px;
  background: none;
  border: 1px solid var(--color-error);
  color: var(--color-error);
  font-family: var(--font-mono);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.logout-button:hover {
  background: var(--color-error);
  color: var(--color-ink);
}
</style>
