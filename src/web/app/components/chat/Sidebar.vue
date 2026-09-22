<script setup lang="ts">
import type { UserSearchResult } from '~/types/chat'

const chatStore = useChatStore()
const auth = useAuthStore()
const { searchUsers, openChatWith, openSavedChat } = useChats()

const myName = computed(() => auth.user?.displayName ?? auth.user?.username ?? '')
const myInitials = computed(() => (myName.value ? toInitials(myName.value) : ''))

const emit = defineEmits<{ select: [string] }>()

const searchInput = ref<HTMLInputElement | null>(null)
const openingUserId = ref<string | null>(null)
const openError = ref('')

function onSelect(chatId: string) {
  chatStore.setActiveChat(chatId)
  emit('select', chatId)
}

async function onSelectUser(user: UserSearchResult) {
  openingUserId.value = user.id
  openError.value = ''
  try {
    await openChatWith(user)
    if (chatStore.activeChatId) emit('select', chatStore.activeChatId)
  } catch (e) {
    openError.value = extractApiErrorMessage(e, 'Не удалось открыть чат')
  } finally {
    openingUserId.value = null
  }
}

async function onOpenSaved() {
  openError.value = ''
  try {
    await openSavedChat()
    if (chatStore.activeChatId) emit('select', chatStore.activeChatId)
  } catch (e) {
    openError.value = extractApiErrorMessage(e, 'Не удалось открыть избранное')
  }
}

const search = computed({
  get: () => chatStore.search,
  set: (value: string) => chatStore.setSearch(value),
})

const isSearching = computed(() => chatStore.search.trim().length > 0)

// Людей ищем на сервере с паузой, чтобы не слать запрос на каждую букву.
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => chatStore.search,
  (value) => {
    openError.value = ''
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => searchUsers(value), 300)
  },
)

watch(
  () => chatStore.searchFocusTick,
  () => searchInput.value?.focus(),
)

onBeforeUnmount(() => clearTimeout(searchTimer))
</script>

<template>
  <aside class="sidebar">
    <header class="sidebar__head">
      <span class="sidebar__logo">Телемакс</span>
      <div class="sidebar__actions">
        <button
          type="button"
          class="sidebar__icon-btn"
          aria-label="Избранное"
          title="Избранное"
          @click="onOpenSaved"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M6 3h12v18l-6-4.5L6 21z" />
          </svg>
        </button>
        <button
          type="button"
          class="sidebar__icon-btn"
          aria-label="Новый чат"
          @click="chatStore.requestSearchFocus()"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M4 20h4L19 9l-4-4L4 16v4z" />
            <path d="M14 5l4 4" />
          </svg>
        </button>
        <NuxtLink to="/settings" class="sidebar__icon-btn" aria-label="Настройки">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
            />
          </svg>
        </NuxtLink>
      </div>
    </header>

    <div class="sidebar__panel">
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
          ref="searchInput"
          v-model="search"
          class="sidebar__search-input"
          type="search"
          placeholder="Поиск по @username"
          aria-label="Поиск по @username"
        />
      </label>
    </div>

    <div class="sidebar__list">
      <p v-if="isSearching && chatStore.visibleChats.length" class="sidebar__section">Чаты</p>

      <ChatListItem
        v-for="chat in chatStore.visibleChats"
        :key="chat.id"
        :chat="chat"
        :active="chat.id === chatStore.activeChatId"
        @select="onSelect(chat.id)"
      />

      <template v-if="isSearching">
        <p class="sidebar__section">Люди</p>

        <ChatUserItem
          v-for="user in chatStore.userResults"
          :key="user.id"
          :user="user"
          :disabled="openingUserId === user.id"
          @select="onSelectUser(user)"
        />

        <p v-if="openError" class="sidebar__empty is-error">{{ openError }}</p>
        <p v-else-if="chatStore.isSearchingUsers" class="sidebar__empty">Ищем…</p>
        <p v-else-if="!chatStore.userResults.length" class="sidebar__empty">
          Никого не нашли
        </p>
      </template>

      <template v-else>
        <p v-if="openError" class="sidebar__empty is-error">{{ openError }}</p>
        <p v-else-if="chatStore.chatsError" class="sidebar__empty is-error">
          {{ chatStore.chatsError }}
        </p>
        <p v-else-if="chatStore.isLoadingChats && !chatStore.chats.length" class="sidebar__empty">
          Загрузка…
        </p>
        <p v-else-if="!chatStore.chats.length" class="sidebar__empty">
          Чатов пока нет. Найдите собеседника по @username.
        </p>
      </template>
    </div>

    <footer v-if="myName" class="sidebar__me">
      <span class="sidebar__me-avatar">
        <UserAvatar :url="auth.user?.avatarUrl" :initials="myInitials" />
      </span>
      <span class="sidebar__me-name">{{ myName }}</span>
    </footer>
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
  height: 72px;
  flex: none;
  padding: 0 16px;
  border-bottom: 1px solid var(--chat-line);
}

.sidebar__logo {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-accent);
}

.sidebar__actions {
  display: flex;
  gap: 8px;
}

.sidebar__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius);
  color: var(--color-text-muted);
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}

.sidebar__icon-btn:hover {
  color: var(--color-accent);
  border-color: var(--chat-accent-soft);
}

.sidebar__icon-btn svg {
  width: 18px;
  height: 18px;
}

.sidebar__panel {
  flex: none;
  padding: 14px 12px 8px;
}

.sidebar__search {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  padding: 0 14px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
  color: var(--color-text-dim);
}

.sidebar__search:focus-within {
  border-color: var(--color-focus);
}

.sidebar__search-icon {
  width: 16px;
  height: 16px;
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
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
}

.sidebar__section {
  margin: 6px 4px 0;
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-dim);
}

.sidebar__empty {
  margin: 18px 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.sidebar__empty.is-error {
  color: var(--color-error);
}

.sidebar__me {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
  padding: 14px 16px;
  border-top: 1px solid var(--chat-line);
}

.sidebar__me-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-accent-soft);
  border-radius: var(--chat-radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-accent);
}

.sidebar__me-name {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .sidebar {
    width: 100%;
  }
}
</style>
