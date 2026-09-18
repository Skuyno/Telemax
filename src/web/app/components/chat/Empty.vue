<script setup lang="ts">
defineProps<{ hasChats: boolean }>()

const chatStore = useChatStore()
</script>

<template>
  <section class="empty">
    <h2 class="empty__title">{{ hasChats ? 'Выберите чат' : 'Чатов пока нет' }}</h2>
    <p class="empty__hint">
      {{
        hasChats
          ? 'Откройте переписку в списке слева или начните новую.'
          : 'Найдите собеседника по @username и начните переписку.'
      }}
    </p>
    <button type="button" class="empty__cta" @click="chatStore.requestSearchFocus()">
      <span aria-hidden="true">▶</span>
      Новый чат
    </button>
  </section>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  padding: 24px;
  background: var(--color-ground);
}

.empty__title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 20px;
  color: var(--color-text);
}

.empty__hint {
  margin: 0;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-dim);
}

.empty__cta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding: 11px 18px;
  background: var(--color-accent);
  border: none;
  border-radius: var(--radius);
  box-shadow: 3px 3px 0 var(--color-ink);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-ink);
  cursor: pointer;
}

.empty__cta:hover {
  background: var(--color-accent-hover);
}

.empty__cta:active {
  background: var(--color-accent-pressed);
}
</style>
