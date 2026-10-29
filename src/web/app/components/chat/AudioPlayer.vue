<script lang="ts">
const playing = ref<HTMLAudioElement | null>(null)
const peaksCache = new Map<string, Promise<number[] | null>>()
const WAVE_BARS = 48
const WAVE_MAX_BYTES = 25 * 1024 * 1024

async function decodePeaks(src: string): Promise<number[] | null> {
  try {
    const response = await fetch(src)
    if (!response.ok) return null
    const context = new AudioContext()
    try {
      const buffer = await context.decodeAudioData(await response.arrayBuffer())
      const data = buffer.getChannelData(0)
      const step = Math.max(1, Math.floor(data.length / WAVE_BARS))
      const peaks: number[] = []
      for (let bar = 0; bar < WAVE_BARS; bar++) {
        let max = 0
        for (let i = bar * step; i < Math.min((bar + 1) * step, data.length); i++) {
          const value = Math.abs(data[i]!)
          if (value > max) max = value
        }
        peaks.push(max)
      }
      const top = Math.max(...peaks) || 1
      return peaks.map((peak) => peak / top)
    } finally {
      context.close()
    }
  } catch {
    return null
  }
}
</script>

<script setup lang="ts">
const props = defineProps<{ fileId: string; src: string; name: string; size: number; own: boolean }>()

const emit = defineEmits<{ error: [] }>()

const audio = ref<HTMLAudioElement | null>(null)

const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const peaks = ref<number[] | null>(null)

const progress = computed(() => (duration.value ? currentTime.value / duration.value : 0))

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return '0:00'
  const total = Math.floor(seconds)
  const minutes = Math.floor(total / 60)
  return `${minutes}:${String(total % 60).padStart(2, '0')}`
}

function toggle() {
  const element = audio.value
  if (!element) return
  if (element.paused) element.play().catch(() => {})
  else element.pause()
}

function onPlay() {
  if (playing.value && playing.value !== audio.value) playing.value.pause()
  playing.value = audio.value
  isPlaying.value = true
}

function onPause() {
  if (playing.value === audio.value) playing.value = null
  isPlaying.value = false
}

function onEnded() {
  onPause()
  currentTime.value = 0
  if (audio.value) audio.value.currentTime = 0
}

function onLoadedMetadata() {
  const seconds = audio.value?.duration ?? 0
  if (Number.isFinite(seconds)) duration.value = seconds
}

function seekTo(fraction: number) {
  const element = audio.value
  if (!element || !duration.value) return
  element.currentTime = Math.min(Math.max(fraction, 0), 1) * duration.value
  currentTime.value = element.currentTime
}

function onWaveClick(event: MouseEvent) {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  seekTo((event.clientX - rect.left) / rect.width)
}

function onWaveKeydown(event: KeyboardEvent) {
  if (!duration.value) return
  const step = 5 / duration.value
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    seekTo(progress.value + step)
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    seekTo(progress.value - step)
  }
}

watch(
  () => props.fileId,
  async (id) => {
    peaks.value = null
    if (props.size > WAVE_MAX_BYTES) return
    let pending = peaksCache.get(id)
    if (!pending) {
      pending = decodePeaks(props.src)
      peaksCache.set(id, pending)
    }
    const loaded = await pending
    if (!loaded) peaksCache.delete(id)
    if (props.fileId === id) peaks.value = loaded
  },
  { immediate: true },
)

watch(
  () => props.src,
  () => {
    isPlaying.value = false
    currentTime.value = 0
  },
)

onBeforeUnmount(() => {
  if (playing.value === audio.value) playing.value = null
})
</script>

<template>
  <div class="audio" :class="{ 'is-own': own, 'is-playing': isPlaying }">
    <audio
      ref="audio"
      :src="src"
      preload="metadata"
      @play="onPlay"
      @pause="onPause"
      @ended="onEnded"
      @timeupdate="currentTime = audio?.currentTime ?? 0"
      @loadedmetadata="onLoadedMetadata"
      @durationchange="onLoadedMetadata"
      @error="emit('error')"
    />

    <button
      type="button"
      class="audio__play"
      :aria-label="isPlaying ? 'Пауза' : 'Слушать'"
      @click="toggle"
    >
      <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" />
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M8 5.5v13l11-6.5z" />
      </svg>
    </button>

    <div class="audio__body">
      <div
        class="audio__wave"
        :class="{ 'is-line': !peaks }"
        role="slider"
        tabindex="0"
        aria-label="Перемотка"
        :aria-valuemin="0"
        :aria-valuemax="Math.round(duration)"
        :aria-valuenow="Math.round(currentTime)"
        :aria-valuetext="formatTime(currentTime)"
        :style="{ '--played': `${progress * 100}%` }"
        @click="onWaveClick"
        @keydown="onWaveKeydown"
      >
        <template v-if="peaks">
          <span
            v-for="(peak, index) in peaks"
            :key="index"
            class="audio__bar"
            :class="{ 'is-played': (index + 0.5) / peaks.length <= progress }"
            :style="{ height: `${Math.max(peak * 100, 12)}%` }"
          />
        </template>
      </div>

      <div class="audio__info">
        <span class="audio__time">
          {{ isPlaying || currentTime ? formatTime(currentTime) : formatTime(duration) }}
        </span>
        <span v-if="name !== 'Файл'" class="audio__name">{{ name }}</span>
      </div>
    </div>

    <a class="audio__download" :href="src" :download="name" aria-label="Скачать" title="Скачать">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M12 4v11" />
        <path d="M7.5 11.5 12 16l4.5-4.5" />
        <path d="M5 19h14" />
      </svg>
    </a>
  </div>
</template>

<style scoped>
.audio {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 300px;
  max-width: 100%;
  padding: 10px 12px;
  background: var(--color-ground);
  color: var(--color-text);
}

.audio.is-own {
  background: rgba(11, 18, 54, 0.12);
  color: var(--color-ink);
}

.audio audio {
  display: none;
}

.audio__play {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: none;
  padding: 0;
  background: var(--color-accent);
  border: none;
  border-radius: 50%;
  color: var(--color-ink);
  cursor: pointer;
  transition: transform 0.15s ease;
}

.audio__play:hover {
  transform: scale(1.06);
}

.audio.is-own .audio__play {
  background: var(--color-ink);
  color: var(--color-accent);
}

.audio__play svg {
  width: 20px;
  height: 20px;
}

.audio__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.audio__wave {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
}

.audio__wave:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.audio__wave.is-line {
  height: 4px;
  margin: 12px 0;
  background:
    linear-gradient(var(--color-accent), var(--color-accent)) 0 / var(--played, 0%) 100% no-repeat,
    rgba(230, 236, 255, 0.18);
  border-radius: 999px;
}

.audio.is-own .audio__wave.is-line {
  background:
    linear-gradient(var(--color-ink), var(--color-ink)) 0 / var(--played, 0%) 100% no-repeat,
    rgba(11, 18, 54, 0.22);
}

.audio__bar {
  flex: 1;
  min-width: 2px;
  background: rgba(230, 236, 255, 0.28);
  border-radius: 999px;
  transition: background 0.15s ease;
}

.audio__bar.is-played {
  background: var(--color-accent);
}

.audio.is-own .audio__bar {
  background: rgba(11, 18, 54, 0.28);
}

.audio.is-own .audio__bar.is-played {
  background: var(--color-ink);
}

.audio__info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-family: var(--font-mono);
  font-size: 11px;
}

.audio__time {
  flex: none;
}

.audio__name {
  overflow: hidden;
  opacity: 0.7;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audio__download {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  align-self: flex-start;
  border-radius: 10px;
  color: inherit;
  opacity: 0.6;
  transition:
    opacity 0.15s ease,
    color 0.15s ease;
}

.audio__download:hover {
  opacity: 1;
  color: var(--color-accent);
}

.audio.is-own .audio__download:hover {
  color: var(--color-ink);
}

.audio__download svg {
  width: 16px;
  height: 16px;
}

@media (prefers-reduced-motion: reduce) {
  .audio__play,
  .audio__bar {
    transition: none;
  }
}
</style>
