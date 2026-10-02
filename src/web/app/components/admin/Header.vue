<script setup lang="ts">
withDefaults(
  defineProps<{ title: string; back: string; icon?: 'shield' | 'users'; highlight?: boolean }>(),
  { icon: 'users', highlight: false },
)
</script>

<template>
  <header class="head">
    <NuxtLink :to="back" class="back" aria-label="Назад">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M15 18l-6-6 6-6" />
      </svg>
    </NuxtLink>

    <span class="badge" :class="{ 'is-highlight': highlight }" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
        <template v-if="icon === 'shield'">
          <path d="M12 3 5 6v5.5c0 4.2 2.9 7.3 7 8.5 4.1-1.2 7-4.3 7-8.5V6z" />
          <path d="M12 8.6l.9 1.9 2 .3-1.5 1.4.4 2-1.8-1-1.8 1 .4-2L9 10.8l2-.3z" />
        </template>
        <template v-else>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </template>
      </svg>
    </span>

    <h1 class="title">{{ title }}</h1>
  </header>
</template>

<style scoped>
.head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  height: 76px;
  padding: 0 36px;
  background: rgba(13, 22, 66, 0.7);
}

.head::after {
  content: '';
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    rgba(255, 204, 46, 0.7),
    rgba(255, 204, 46, 0.15) 30%,
    rgba(61, 79, 156, 0.45) 60%,
    transparent
  );
}

.back {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: none;
  background: rgba(7, 11, 28, 0.5);
  border-radius: 12px;
  box-shadow: inset 0 0 0 1px rgba(61, 79, 156, 0.75);
  color: var(--color-text);
}

.back:hover {
  background: var(--color-surface);
}

.back svg {
  width: 18px;
  height: 18px;
}

.badge {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: none;
  background: rgba(255, 204, 46, 0.14);
  border-radius: 12px;
  box-shadow: inset 0 0 0 1px rgba(255, 204, 46, 0.35);
  color: var(--color-accent);
}

.badge.is-highlight {
  background: linear-gradient(140deg, var(--color-accent), var(--color-accent-pressed));
  box-shadow: 0 0 22px rgba(255, 204, 46, 0.35);
  color: var(--color-ink);
}

.badge svg {
  width: 20px;
  height: 20px;
}

.title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 21px;
  letter-spacing: -0.015em;
  color: var(--color-text);
}

@media (max-width: 640px) {
  .head {
    gap: 12px;
    padding: 0 16px;
  }

  .title {
    font-size: 17px;
  }
}
</style>
