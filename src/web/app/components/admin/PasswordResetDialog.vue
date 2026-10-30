<script setup lang="ts">
const props = defineProps<{ open: boolean; busy?: boolean; username: string }>()

const emit = defineEmits<{ confirm: [password: string]; cancel: [] }>()

const password = ref('')
const isVisible = ref(false)

const canSubmit = computed(() => password.value.length >= 8 && !props.busy)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('cancel')
}

function onSubmit() {
  if (!canSubmit.value) return
  emit('confirm', password.value)
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
      password.value = ''
      isVisible.value = false
    }
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
        aria-label="Сброс пароля"
        @click.self="emit('cancel')"
      >
        <form class="confirm__card" @submit.prevent="onSubmit">
          <h2 class="confirm__title">Сбросить пароль @{{ username }}</h2>
          <p class="confirm__text">
            Пользователь будет разлогинен на всех устройствах и сможет войти только с новым
            паролем.
          </p>

          <label class="confirm__field">
            <span class="input">
              <input
                v-model="password"
                :type="isVisible ? 'text' : 'password'"
                minlength="8"
                maxlength="256"
                autocomplete="new-password"
                placeholder="Новый пароль, не короче 8 символов"
                autofocus
              />
              <button
                type="button"
                class="eye"
                :aria-label="isVisible ? 'Скрыть пароль' : 'Показать пароль'"
                @click="isVisible = !isVisible"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                  <path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6z" />
                  <circle cx="12" cy="12" r="3" />
                  <path v-if="isVisible" d="M4 20 20 4" />
                </svg>
              </button>
            </span>
          </label>

          <div class="confirm__actions">
            <button type="button" class="confirm__btn" @click="emit('cancel')">Отмена</button>
            <button type="submit" class="confirm__btn is-primary" :disabled="!canSubmit">
              {{ busy ? 'Сохраняем…' : 'Сбросить' }}
            </button>
          </div>
        </form>
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
  margin: 0 0 18px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.confirm__field {
  display: block;
}

.input {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  height: 48px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  border-radius: 12px;
}

.input input {
  flex: 1;
  min-width: 0;
  height: 100%;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.eye {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 28px;
  height: 28px;
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
}

.eye svg {
  width: 18px;
  height: 18px;
}

.confirm__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.confirm__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 46px;
  padding: 0 22px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
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

.confirm__btn.is-primary {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-ink);
}

.confirm__btn.is-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
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
