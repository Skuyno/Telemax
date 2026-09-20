<script setup lang="ts">
import type { Chat } from '~/types/chat'
import { formatChatListTime } from '~/utils/chatTime'

const props = defineProps<{ chat: Chat; active: boolean }>()

defineEmits<{ select: [] }>()

const preview = computed(() => {
  const last = props.chat.lastMessage
  if (!last) return 'Нет сообщений'
  return last.authorLabel ? `${last.authorLabel}: ${last.body}` : last.body
})
</script>

<template>
  <button type="button" class="row" :class="{ 'is-active': active }" @click="$emit('select')">
    <span class="row__avatar">{{ chat.initials }}</span>

    <span class="row__body">
      <span class="row__top">
        <span class="row__title">{{ chat.title }}</span>
        <span v-if="chat.lastMessage" class="row__time">
          {{ formatChatListTime(chat.lastMessage.createdAt) }}
        </span>
      </span>

      <span class="row__preview">{{ preview }}</span>
    </span>
  </button>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--chat-radius);
  text-align: left;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}

.row:hover {
  background: var(--color-surface);
}

.row.is-active {
  background: var(--color-surface);
  border-color: var(--chat-line);
}

.row__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-accent);
}

.row.is-active .row__avatar {
  border-color: var(--chat-accent-soft);
}

.row__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.row__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.row__title {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row__time {
  flex: none;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-dim);
}

.row__preview {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
