<script setup lang="ts">
const props = defineProps<{ src: string; title?: string }>()

const emit = defineEmits<{ error: [] }>()

const video = ref<HTMLVideoElement | null>(null)
const root = ref<HTMLElement | null>(null)

const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const buffered = ref(0)
const volume = ref(1)
const isMuted = ref(false)
const isFullscreen = ref(false)

const progress = computed(() => (duration.value ? (currentTime.value / duration.value) * 100 : 0))
const bufferedPercent = computed(() =>
  duration.value ? (buffered.value / duration.value) * 100 : 0,
)

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return '0:00'
  const total = Math.floor(seconds)
  const minutes = Math.floor(total / 60)
  return `${minutes}:${String(total % 60).padStart(2, '0')}`
}

function toggle() {
  const element = video.value
  if (!element) return
  if (element.paused) element.play()
  else element.pause()
}

function onTimeUpdate() {
  const element = video.value
  if (!element) return
  currentTime.value = element.currentTime
  if (element.buffered.length) {
    buffered.value = element.buffered.end(element.buffered.length - 1)
  }
}

function onLoadedMetadata() {
  duration.value = video.value?.duration ?? 0
}

function seek(event: Event) {
  const element = video.value
  if (!element) return
  element.currentTime = (Number((event.target as HTMLInputElement).value) / 100) * duration.value
}

function changeVolume(event: Event) {
  const element = video.value
  if (!element) return
  volume.value = Number((event.target as HTMLInputElement).value)
  element.volume = volume.value
  element.muted = volume.value === 0
  isMuted.value = element.muted
}

function toggleMute() {
  const element = video.value
  if (!element) return
  element.muted = !element.muted
  isMuted.value = element.muted
}

function skip(seconds: number) {
  const element = video.value
  if (!element) return
  element.currentTime = Math.min(Math.max(element.currentTime + seconds, 0), duration.value)
}

async function toggleFullscreen() {
  if (document.fullscreenElement) await document.exitFullscreen()
  else await root.value?.requestFullscreen()
}

function onFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === ' ' || event.key === 'k') {
    event.preventDefault()
    toggle()
  } else if (event.key === 'ArrowRight') {
    skip(5)
  } else if (event.key === 'ArrowLeft') {
    skip(-5)
  } else if (event.key === 'm') {
    toggleMute()
  }
}

watch(
  () => props.src,
  () => {
    currentTime.value = 0
    duration.value = 0
    buffered.value = 0
  },
)

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div ref="root" class="player" :class="{ 'is-fullscreen': isFullscreen, 'is-playing': isPlaying }">
    <video
      ref="video"
      class="player__video"
      :src="src"
      autoplay
      playsinline
      @click="toggle"
      @play="isPlaying = true"
      @pause="isPlaying = false"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @progress="onTimeUpdate"
      @error="emit('error')"
    />

    <button
      v-if="!isPlaying"
      type="button"
      class="player__big"
      aria-label="Воспроизвести"
      @click="toggle"
    >
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M8 5.5v13l11-6.5z" />
      </svg>
    </button>

    <div class="bar">
      <input
        class="bar__seek"
        type="range"
        min="0"
        max="100"
        step="0.1"
        :value="progress"
        :style="{ '--played': `${progress}%`, '--loaded': `${bufferedPercent}%` }"
        aria-label="Перемотка"
        @input="seek"
      />

      <div class="bar__row">
        <button
          type="button"
          class="bar__btn"
          :aria-label="isPlaying ? 'Пауза' : 'Воспроизвести'"
          @click="toggle"
        >
          <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M8 5.5v13l11-6.5z" />
          </svg>
        </button>

        <span class="bar__time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>

        <span class="bar__volume">
          <button
            type="button"
            class="bar__btn"
            :aria-label="isMuted ? 'Включить звук' : 'Выключить звук'"
            @click="toggleMute"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M5 9v6h3.5L13 19V5L8.5 9z" />
              <template v-if="isMuted">
                <path d="M17 9.5l4 5" />
                <path d="M21 9.5l-4 5" />
              </template>
              <template v-else>
                <path d="M16.5 9.5a3.5 3.5 0 0 1 0 5" />
                <path d="M19 7a7 7 0 0 1 0 10" />
              </template>
            </svg>
          </button>
          <input
            class="bar__volume-range"
            type="range"
            min="0"
            max="1"
            step="0.05"
            :value="isMuted ? 0 : volume"
            :style="{ '--played': `${(isMuted ? 0 : volume) * 100}%` }"
            aria-label="Громкость"
            @input="changeVolume"
          />
        </span>

        <span class="bar__spacer" />

        <span v-if="title" class="bar__title">{{ title }}</span>

        <button
          type="button"
          class="bar__btn"
          :aria-label="isFullscreen ? 'Выйти из полноэкранного режима' : 'Во весь экран'"
          @click="toggleFullscreen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <template v-if="isFullscreen">
              <path d="M9 4v5H4" />
              <path d="M15 4v5h5" />
              <path d="M9 20v-5H4" />
              <path d="M15 20v-5h5" />
            </template>
            <template v-else>
              <path d="M4 9V4h5" />
              <path d="M20 9V4h-5" />
              <path d="M4 15v5h5" />
              <path d="M20 15v5h-5" />
            </template>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player {
  position: relative;
  display: flex;
  width: min(1080px, 100%);
  max-height: 100%;
  overflow: hidden;
  background: var(--color-ink);
  border: 1px solid rgba(255, 204, 46, 0.25);
  border-radius: 18px;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.55);
  cursor: default;
}

.player.is-fullscreen {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

.player__video {
  display: block;
  width: 100%;
  max-height: 80vh;
  object-fit: contain;
  cursor: pointer;
}

.player.is-fullscreen .player__video {
  max-height: 100vh;
}

.player__big {
  position: absolute;
  top: 50%;
  left: 50%;
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  background: rgba(255, 204, 46, 0.92);
  border: none;
  border-radius: 50%;
  box-shadow: 0 0 32px rgba(7, 11, 28, 0.6);
  color: var(--color-ink);
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition: transform 0.15s ease;
}

.player__big:hover {
  transform: translate(-50%, -50%) scale(1.07);
}

.player__big svg {
  width: 34px;
  height: 34px;
}

.bar {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 40px 18px 14px;
  background: linear-gradient(to top, rgba(7, 11, 28, 0.95), rgba(7, 11, 28, 0.55) 55%, transparent);
  opacity: 0;
  transform: translateY(8px);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.player:hover .bar,
.player:focus-within .bar,
.player:not(.is-playing) .bar {
  opacity: 1;
  transform: translateY(0);
}

.bar__row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar__btn {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: none;
  padding: 0;
  background: rgba(230, 236, 255, 0.08);
  border: none;
  border-radius: 12px;
  color: var(--color-text);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.bar__btn:hover {
  background: rgba(255, 204, 46, 0.18);
  color: var(--color-accent);
}

.bar__btn svg {
  width: 20px;
  height: 20px;
}

.bar__time {
  flex: none;
  padding: 5px 10px;
  background: rgba(230, 236, 255, 0.08);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
}

.bar__volume {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.bar__spacer {
  flex: 1;
}

.bar__title {
  max-width: 40%;
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar__seek,
.bar__volume-range {
  height: 16px;
  appearance: none;
  -webkit-appearance: none;
  background: none;
  cursor: pointer;
}

.bar__seek {
  width: 100%;
}

.bar__volume-range {
  width: 78px;
}

.bar__seek::-webkit-slider-runnable-track,
.bar__volume-range::-webkit-slider-runnable-track {
  height: 6px;
  background:
    linear-gradient(var(--color-accent), var(--color-accent)) 0 / var(--played, 0%) 100% no-repeat,
    linear-gradient(rgba(230, 236, 255, 0.35), rgba(230, 236, 255, 0.35)) 0 / var(--loaded, 0%) 100%
      no-repeat,
    rgba(230, 236, 255, 0.18);
  border-radius: 999px;
}

.bar__seek::-moz-range-track,
.bar__volume-range::-moz-range-track {
  height: 4px;
  background:
    linear-gradient(var(--color-accent), var(--color-accent)) 0 / var(--played, 0%) 100% no-repeat,
    rgba(230, 236, 255, 0.18);
  border-radius: 999px;
}

.bar__seek::-webkit-slider-thumb,
.bar__volume-range::-webkit-slider-thumb {
  width: 14px;
  height: 14px;
  margin-top: -4px;
  appearance: none;
  -webkit-appearance: none;
  background: var(--color-accent);
  border: none;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(255, 204, 46, 0.6);
}

.bar__seek::-moz-range-thumb,
.bar__volume-range::-moz-range-thumb {
  width: 12px;
  height: 12px;
  background: var(--color-accent);
  border: none;
  border-radius: 50%;
}

@media (max-width: 640px) {
  .bar__title,
  .bar__volume-range {
    display: none;
  }
}
</style>
