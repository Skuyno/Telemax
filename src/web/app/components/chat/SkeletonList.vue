<script setup lang="ts">
withDefaults(defineProps<{ rows?: number }>(), { rows: 7 })
</script>

<template>
  <div class="skeleton" aria-hidden="true">
    <div v-for="row in rows" :key="row" class="skeleton__row">
      <span class="skeleton__avatar shimmer" />
      <span class="skeleton__text">
        <span class="skeleton__line shimmer" :style="{ width: `${45 + ((row * 13) % 35)}%` }" />
        <span class="skeleton__line is-small shimmer" :style="{ width: `${55 + ((row * 7) % 30)}%` }" />
      </span>
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 12px;
}

.skeleton__row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
}

.skeleton__avatar {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: var(--chat-radius, 10px);
}

.skeleton__text {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.skeleton__line {
  height: 11px;
  border-radius: 999px;
}

.skeleton__line.is-small {
  height: 9px;
  opacity: 0.7;
}

.shimmer {
  background: linear-gradient(
    90deg,
    rgba(230, 236, 255, 0.07) 25%,
    rgba(230, 236, 255, 0.16) 50%,
    rgba(230, 236, 255, 0.07) 75%
  );
  background-size: 300% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

@keyframes shimmer {
  from {
    background-position: 150% 0;
  }

  to {
    background-position: -150% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .shimmer {
    animation: none;
  }
}
</style>
