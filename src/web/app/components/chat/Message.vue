<script setup lang="ts">
import type { Message } from '~/types/chat'
import { formatMessageTime } from '~/utils/chatTime'

defineProps<{ message: Message; own: boolean; initials: string }>()
</script>

<template>
  <div class="line" :class="own ? 'line--out' : 'line--in'">
    <span class="line__avatar">{{ initials }}</span>

    <div class="bubble" :class="{ 'is-own': own }">
      <p class="bubble__body">{{ message.body }}</p>
      <span class="bubble__time">{{ formatMessageTime(message.createdAt) }}</span>
    </div>
  </div>
</template>

<style scoped>
.line {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.line--in {
  justify-content: flex-start;
}

.line--out {
  flex-direction: row-reverse;
  justify-content: flex-start;
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
  align-items: flex-end;
  gap: 10px;
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

.bubble__body {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text);
  white-space: pre-line;
  overflow-wrap: anywhere;
}

.bubble.is-own .bubble__body {
  color: var(--color-ink);
}

.bubble__time {
  flex: none;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.8;
  color: var(--color-text-dim);
}

.bubble.is-own .bubble__time {
  color: var(--color-ink);
  opacity: 0.7;
}

@media (max-width: 900px) {
  .bubble {
    max-width: 78%;
  }
}
</style>
