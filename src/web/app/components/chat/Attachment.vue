<script setup lang="ts">
import type { Attachment } from '~/types/chat'

const props = defineProps<{ fileId: string; own: boolean }>()

const { getAttachmentInfo, refreshStreamUrl } = useFiles()

const attachment = ref<Attachment | null>(null)
const failed = ref(false)

watch(
  () => props.fileId,
  async (id) => {
    attachment.value = null
    failed.value = false
    const loaded = await getAttachmentInfo(id)
    if (props.fileId !== id) return
    attachment.value = loaded
    failed.value = !loaded
  },
  { immediate: true },
)

const duration = ref('')

function onMetadata(event: Event) {
  const seconds = (event.target as HTMLVideoElement).duration
  if (!Number.isFinite(seconds)) return

  const total = Math.round(seconds)
  const minutes = Math.floor(total / 60)
  duration.value = `${minutes}:${String(total % 60).padStart(2, '0')}`
}

async function onSourceError() {
  const current = attachment.value
  if (!current || current.url.startsWith('blob:')) return

  const url = await refreshStreamUrl(props.fileId).catch(() => '')
  if (url && attachment.value) attachment.value = { ...attachment.value, url }
}

const isImage = computed(() => attachment.value?.type.startsWith('image/') ?? false)
const isVideo = computed(() => attachment.value?.type.startsWith('video/') ?? false)

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
    <img
      class="media__img"
      :src="attachment.url"
      :alt="attachment.name"
      @error="onSourceError"
    />
  </button>

  <button
    v-else-if="attachment && isVideo"
    type="button"
    class="media media--video"
    aria-label="Смотреть видео"
    @click="viewerOpen = true"
  >
    <video
      class="media__video"
      :src="attachment.url"
      preload="metadata"
      muted
      playsinline
      @loadedmetadata="onMetadata"
      @error="onSourceError"
    />
    <span class="media__play" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M8 5.5v13l11-6.5z" />
      </svg>
    </span>
    <span v-if="duration" class="media__badge">{{ duration }}</span>
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
      <span v-if="attachment.size" class="file__size">{{ formatSize(attachment.size) }}</span>
    </span>
  </a>

  <span v-else-if="failed" class="file is-broken" :class="{ 'is-own': own }">
    Файл недоступен
  </span>

  <span v-else class="loading" :class="{ 'is-own': own }" aria-label="Загружаем файл" />

  <Teleport to="body">
    <Transition name="viewer">
      <div
        v-if="viewerOpen && attachment"
        class="viewer"
        role="dialog"
        :aria-label="isVideo ? 'Просмотр видео' : 'Просмотр картинки'"
        @click.self="viewerOpen = false"
      >
        <ChatVideoPlayer
          v-if="isVideo"
          :src="attachment.url"
          :title="attachment.name === 'Файл' ? undefined : attachment.name"
          @error="onSourceError"
        />
        <img v-else class="viewer__img" :src="attachment.url" :alt="attachment.name" />
        <div class="viewer__bar">
          <a
            class="viewer__btn"
            :href="attachment.url"
            :download="attachment.name"
            aria-label="Скачать"
            title="Скачать"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 4v11" />
              <path d="M7.5 11.5 12 16l4.5-4.5" />
              <path d="M5 19h14" />
            </svg>
          </a>
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
  max-width: 300px;
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

.viewer__img,
.viewer__video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 10px;
  box-shadow: var(--shadow-hard);
  cursor: default;
}

.viewer__video {
  width: min(1080px, 100%);
  background: var(--color-ink);
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

.media--video {
  position: relative;
  width: 300px;
  background: var(--color-ink);
}

.media__video {
  display: block;
  width: 100%;
  height: 180px;
  object-fit: cover;
  pointer-events: none;
}

.media__play {
  position: absolute;
  top: 50%;
  left: 50%;
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  background: rgba(255, 204, 46, 0.92);
  border-radius: 50%;
  box-shadow: 0 0 24px rgba(7, 11, 28, 0.55);
  color: var(--color-ink);
  transform: translate(-50%, -50%);
  transition: transform 0.15s ease;
}

.media--video:hover .media__play {
  transform: translate(-50%, -50%) scale(1.08);
}

.media__play svg {
  width: 26px;
  height: 26px;
}

.media__badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  padding: 3px 8px;
  background: rgba(7, 11, 28, 0.72);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text);
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

.loading {
  display: block;
  width: 300px;
  height: 180px;
  border-radius: var(--chat-radius);
  background: linear-gradient(
    90deg,
    rgba(230, 236, 255, 0.07) 25%,
    rgba(230, 236, 255, 0.16) 50%,
    rgba(230, 236, 255, 0.07) 75%
  );
  background-size: 300% 100%;
  animation: attachment-shimmer 1.3s ease-in-out infinite;
}

.loading.is-own {
  background: linear-gradient(
    90deg,
    rgba(11, 18, 54, 0.1) 25%,
    rgba(11, 18, 54, 0.22) 50%,
    rgba(11, 18, 54, 0.1) 75%
  );
  background-size: 300% 100%;
}

@keyframes attachment-shimmer {
  from {
    background-position: 150% 0;
  }

  to {
    background-position: -150% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading {
    animation: none;
  }
}

.file.is-broken {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

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
