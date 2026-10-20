<script setup lang="ts">
import type { Chat, GroupMember, UserSearchResult } from '~/types/chat'

const props = defineProps<{ chat: Chat }>()

const emit = defineEmits<{ close: [] }>()

const chatStore = useChatStore()
const { loadMembers, addMembers, removeMember, renameGroup, searchUsers } = useChats()

const members = ref<GroupMember[]>([])
const isLoading = ref(true)
const error = ref('')
const busyId = ref('')

const title = ref(props.chat.title)
const isRenaming = ref(false)

const query = ref('')
const isAdding = ref(false)

const iAmOwner = computed(() =>
  members.value.some((member) => member.id === chatStore.meId && member.isOwner),
)

const results = computed(() =>
  chatStore.userResults.filter((user) => !members.value.some((member) => member.id === user.id)),
)

async function refresh() {
  error.value = ''
  try {
    members.value = await loadMembers(props.chat.id)
  } catch (e) {
    error.value = extractApiErrorMessage(e, 'Не удалось загрузить участников')
  } finally {
    isLoading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(query, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => searchUsers(value), 300)
})

async function onAdd(user: UserSearchResult) {
  isAdding.value = true
  error.value = ''
  try {
    await addMembers(props.chat.id, [user.id])
    query.value = ''
    chatStore.userResults = []
    await refresh()
  } catch (e) {
    error.value = extractApiErrorMessage(e, 'Не удалось добавить участника')
  } finally {
    isAdding.value = false
  }
}

async function onRemove(member: GroupMember) {
  if (busyId.value) return

  busyId.value = member.id
  error.value = ''
  try {
    await removeMember(props.chat.id, member.id)
    await refresh()
  } catch (e) {
    error.value = extractApiErrorMessage(e, 'Не удалось удалить участника')
  } finally {
    busyId.value = ''
  }
}

async function onLeave() {
  const me = chatStore.meId
  if (!me || busyId.value) return

  busyId.value = me
  error.value = ''
  try {
    await removeMember(props.chat.id, me)
    chatStore.removeChat(props.chat.id)
    emit('close')
  } catch (e) {
    error.value = extractApiErrorMessage(e, 'Не удалось выйти из группы')
  } finally {
    busyId.value = ''
  }
}

async function onRename() {
  const next = title.value.trim()
  if (!next || next === props.chat.title) {
    title.value = props.chat.title
    return
  }

  isRenaming.value = true
  error.value = ''
  try {
    await renameGroup(props.chat.id, next)
  } catch (e) {
    title.value = props.chat.title
    error.value = extractApiErrorMessage(e, 'Не удалось переименовать группу')
  } finally {
    isRenaming.value = false
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  refresh()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  chatStore.userResults = []
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div
      class="overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Участники группы"
      @click.self="emit('close')"
    >
      <div class="card">
        <header class="card__head">
          <h2 class="card__title">Группа</h2>
          <button type="button" class="card__close" aria-label="Закрыть" @click="emit('close')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 6 6 18" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </header>

        <label class="field">
          <span class="field__label">Название</span>
          <input
            v-model="title"
            class="field__input"
            type="text"
            maxlength="128"
            :disabled="!iAmOwner || isRenaming"
            @blur="onRename"
            @keydown.enter="onRename"
          />
        </label>

        <label v-if="iAmOwner" class="field">
          <span class="field__label">Добавить участника</span>
          <input
            v-model="query"
            class="field__input"
            type="search"
            placeholder="Поиск по @username"
            :disabled="isAdding"
          />
        </label>

        <div v-if="iAmOwner && query.trim()" class="results">
          <button
            v-for="user in results"
            :key="user.id"
            type="button"
            class="row"
            :disabled="isAdding"
            @click="onAdd(user)"
          >
            <span class="row__avatar">
              <UserAvatar :url="user.avatarUrl" :initials="user.initials" />
            </span>
            <span class="row__text">
              <span class="row__name">{{ user.title }}</span>
              <span class="row__tag">@{{ user.username }}</span>
            </span>
          </button>

          <p v-if="chatStore.isSearchingUsers" class="note">Ищем…</p>
          <p v-else-if="!results.length" class="note">Никого не нашли</p>
        </div>

        <div class="members">
          <p class="field__label">Участники</p>

          <p v-if="isLoading" class="note">Загружаем…</p>

          <div v-for="member in members" v-else :key="member.id" class="row is-static">
            <span class="row__avatar">
              <UserAvatar :url="member.avatarUrl" :initials="member.initials" />
            </span>
            <span class="row__text">
              <span class="row__name">{{ member.title }}</span>
              <span class="row__tag">
                {{ member.isOwner ? 'владелец' : `@${member.username}` }}
              </span>
            </span>

            <button
              v-if="iAmOwner && !member.isOwner"
              type="button"
              class="row__action"
              :aria-label="`Удалить ${member.title}`"
              :disabled="busyId === member.id"
              @click="onRemove(member)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M18 6 6 18" />
                <path d="M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <p v-if="error" class="card__error">{{ error }}</p>

        <button
          v-if="!isLoading && !iAmOwner"
          type="button"
          class="leave"
          :disabled="!!busyId"
          @click="onLeave"
        >
          Выйти из группы
        </button>

        <p v-else-if="!isLoading" class="note">
          Владелец не может выйти из группы.
        </p>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(7, 11, 28, 0.88);
}

.card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 420px;
  max-height: 86vh;
  overflow-y: auto;
  padding: 24px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
}

.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card__title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 18px;
  color: var(--color-text);
}

.card__close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
}

.card__close:hover {
  color: var(--color-accent);
}

.card__close svg {
  width: 18px;
  height: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__label {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.field__input {
  height: 46px;
  padding: 0 16px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  border-radius: 12px;
  outline: none;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
}

.field__input:focus {
  border-color: var(--color-focus);
}

.field__input:disabled {
  opacity: 0.7;
}

.field__input::placeholder {
  color: var(--color-text-dim);
}

.field__input::-webkit-search-cancel-button {
  display: none;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.members {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 8px;
  background: none;
  border: none;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
}

.row:hover:not(.is-static):not(:disabled) {
  background: var(--color-surface);
}

.row.is-static {
  cursor: default;
}

.row__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-line, var(--color-line));
  border-radius: 12px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-accent);
}

.row__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.row__name {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row__tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.row__action {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
}

.row__action:hover:not(:disabled) {
  color: var(--color-error);
}

.row__action svg {
  width: 15px;
  height: 15px;
}

.note {
  margin: 4px 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.card__error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-error);
}

.leave {
  height: 44px;
  background: var(--color-ground);
  border: 1px solid var(--color-error);
  border-radius: 14px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-error);
  cursor: pointer;
}

.leave:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-ink);
}

.leave:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
