<script setup lang="ts">
import type { Message } from '~/types/chat'
import { formatMessageTime } from '~/utils/chatTime'

defineProps<{
  message: Message
  own: boolean
  initials: string
  avatarUrl?: string | null
  read?: boolean
  hideStatus?: boolean
  highlighted?: boolean
}>()

defineEmits<{ edit: []; remove: [] }>()
</script>

<template>
  <div
    class="line"
    :class="[own ? 'line--out' : 'line--in', { 'is-highlighted': highlighted }]"
    :data-message-id="message.id"
  >
    <span class="line__avatar">
      <UserAvatar :url="avatarUrl" :initials="initials" />
    </span>

    <div class="bubble" :class="{ 'is-own': own, 'is-deleted': message.isDeleted }">
      <p v-if="message.isDeleted" class="bubble__body is-deleted">Сообщение удалено</p>

      <template v-else>
        <div v-if="message.attachmentIds.length" class="bubble__attachments">
          <ChatAttachment
            v-for="fileId in message.attachmentIds"
            :key="fileId"
            :file-id="fileId"
            :own="own"
          />
        </div>
        <p v-if="message.body" class="bubble__body">{{ message.body }}</p>
      </template>

      <span class="bubble__meta">
        <span v-if="message.editedAt && !message.isDeleted" class="bubble__edited">изменено</span>
        <span class="bubble__time">{{ formatMessageTime(message.createdAt) }}</span>
        <svg
          v-if="own && !hideStatus && read"
          class="bubble__check"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-label="прочитано"
        >
          <path d="M2 13l4 4 8-9" />
          <path d="M9 17l4-4.5" />
          <path d="M13 17l8-9" />
        </svg>
        <svg
          v-else-if="own && !hideStatus"
          class="bubble__check"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-label="отправлено"
        >
          <path d="M4 13l5 5 11-12" />
        </svg>
      </span>
    </div>

    <div v-if="own && !message.isDeleted" class="line__actions">
      <button
        v-if="message.body"
        type="button"
        class="line__action"
        aria-label="Изменить сообщение"
        @click="$emit('edit')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M4 20h4L19 9l-4-4L4 16v4z" />
          <path d="M14 5l4 4" />
        </svg>
      </button>
      <button
        type="button"
        class="line__action is-danger"
        aria-label="Удалить сообщение"
        @click="$emit('remove')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M4 7h16" />
          <path d="M9 7V4h6v3" />
          <path d="M6 7l1 13h10l1-13" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.line {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  border-radius: var(--chat-radius-lg);
  transition: background 0.6s ease;
}

.line--in {
  justify-content: flex-start;
}

.line--out {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.line.is-highlighted {
  background: rgba(79, 216, 255, 0.12);
}

.line__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 11px;
  color: var(--color-accent);
}

.bubble {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px 10px;
  max-width: 62%;
  padding: 10px 14px;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
}

.bubble.is-own {
  background: var(--color-accent);
  border-color: var(--color-accent);
}

.bubble.is-deleted {
  background: transparent;
  border-style: dashed;
  border-color: var(--chat-line);
}

.bubble__attachments {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.bubble__body {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.bubble.is-own .bubble__body {
  color: var(--color-ink);
}

.bubble__body.is-deleted,
.bubble.is-own .bubble__body.is-deleted {
  font-style: italic;
  color: var(--color-text-dim);
}

.bubble__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: none;
  margin-left: auto;
}

.bubble__time,
.bubble__edited {
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.8;
  color: var(--color-text-dim);
}

.bubble.is-own:not(.is-deleted) .bubble__meta {
  color: var(--color-ink);
  opacity: 0.7;
}

.bubble.is-own:not(.is-deleted) .bubble__time,
.bubble.is-own:not(.is-deleted) .bubble__edited {
  color: inherit;
}

.bubble__check {
  width: 14px;
  height: 14px;
}

.line__actions {
  display: flex;
  gap: 4px;
  align-self: center;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.line:hover .line__actions,
.line__actions:focus-within {
  opacity: 1;
}

.line__action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius);
  color: var(--color-text-muted);
  cursor: pointer;
}

.line__action:hover {
  color: var(--color-accent);
}

.line__action.is-danger:hover {
  color: var(--color-error);
}

.line__action svg {
  width: 15px;
  height: 15px;
}

@media (max-width: 900px) {
  .bubble {
    max-width: 78%;
  }

  .line__actions {
    opacity: 1;
  }
}
</style>
