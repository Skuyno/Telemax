<script setup lang="ts">
import type { Message } from '~/types/chat'
import { formatMessageTime } from '~/utils/chatTime'

const props = defineProps<{ chatId: string }>()

const emit = defineEmits<{ jump: [Message] }>()

const { searchMessages } = useChats()

const query = ref('')
const results = ref<Message[]>([])
const isSearching = ref(false)
const searchDone = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | undefined

watch(query, (value) => {
  clearTimeout(searchTimer)
  searchDone.value = false
  const text = value.trim()
  if (!text) {
    results.value = []
    return
  }

  searchTimer = setTimeout(async () => {
    isSearching.value = true
    try {
      const found = await searchMessages(props.chatId, text)
      if (query.value.trim() === text) results.value = found
    } catch {
      results.value = []
    } finally {
      isSearching.value = false
      searchDone.value = true
    }
  }, 300)
})

watch(
  () => props.chatId,
  () => {
    query.value = ''
    results.value = []
    searchDone.value = false
  },
)

onBeforeUnmount(() => clearTimeout(searchTimer))
</script>

<template>
  <div class="search">
    <label class="search__field">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="11" cy="11" r="7" />
        <path d="M20 20l-3.5-3.5" />
      </svg>
      <input
        v-model="query"
        class="search__input"
        type="search"
        placeholder="Поиск по сообщениям"
        aria-label="Поиск по сообщениям"
        autofocus
      />
    </label>

    <div v-if="query.trim()" class="search__results">
      <button
        v-for="result in results"
        :key="result.id"
        type="button"
        class="search__result"
        @click="emit('jump', result)"
      >
        <span class="search__result-body">{{ result.body }}</span>
        <span class="search__result-time">{{ formatMessageTime(result.createdAt) }}</span>
      </button>
      <p v-if="isSearching" class="search__note">Ищем…</p>
      <p v-else-if="searchDone && !results.length" class="search__note">Ничего не нашли</p>
    </div>
  </div>
</template>

<style scoped>
.search {
  position: relative;
  flex: none;
  padding: 12px 20px;
  background: var(--color-lift);
  border-bottom: 1px solid var(--chat-line);
}

.search__field {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 14px;
  background: var(--color-ground);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
  color: var(--color-text-dim);
}

.search__field:focus-within {
  border-color: var(--color-focus);
}

.search__field svg {
  width: 16px;
  height: 16px;
  flex: none;
}

.search__input {
  width: 100%;
  background: none;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.search__input::placeholder {
  color: var(--color-text-dim);
}

.search__input::-webkit-search-cancel-button {
  display: none;
}

.search__results {
  position: absolute;
  top: 100%;
  right: 20px;
  left: 20px;
  z-index: 5;
  max-height: 320px;
  margin-top: 6px;
  overflow-y: auto;
  padding: 6px;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: var(--chat-radius-lg);
  box-shadow: var(--shadow-hard);
}

.search__result {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  background: none;
  border: none;
  border-radius: var(--chat-radius);
  text-align: left;
  cursor: pointer;
}

.search__result:hover {
  background: var(--color-surface);
}

.search__result-body {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search__result-time {
  flex: none;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-dim);
}

.search__note {
  margin: 8px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

@media (max-width: 900px) {
  .search {
    padding-inline: 14px;
  }

  .search__results {
    right: 14px;
    left: 14px;
  }
}
</style>
