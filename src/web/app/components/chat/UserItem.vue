<script setup lang="ts">
import type { UserSearchResult } from '~/types/chat'

defineProps<{ user: UserSearchResult; disabled?: boolean }>()

defineEmits<{ select: [] }>()
</script>

<template>
  <button type="button" class="user" :disabled="disabled" @click="$emit('select')">
    <span class="user__avatar">{{ user.initials }}</span>
    <span class="user__body">
      <span class="user__title">{{ user.title }}</span>
      <span class="user__tag">@{{ user.username }}</span>
    </span>
  </button>
</template>

<style scoped>
.user {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 8px;
  background: none;
  border: none;
  border-left: 2px solid transparent;
  border-radius: var(--radius);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}

.user:hover:not(:disabled) {
  background: var(--color-surface);
}

.user:disabled {
  opacity: 0.6;
  cursor: wait;
}

.user__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-line);
  border-radius: var(--radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-text-muted);
}

.user__body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.user__title {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user__tag {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
