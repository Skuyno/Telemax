<script setup lang="ts">
const props = defineProps<{ url: string; title: string }>()

const emit = defineEmits<{ close: [] }>()

const src = useAvatarSrc(() => props.url)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      class="viewer"
      role="dialog"
      aria-modal="true"
      :aria-label="`Фото: ${title}`"
      @click.self="emit('close')"
    >
      <figure class="viewer__frame">
        <img v-if="src" class="viewer__img" :src="src" :alt="title" />
        <span v-else class="viewer__loading" aria-label="Загружаем фото" />
        <figcaption class="viewer__title">{{ title }}</figcaption>
      </figure>

      <div class="viewer__bar">
        <a
          v-if="src"
          class="viewer__btn"
          :href="src"
          :download="title"
          aria-label="Скачать"
          title="Скачать"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 4v11" />
            <path d="M7.5 11.5 12 16l4.5-4.5" />
            <path d="M5 19h14" />
          </svg>
        </a>
        <button type="button" class="viewer__btn" aria-label="Закрыть" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M18 6 6 18" />
            <path d="M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.viewer {
  position: fixed;
  inset: 0;
  z-index: 250;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 24px 24px;
  background: rgba(7, 11, 28, 0.88);
  cursor: zoom-out;
}

.viewer__frame {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  max-width: 100%;
  max-height: 100%;
  margin: 0;
  cursor: default;
}

.viewer__img {
  display: block;
  max-width: min(560px, 100%);
  max-height: calc(100dvh - 140px);
  object-fit: contain;
  border-radius: 18px;
  box-shadow: var(--shadow-hard);
}

.viewer__loading {
  display: block;
  width: min(360px, 80vw);
  aspect-ratio: 1;
  border-radius: 18px;
  background: linear-gradient(
    90deg,
    rgba(230, 236, 255, 0.07) 25%,
    rgba(230, 236, 255, 0.16) 50%,
    rgba(230, 236, 255, 0.07) 75%
  );
  background-size: 300% 100%;
  animation: avatar-shimmer 1.3s ease-in-out infinite;
}

.viewer__title {
  max-width: 100%;
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 15px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewer__bar {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
}

.viewer__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  padding: 0;
  background: rgba(22, 34, 90, 0.85);
  border: 1px solid rgba(61, 79, 156, 0.75);
  border-radius: 999px;
  color: var(--color-text);
  cursor: pointer;
}

.viewer__btn:hover {
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.viewer__btn svg {
  width: 18px;
  height: 18px;
}

@keyframes avatar-shimmer {
  from {
    background-position: 150% 0;
  }

  to {
    background-position: -150% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .viewer__loading {
    animation: none;
  }
}
</style>
