<script setup lang="ts">
const chatStore = useChatStore()

const emit = defineEmits<{ select: [string] }>()

function onSelect(chatId: string) {
  chatStore.setActiveChat(chatId)
  emit('select', chatId)
}

const search = computed({
  get: () => chatStore.search,
  set: (value: string) => chatStore.setSearch(value),
})
</script>

<template>
  <aside class="sidebar">
    <header class="sidebar__head">
      <span class="sidebar__logo">Телемакс</span>
      <NuxtLink to="/settings" class="sidebar__icon-btn" aria-label="Настройки">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="3" />
          <path
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
          />
        </svg>
      </NuxtLink>
    </header>

    <div class="sidebar__panel">
      <!-- Локальный фильтр по уже загруженным чатам: поиска людей на бэкенде нет. -->
      <label class="sidebar__search">
        <svg
          class="sidebar__search-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          v-model="search"
          class="sidebar__search-input"
          type="search"
          placeholder="Поиск по чатам"
          aria-label="Поиск по чатам"
        />
      </label>
    </div>

    <div class="sidebar__list">
      <ChatListItem
        v-for="chat in chatStore.visibleChats"
        :key="chat.id"
        :chat="chat"
        :active="chat.id === chatStore.activeChatId"
        @select="onSelect(chat.id)"
      />

      <p v-if="!chatStore.visibleChats.length" class="sidebar__empty">
        {{ chatStore.search ? 'Ничего не найдено' : 'Чатов пока нет' }}
      </p>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: 300px;
  flex: none;
  background: var(--color-lift);
  border-right: 1px solid var(--chat-line);
}

.sidebar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  flex: none;
  padding: 0 12px;
  border-bottom: 2px solid var(--color-accent);
}

.sidebar__logo {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-accent);
}

.sidebar__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 0.15s ease;
}

.sidebar__icon-btn:hover {
  color: var(--color-accent);
}

.sidebar__icon-btn svg {
  width: 18px;
  height: 18px;
}

.sidebar__panel {
  flex: none;
  padding: 10px 12px;
}

.sidebar__search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--radius);
  color: var(--color-text-dim);
}

.sidebar__search:focus-within {
  border-color: var(--color-focus);
}

.sidebar__search-icon {
  width: 14px;
  height: 14px;
  flex: none;
}

.sidebar__search-input {
  width: 100%;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
}

.sidebar__search-input::placeholder {
  color: var(--color-text-dim);
}

.sidebar__search-input::-webkit-search-cancel-button {
  display: none;
}

.sidebar__list {
  flex: 1;
  overflow-y: auto;
}

.sidebar__empty {
  margin: 24px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

@media (max-width: 900px) {
  .sidebar {
    width: 100%;
  }
}
</style>
