<script setup lang="ts">
const props = defineProps<{ open: boolean; busy?: boolean }>()

const emit = defineEmits<{ confirm: []; cancel: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('cancel')
}

watch(
  () => props.open,
  (open) => {
    if (open) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  },
  { immediate: true },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div
        v-if="open"
        class="confirm"
        role="dialog"
        aria-modal="true"
        aria-label="Удаление сообщения"
        @click.self="emit('cancel')"
      >
        <div class="confirm__card">
          <h2 class="confirm__title">Удалить сообщение?</h2>
          <p class="confirm__text">Оно пропадёт у всех участников чата. Вернуть его не выйдет.</p>

          <div class="confirm__actions">
            <button type="button" class="confirm__btn" @click="emit('cancel')">Отмена</button>
            <button
              type="button"
              class="confirm__btn is-danger"
              :disabled="busy"
              @click="emit('confirm')"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M4 7h16" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
                <path d="M6 7l1 13h10l1-13" />
                <path d="M9 7V4h6v3" />
              </svg>
              {{ busy ? 'Удаляем…' : 'Удалить' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(7, 11, 28, 0.88);
}

.confirm__card {
  width: 100%;
  max-width: 400px;
  padding: 26px 26px 22px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 18px;
  box-shadow: var(--shadow-hard);
}

.confirm__title {
  margin: 0 0 10px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 18px;
  color: var(--color-text);
}

.confirm__text {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.confirm__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 26px;
}

.confirm__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 46px;
  padding: 0 22px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: 14px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.confirm__btn:hover:not(:disabled) {
  background: var(--color-surface);
  border-color: var(--color-line);
}

.confirm__btn.is-danger {
  background: var(--color-error);
  border-color: var(--color-error);
  color: var(--color-ink);
}

.confirm__btn.is-danger:hover:not(:disabled) {
  background: rgba(255, 107, 94, 0.85);
  border-color: rgba(255, 107, 94, 0.85);
}

.confirm__btn svg {
  width: 17px;
  height: 17px;
  flex: none;
}

.confirm__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.confirm-enter-active {
  transition: opacity 0.18s ease;
}

.confirm-leave-active {
  transition: opacity 0.15s ease;
}

.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}

.confirm-enter-active .confirm__card {
  animation: confirm-pop 0.22s cubic-bezier(0.2, 0.9, 0.3, 1.2);
}

.confirm-leave-active .confirm__card {
  transition:
    transform 0.15s ease,
    opacity 0.15s ease;
}

.confirm-leave-to .confirm__card {
  opacity: 0;
  transform: scale(0.96);
}

@keyframes confirm-pop {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(12px);
  }

  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .confirm-enter-active .confirm__card,
  .confirm-leave-active .confirm__card {
    animation: none;
    transition: none;
  }
}
</style>
