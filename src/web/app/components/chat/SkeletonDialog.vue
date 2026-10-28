<script setup lang="ts">
const bubbles = [
  { own: false, width: 42 },
  { own: true, width: 30 },
  { own: false, width: 54 },
  { own: true, width: 38 },
  { own: false, width: 26 },
  { own: true, width: 46 },
]
</script>

<template>
  <section class="skeleton" aria-hidden="true">
    <header class="skeleton__head">
      <span class="skeleton__avatar shimmer" />
      <span class="skeleton__head-text">
        <span class="skeleton__line shimmer" style="width: 140px" />
        <span class="skeleton__line is-small shimmer" style="width: 80px" />
      </span>
    </header>

    <div class="skeleton__feed">
      <div
        v-for="(bubble, index) in bubbles"
        :key="index"
        class="skeleton__line-row"
        :class="{ 'is-own': bubble.own }"
      >
        <span v-if="!bubble.own" class="skeleton__bubble-avatar shimmer" />
        <span class="skeleton__bubble shimmer" :style="{ width: `${bubble.width}%` }" />
      </div>
    </div>

    <footer class="skeleton__composer">
      <span class="skeleton__tool shimmer" />
      <span class="skeleton__input shimmer" />
      <span class="skeleton__send shimmer" />
    </footer>
  </section>
</template>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: var(--color-ground);
}

.skeleton__head {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 72px;
  flex: none;
  padding: 0 20px;
  background: var(--color-lift);
  border-bottom: 1px solid var(--chat-line);
}

.skeleton__head-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton__avatar {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: var(--chat-radius);
}

.skeleton__feed {
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
  padding: 24px 20px;
  background-image: var(--chat-grid);
  background-size: 48px 48px;
}

.skeleton__line-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.skeleton__line-row.is-own {
  justify-content: flex-end;
}

.skeleton__bubble-avatar {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: var(--chat-radius);
}

.skeleton__bubble {
  height: 42px;
  border-radius: var(--chat-radius-lg);
}

.skeleton__line {
  height: 12px;
  border-radius: 999px;
}

.skeleton__line.is-small {
  height: 9px;
  opacity: 0.7;
}

.skeleton__composer {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
  padding: 16px 20px;
  background: var(--color-lift);
  border-top: 1px solid var(--chat-line);
}

.skeleton__tool,
.skeleton__send {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: var(--chat-radius-lg);
}

.skeleton__input {
  height: 48px;
  flex: 1;
  border-radius: var(--chat-radius-lg);
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
