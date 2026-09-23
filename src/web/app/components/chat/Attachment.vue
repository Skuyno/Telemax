<script setup lang="ts">
import type { Attachment } from '~/types/chat'

const props = defineProps<{ fileId: string; own: boolean }>()

const { getAttachment } = useFiles()

const attachment = ref<Attachment | null>(null)
const failed = ref(false)

watch(
  () => props.fileId,
  async (id) => {
    attachment.value = null
    failed.value = false
    const loaded = await getAttachment(id)
    if (props.fileId !== id) return
    attachment.value = loaded
    failed.value = !loaded
  },
  { immediate: true },
)

const isImage = computed(() => attachment.value?.type.startsWith('image/') ?? false)

const viewerOpen = ref(false)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') viewerOpen.value = false
}

watch(viewerOpen, (open) => {
  if (open) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}
</script>

<template>
  <button
    v-if="attachment && isImage"
    type="button"
    class="media"
    aria-label="Открыть картинку"
    @click="viewerOpen = true"
  >
    <img class="media__img" :src="attachment.url" :alt="attachment.name" />
  </button>

  <a
    v-else-if="attachment"
    class="file"
    :class="{ 'is-own': own }"
    :href="attachment.url"
    :download="attachment.name"
  >
    <span class="file__icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 3H6v18h12V7z" />
        <path d="M14 3v4h4" />
      </svg>
    </span>
    <span class="file__text">
      <span class="file__name">{{ attachment.name }}</span>
      <span class="file__size">{{ formatSize(attachment.size) }}</span>
    </span>
  </a>

  <span v-else-if="failed" class="file is-broken" :class="{ 'is-own': own }">
    Файл недоступен
  </span>

  <span v-else class="file is-loading" :class="{ 'is-own': own }">Загружаем файл…</span>

  <Teleport to="body">
    <Transition name="viewer">
      <div
        v-if="viewerOpen && attachment"
        class="viewer"
        role="dialog"
        aria-label="Просмотр картинки"
        @click.self="viewerOpen = false"
      >
        <img class="viewer__img" :src="attachment.url" :alt="attachment.name" />
        <div class="viewer__bar">
          <a class="viewer__btn" :href="attachment.url" :download="attachment.name">Скачать</a>
          <button
            type="button"
            class="viewer__btn"
            aria-label="Закрыть"
            @click="viewerOpen = false"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 6 6 18" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.media {
  display: block;
  max-width: 280px;
  padding: 0;
  overflow: hidden;
  background: none;
  border: none;
  border-radius: var(--chat-radius);
  cursor: zoom-in;
}

.viewer {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 24px 24px;
  background: rgba(7, 11, 28, 0.88);
  cursor: zoom-out;
}

.viewer__img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: var(--shadow-hard);
  cursor: default;
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
  min-width: 40px;
  height: 40px;
  padding: 0 14px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
  text-decoration: none;
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

.viewer-enter-active,
.viewer-leave-active {
  transition: opacity 0.15s ease;
}

.viewer-enter-from,
.viewer-leave-to {
  opacity: 0;
}

.media__img {
  display: block;
  width: 100%;
  max-height: 320px;
  object-fit: cover;
}

.file {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 200px;
  max-width: 280px;
  padding: 8px 10px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius);
  color: var(--color-text);
  text-decoration: none;
}

.file.is-own {
  background: rgba(11, 18, 54, 0.12);
  border-color: rgba(11, 18, 54, 0.25);
  color: var(--color-ink);
}

.file.is-loading,
.file.is-broken {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.file.is-own.is-loading,
.file.is-own.is-broken {
  color: var(--color-ink);
  opacity: 0.7;
}

.file__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex: none;
  background: var(--color-surface);
  border-radius: var(--chat-radius);
  color: var(--color-accent);
}

.file.is-own .file__icon {
  background: var(--color-ink);
}

.file__icon svg {
  width: 18px;
  height: 18px;
}

.file__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.file__name {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file__size {
  font-family: var(--font-mono);
  font-size: 10px;
  opacity: 0.7;
}
</style>
