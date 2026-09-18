<script setup lang="ts">
function close() {
  navigateTo('/')
}

function onBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) close()
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

      <div class="settings-modal__body" />
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
  background: var(--color-ground);
}
</style>
