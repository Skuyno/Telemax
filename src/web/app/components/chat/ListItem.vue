<script setup lang="ts">
import type { Chat } from '~/types/chat'
import { formatChatListTime } from '~/utils/chatTime'

const props = defineProps<{ chat: Chat; active: boolean }>()

defineEmits<{ select: [] }>()

const chatStore = useChatStore()

const online = computed(() => chatStore.isPeerOnline(props.chat))
const typing = computed(() => chatStore.isPeerTyping(props.chat.id))
const unread = computed(() => (props.active ? 0 : props.chat.unreadCount))

const preview = computed(() => {
  const last = props.chat.lastMessage
  if (!last) return 'Нет сообщений'
  const body = last.body || 'Вложение'
  return last.authorLabel ? `${last.authorLabel}: ${body}` : body
})
</script>

<template>
  <button type="button" class="row" :class="{ 'is-active': active }" @click="$emit('select')">
    <span class="row__avatar">
      <UserAvatar :url="chat.avatarUrl" :initials="chat.initials" />
      <span v-if="online" class="row__online" aria-label="в сети" />
    </span>

    <span class="row__body">
      <span class="row__top">
        <span class="row__title">{{ chat.title }}</span>
        <span v-if="chat.lastMessage" class="row__time">
          {{ formatChatListTime(chat.lastMessage.createdAt) }}
        </span>
      </span>

      <span class="row__bottom">
        <span v-if="typing" class="row__preview is-typing">печатает…</span>
        <span v-else class="row__preview">{{ preview }}</span>
        <span v-if="unread" class="row__unread">{{ unread > 99 ? '99+' : unread }}</span>
      </span>
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
  position: relative;
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

.row__online {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 12px;
  height: 12px;
  background: var(--color-focus);
  border: 2px solid var(--color-lift);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--color-focus);
}

.row.is-active .row__online,
.row:hover .row__online {
  border-color: var(--color-surface);
}

.row__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.row__preview.is-typing {
  color: var(--color-focus);
}

.row__unread {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 20px;
  flex: none;
  padding: 0 7px;
  background: var(--color-accent);
  border-radius: 999px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 11px;
  color: var(--color-ink);
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
