<script setup lang="ts">
import type { PinScope } from '~/types/chat'

const props = defineProps<{ mode: 'pin' | 'unpin' | null; busy?: boolean }>()

const emit = defineEmits<{ choose: [PinScope]; cancel: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('cancel')
}

watch(
  () => props.mode,
  (mode) => {
    if (mode) window.addEventListener('keydown', onKeydown)
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
        v-if="mode"
        class="confirm"
        role="dialog"
        aria-modal="true"
        :aria-label="mode === 'pin' ? 'Закрепление сообщения' : 'Открепление сообщения'"
        @click.self="emit('cancel')"
      >
        <div class="confirm__card">
          <h2 class="confirm__title">
            {{ mode === 'pin' ? 'Закрепить сообщение?' : 'Открепить сообщение?' }}
          </h2>
          <p v-if="mode === 'pin'" class="confirm__text">
            Для всех — сообщение появится сверху переписки у каждого участника. Для себя — увидите
            только вы.
          </p>
          <p v-else class="confirm__text">
            Для всех — сообщение пропадёт из закреплённых у каждого участника. Для себя — только у
            вас, остальные продолжат его видеть.
          </p>

          <div class="confirm__actions">
            <button type="button" class="confirm__btn" @click="emit('cancel')">Отмена</button>
            <button
              type="button"
              class="confirm__btn"
              :disabled="busy"
              @click="emit('choose', 'me')"
            >
              Для себя
            </button>
            <button
              type="button"
              class="confirm__btn is-primary"
              :disabled="busy"
              @click="emit('choose', 'everyone')"
            >
              Для всех
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
  max-width: 420px;
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
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 26px;
}

.confirm__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 46px;
  padding: 0 20px;
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
    border-color 0.15s ease;
}

.confirm__btn:hover:not(:disabled) {
  background: var(--color-surface);
  border-color: var(--color-line);
}

.confirm__btn.is-primary {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-ink);
}

.confirm__btn.is-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
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
  .confirm-enter-active .confirm__card {
    animation: none;
  }
}
</style>
