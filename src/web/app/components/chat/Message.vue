<script setup lang="ts">
import type { Message } from '~/types/chat'
import { formatMessageTime } from '~/utils/chatTime'

defineProps<{ message: Message; own: boolean }>()
</script>

<template>
  <div class="line" :class="own ? 'line--out' : 'line--in'">
    <div class="bubble" :class="{ 'is-own': own }">
      <p class="bubble__body">{{ message.body }}</p>
      <span class="bubble__time">{{ formatMessageTime(message.createdAt) }}</span>
    </div>
  </div>
</template>

<style scoped>
.line {
  display: flex;
}

.line--in {
  justify-content: flex-start;
}

.line--out {
  justify-content: flex-end;
}

.bubble {
  max-width: 62%;
  padding: 9px 12px 7px;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: var(--radius);
}

.bubble.is-own {
  background: var(--color-surface);
  border-color: var(--chat-accent-soft);
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

.bubble__time {
  display: block;
  margin-top: 3px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-dim);
}

@media (max-width: 900px) {
  .bubble {
    max-width: 82%;
  }
}
</style>
