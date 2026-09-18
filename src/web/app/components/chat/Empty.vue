<script setup lang="ts">
defineProps<{ hasChats: boolean }>()
</script>

<template>
  <section class="empty">
    <h2 class="empty__title">{{ hasChats ? 'Выберите чат' : 'Чатов пока нет' }}</h2>
    <p class="empty__hint">
      {{
        hasChats
          ? 'Откройте переписку в списке слева.'
          : 'Здесь появятся ваши переписки.'
      }}
    </p>
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
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-dim);
}
</style>
