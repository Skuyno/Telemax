<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    icon: 'user' | 'shield' | 'profile' | 'key' | 'add' | 'at' | 'lock'
    tone?: 'accent' | 'signal' | 'neutral'
    size?: number
    angle: number
    radius: number
  }>(),
  { tone: 'neutral', size: 44 },
)

const position = computed(() => {
  const radians = (props.angle * Math.PI) / 180
  return {
    left: `calc(50% + ${(Math.cos(radians) * props.radius).toFixed(2)}px)`,
    top: `calc(50% + ${(Math.sin(radians) * props.radius).toFixed(2)}px)`,
    width: `${props.size}px`,
    height: `${props.size}px`,
  }
})
</script>

<template>
  <span class="tile" :class="tone" :style="position" aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <template v-if="icon === 'user'">
        <circle cx="12" cy="8" r="3.5" />
        <path d="M5.5 19a6.5 6.5 0 0 1 13 0" />
      </template>
      <template v-else-if="icon === 'shield'">
        <path d="M12 3 5 6v5.5c0 4.2 2.9 7.3 7 8.5 4.1-1.2 7-4.3 7-8.5V6z" />
        <path d="M12 8.6l.9 1.9 2 .3-1.5 1.4.4 2-1.8-1-1.8 1 .4-2L9 10.8l2-.3z" />
      </template>
      <template v-else-if="icon === 'profile'">
        <circle cx="12" cy="12" r="8.5" />
        <circle cx="12" cy="10" r="2.6" />
        <path d="M7 17.8a5.6 5.6 0 0 1 10 0" />
      </template>
      <template v-else-if="icon === 'key'">
        <circle cx="9" cy="9" r="3.5" />
        <path d="M11.5 11.5 20 20" />
        <path d="M17 17l2-2" />
      </template>
      <template v-else-if="icon === 'add'">
        <circle cx="10" cy="8" r="3.4" />
        <path d="M4 19a6 6 0 0 1 12 0" />
        <path d="M18 7v5M15.5 9.5h5" />
      </template>
      <template v-else-if="icon === 'at'">
        <circle cx="12" cy="12" r="4" />
        <path d="M16 8v5a3 3 0 0 0 5-2 9 9 0 1 0-3.5 7" />
      </template>
      <template v-else>
        <rect x="5" y="11" width="14" height="9" rx="2" />
        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      </template>
    </svg>
  </span>
</template>

<style scoped>
.tile {
  position: absolute;
  display: grid;
  place-items: center;
  border-radius: 13px;
  transform: translate(-50%, -50%);
}

.tile svg {
  width: 45%;
  height: 45%;
}

.neutral {
  background: var(--color-surface);
  color: var(--color-text-muted);
  box-shadow: inset 0 0 0 1px rgba(61, 79, 156, 0.75);
}

.accent {
  background: var(--color-lift);
  color: var(--color-accent);
  box-shadow:
    inset 0 0 0 1px rgba(255, 204, 46, 0.45),
    0 0 18px rgba(255, 204, 46, 0.15);
}

.signal {
  background: var(--color-lift);
  color: var(--color-focus);
  box-shadow:
    inset 0 0 0 1px rgba(79, 216, 255, 0.45),
    0 0 18px rgba(79, 216, 255, 0.12);
}
</style>
