<script setup lang="ts">
import type { Chat, Message, PinScope } from '~/types/chat'
import { dayKey, formatDateSeparator } from '~/utils/chatTime'

const props = defineProps<{
  chat: Chat
  messages: Message[]
  meId: string
  send: (text: string, attachmentIds: string[], replyToId: string | null) => Promise<void>
  loadError?: string
}>()

const emit = defineEmits<{ back: []; loadOlder: []; typing: [] }>()

const auth = useAuthStore()
const chatStore = useChatStore()
const { editMessage, deleteMessage, loadUntil, pinMessage, unpinMessage } = useChats()

const composer = ref<{ reset: () => void; focus: () => void } | null>(null)
const editing = ref<Message | null>(null)
const replyingTo = ref<Message | null>(null)
const forwarding = ref<Message | null>(null)
const pendingRemoval = ref<Message | null>(null)
const isRemoving = ref(false)
const isSending = ref(false)
const sendError = ref('')
const feed = ref<HTMLElement | null>(null)

const searchOpen = ref(false)
const membersOpen = ref(false)
const highlightedId = ref<string | null>(null)
let highlightTimer: ReturnType<typeof setTimeout> | undefined

const online = computed(() => props.chat.type === 'direct' && chatStore.isPeerOnline(props.chat))
const typing = computed(() => chatStore.isPeerTyping(props.chat.id))

const memberCountLabel = computed(() => {
  const count = props.chat.memberCount ?? 0
  const tail = count % 10
  const teens = count % 100
  if (tail === 1 && teens !== 11) return `${count} участник`
  if (tail >= 2 && tail <= 4 && (teens < 12 || teens > 14)) return `${count} участника`
  return `${count} участников`
})

const myInitials = computed(() => {
  const name = auth.user?.displayName ?? auth.user?.username ?? ''
  return name ? toInitials(name) : ''
})

const isGroup = computed(() => props.chat.type === 'group')
const isNotifications = computed(() => props.chat.type === 'notifications')

function senderName(senderId: string) {
  return chatStore.profileByUserId[senderId]?.title ?? 'Неизвестный пользователь'
}

function senderInitials(senderId: string) {
  if (senderId === props.meId) return myInitials.value
  if (isGroup.value) return chatStore.profileByUserId[senderId]?.initials ?? ''
  return props.chat.initials
}

function senderAvatar(senderId: string) {
  if (senderId === props.meId) return auth.user?.avatarUrl ?? null
  if (isGroup.value) return chatStore.profileByUserId[senderId]?.avatarUrl ?? null
  return props.chat.avatarUrl
}

const messageById = computed(() => new Map(props.messages.map((message) => [message.id, message])))

function authorLabel(senderId: string) {
  if (senderId === props.meId) return 'Вы'
  if (isGroup.value) return senderName(senderId)
  return props.chat.title
}

function forwardedName(message: Message) {
  const senderId = message.forwardedFromSenderId
  if (!senderId) return undefined
  if (senderId === props.meId) return 'Вы'
  if (senderId === props.chat.peerId && props.chat.type === 'direct') return props.chat.title
  return chatStore.profileByUserId[senderId]?.title ?? 'Пользователь'
}

const pinned = computed(() => chatStore.pinnedByChatId[props.chat.id] ?? [])
const pinnedIndex = ref(0)
const currentPin = computed(() => pinned.value[Math.min(pinnedIndex.value, pinned.value.length - 1)])
const pinnedIds = computed(() => new Set(pinned.value.map((message) => message.id)))

const pinFlow = ref<{ mode: 'pin' | 'unpin'; message: Message } | null>(null)
const isPinning = ref(false)

watch(
  () => pinned.value.length,
  (length) => {
    if (pinnedIndex.value >= length) pinnedIndex.value = 0
  },
)

function onPinnedClick() {
  const message = currentPin.value
  if (!message) return
  jumpTo(message)
  pinnedIndex.value = (pinnedIndex.value + 1) % pinned.value.length
}

function startPin(message: Message) {
  if (props.chat.isSaved) applyPin('pin', message, 'me')
  else pinFlow.value = { mode: 'pin', message }
}

function startUnpin(message: Message) {
  const scope = pinned.value.find((item) => item.id === message.id)?.pinScope
  if (scope === 'me' || props.chat.isSaved) applyPin('unpin', message, 'me')
  else pinFlow.value = { mode: 'unpin', message }
}

async function applyPin(mode: 'pin' | 'unpin', message: Message, scope: PinScope) {
  if (isPinning.value) return
  isPinning.value = true
  sendError.value = ''
  try {
    if (mode === 'pin') await pinMessage(props.chat.id, message.id, scope)
    else await unpinMessage(props.chat.id, message.id, scope)
    pinFlow.value = null
    if (mode === 'pin') pinnedIndex.value = 0
  } catch (e) {
    sendError.value = extractApiErrorMessage(
      e,
      mode === 'pin' ? 'Не удалось закрепить сообщение' : 'Не удалось открепить сообщение',
    )
    pinFlow.value = null
  } finally {
    isPinning.value = false
  }
}

function onPinScope(scope: PinScope) {
  if (pinFlow.value) applyPin(pinFlow.value.mode, pinFlow.value.message, scope)
}

function onForwarded(chatId: string) {
  forwarding.value = null
  chatStore.setActiveChat(chatId)
}

function previewText(message: Message) {
  if (message.isDeleted) return 'Сообщение удалено'
  return message.body || 'Вложение'
}

function quoteFor(message: Message) {
  if (!message.replyToId) return null
  const original = messageById.value.get(message.replyToId)
  if (!original) return { authorName: 'Ответ', body: 'Сообщение выше в переписке' }
  return { authorName: authorLabel(original.senderId), body: previewText(original) }
}

const replyPreview = computed(() =>
  replyingTo.value
    ? {
        id: replyingTo.value.id,
        authorName: authorLabel(replyingTo.value.senderId),
        body: previewText(replyingTo.value),
      }
    : null,
)

function startReply(message: Message) {
  editing.value = null
  replyingTo.value = message
  sendError.value = ''
}

function jumpToReply(message: Message) {
  if (message.replyToId) jumpTo({ ...message, id: message.replyToId })
}

const MESSAGE_MENU_WIDTH = 200
const MESSAGE_MENU_ITEM_HEIGHT = 44

const messageMenu = ref<{ message: Message; x: number; y: number } | null>(null)
const messageMenuRoot = ref<HTMLElement | null>(null)

const menuItems = computed(() => {
  const message = messageMenu.value?.message
  if (!message) return []
  const own = message.senderId === props.meId
  return [
    ...(isNotifications.value ? [] : [{ key: 'reply', label: 'Ответить' }]),
    { key: 'forward', label: 'Переслать' },
    pinnedIds.value.has(message.id)
      ? { key: 'unpin', label: 'Открепить' }
      : { key: 'pin', label: 'Закрепить' },
    ...(own && message.body ? [{ key: 'edit', label: 'Изменить' }] : []),
    ...(own ? [{ key: 'remove', label: 'Удалить' }] : []),
  ]
})

function openMessageMenu(message: Message, x: number, y: number) {
  const height = 12 + MESSAGE_MENU_ITEM_HEIGHT * 5
  messageMenu.value = {
    message,
    x: Math.max(8, Math.min(x, window.innerWidth - MESSAGE_MENU_WIDTH - 8)),
    y: Math.max(8, Math.min(y, window.innerHeight - height - 8)),
  }
}

function closeMessageMenu() {
  messageMenu.value = null
}

function onMessageMenuAction(key: string) {
  const message = messageMenu.value?.message
  closeMessageMenu()
  if (!message) return
  if (key === 'reply') startReply(message)
  else if (key === 'forward') forwarding.value = message
  else if (key === 'pin') startPin(message)
  else if (key === 'unpin') startUnpin(message)
  else if (key === 'edit') startEdit(message)
  else if (key === 'remove') onRemove(message)
}

function onMessageMenuPointerDown(event: PointerEvent) {
  if (!messageMenuRoot.value?.contains(event.target as Node)) closeMessageMenu()
}

function onMessageMenuKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeMessageMenu()
}

watch(messageMenu, (menu, previous) => {
  if (menu && !previous) {
    window.addEventListener('pointerdown', onMessageMenuPointerDown)
    window.addEventListener('keydown', onMessageMenuKeydown)
    window.addEventListener('resize', closeMessageMenu)
  } else if (!menu) {
    window.removeEventListener('pointerdown', onMessageMenuPointerDown)
    window.removeEventListener('keydown', onMessageMenuKeydown)
    window.removeEventListener('resize', closeMessageMenu)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onMessageMenuPointerDown)
  window.removeEventListener('keydown', onMessageMenuKeydown)
  window.removeEventListener('resize', closeMessageMenu)
})

const typingLabel = computed(() => {
  if (!isGroup.value) return 'печатает'
  const userId = chatStore.typingUserIdByChatId[props.chat.id]
  const name = userId ? chatStore.profileByUserId[userId]?.title : ''
  return name ? `${name} печатает` : 'печатает'
})

/** Лента, разбитая на группы по дням — под разделители дат. */
const groups = computed(() => {
  const result: { key: string; date: string; items: Message[] }[] = []

  for (const message of props.messages) {
    if (message.isDeleted) continue
    const key = dayKey(message.createdAt)
    const last = result.at(-1)
    if (last?.key === key) last.items.push(message)
    else result.push({ key, date: formatDateSeparator(message.createdAt), items: [message] })
  }

  return result
})

let pinTimer: ReturnType<typeof setInterval> | undefined
let pinStoppedAt = 0

async function scrollToBottom() {
  await nextTick()
  if (!feed.value) return
  feed.value.scrollTop = feed.value.scrollHeight
  pinnedToBottom.value = true
  holdBottom()
}

/** Пока грузятся вложения, лента меняет высоту — держим низ ещё полторы секунды. */
function holdBottom() {
  clearInterval(pinTimer)
  pinStoppedAt = Date.now() + 1500
  pinTimer = setInterval(() => {
    const el = feed.value
    if (!el || Date.now() > pinStoppedAt) {
      clearInterval(pinTimer)
      return
    }
    if (pinnedToBottom.value) el.scrollTop = el.scrollHeight
  }, 80)
}

async function onSubmit(text: string, attachmentIds: string[]) {
  if (isSending.value) return

  if (editing.value) {
    if (!text) return
    isSending.value = true
    sendError.value = ''
    try {
      if (text !== editing.value.body) await editMessage(props.chat.id, editing.value.id, text)
      cancelEdit()
    } catch (e) {
      sendError.value = extractApiErrorMessage(e, 'Не удалось изменить сообщение')
    } finally {
      isSending.value = false
    }
    return
  }

  isSending.value = true
  sendError.value = ''
  try {
    await props.send(text, attachmentIds, replyingTo.value?.id ?? null)
    replyingTo.value = null
    composer.value?.reset()
  } catch (e) {
    // Черновик не очищаем — чтобы можно было отправить ещё раз.
    sendError.value = extractApiErrorMessage(e, 'Не удалось отправить сообщение')
  } finally {
    isSending.value = false
  }
}

function startEdit(message: Message) {
  replyingTo.value = null
  editing.value = message
  sendError.value = ''
}

function cancelEdit() {
  editing.value = null
  composer.value?.reset()
}

function onRemove(message: Message) {
  pendingRemoval.value = message
}

async function confirmRemove() {
  const message = pendingRemoval.value
  if (!message || isRemoving.value) return

  isRemoving.value = true
  sendError.value = ''
  try {
    await deleteMessage(props.chat.id, message.id)
    if (editing.value?.id === message.id) cancelEdit()
    if (replyingTo.value?.id === message.id) replyingTo.value = null
  } catch (e) {
    sendError.value = extractApiErrorMessage(e, 'Не удалось удалить сообщение')
  } finally {
    pendingRemoval.value = null
    isRemoving.value = false
  }
}

async function jumpTo(message: Message) {
  const found = await loadUntil(props.chat.id, message.id)
  if (!found) return

  await nextTick()
  const target = feed.value?.querySelector(`[data-message-id="${message.id}"]`)
  target?.scrollIntoView({ block: 'center', behavior: 'smooth' })

  highlightedId.value = message.id
  clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => (highlightedId.value = null), 2000)
}

const pinnedToBottom = ref(true)
let feedObserver: ResizeObserver | null = null

function onScroll() {
  const el = feed.value
  if (!el) return

  closeMessageMenu()
  pinnedToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 90
  if (el.scrollTop < 40) emit('loadOlder')
}

onMounted(() => {
  if (!feed.value || typeof ResizeObserver === 'undefined') return

  feedObserver = new ResizeObserver(() => {
    if (pinnedToBottom.value && feed.value) feed.value.scrollTop = feed.value.scrollHeight
  })
  for (const child of Array.from(feed.value.children)) feedObserver.observe(child)
})

watch(groups, async () => {
  if (!feedObserver || !feed.value) return
  await nextTick()
  feedObserver.disconnect()
  for (const child of Array.from(feed.value.children)) feedObserver.observe(child)
})

onBeforeUnmount(() => {
  feedObserver?.disconnect()
  clearInterval(pinTimer)
})

onBeforeUnmount(() => clearTimeout(highlightTimer))

/** Новое сообщение внизу — прокручиваем к нему; старые подгрузились сверху — держим позицию. */
watch(
  () => ({
    chatId: props.chat.id,
    count: props.messages.length,
    firstId: props.messages[0]?.id,
  }),
  async (next, prev) => {
    const el = feed.value
    const prependedOlder =
      next.chatId === prev?.chatId &&
      prev.count > 0 &&
      next.count > prev.count &&
      next.firstId !== prev.firstId
    if (!el || !prependedOlder) return scrollToBottom()

    const fromBottom = el.scrollHeight - el.scrollTop
    await nextTick()
    el.scrollTop = el.scrollHeight - fromBottom
  },
)

watch(
  () => props.chat.id,
  () => {
    sendError.value = ''
    editing.value = null
    replyingTo.value = null
    forwarding.value = null
    messageMenu.value = null
    pinFlow.value = null
    pinnedIndex.value = 0
    searchOpen.value = false
    membersOpen.value = false
    scrollToBottom()
  },
  { immediate: true },
)
</script>

<template>
  <section class="dialog">
    <header class="dialog__head">
      <button type="button" class="dialog__back" aria-label="К списку чатов" @click="emit('back')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 5l-7 7 7 7" />
        </svg>
      </button>

      <span class="dialog__avatar">
        <ChatSavedIcon v-if="chat.isSaved" />
        <ChatGroupIcon v-else-if="chat.type === 'group'" />
        <ChatNotificationsIcon v-else-if="isNotifications" />
        <UserAvatar v-else :url="chat.avatarUrl" :initials="chat.initials" />
        <span v-if="online" class="dialog__online" />
      </span>
      <span class="dialog__ident">
        <span class="dialog__title">{{ chat.title }}</span>
        <span v-if="chat.isSaved" class="dialog__status">заметки для себя</span>
        <span v-else-if="isNotifications" class="dialog__status">только для чтения</span>
        <span v-else-if="chat.type === 'group'" class="dialog__status">
          {{ memberCountLabel }}
        </span>
        <span v-if="typing" class="dialog__status is-active">{{ typingLabel }}…</span>
        <span v-else-if="online" class="dialog__status is-active">в сети</span>
      </span>

      <button
        v-if="chat.type === 'group'"
        type="button"
        class="dialog__tool"
        :class="{ 'is-active': membersOpen }"
        aria-label="Участники группы"
        @click="membersOpen = true"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      </button>

      <button
        type="button"
        class="dialog__tool"
        :class="{ 'is-active': searchOpen }"
        aria-label="Поиск по сообщениям"
        @click="searchOpen = !searchOpen"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
      </button>
    </header>

    <div v-if="currentPin" class="pinned">
      <button
        type="button"
        class="pinned__main"
        aria-label="Перейти к закреплённому сообщению"
        @click="onPinnedClick"
      >
        <span v-if="pinned.length > 1" class="pinned__track" aria-hidden="true">
          <i
            v-for="(item, index) in pinned"
            :key="item.id"
            :class="{ 'is-current': index === pinnedIndex }"
          />
        </span>
        <span class="pinned__text">
          <span class="pinned__label">
            Закреплённое сообщение
            <template v-if="pinned.length > 1">#{{ pinnedIndex + 1 }}</template>
            <span v-if="currentPin.pinScope === 'me' && !chat.isSaved" class="pinned__scope">
              только у вас
            </span>
          </span>
          <span class="pinned__body">{{ previewText(currentPin) }}</span>
        </span>
      </button>
      <button
        type="button"
        class="pinned__close"
        aria-label="Открепить"
        title="Открепить"
        @click="startUnpin(currentPin)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 6 6 18" />
          <path d="M6 6l12 12" />
        </svg>
      </button>
    </div>

    <ChatMessageSearch v-if="searchOpen" :chat-id="chat.id" @jump="jumpTo" />

    <div ref="feed" class="dialog__feed" @scroll="onScroll">
      <div v-for="group in groups" :key="group.key" class="dialog__group">
        <div class="dialog__date">
          <span class="dialog__date-label">{{ group.date }}</span>
        </div>

        <ChatMessage
          v-for="message in group.items"
          :key="message.id"
          :message="message"
          :own="message.senderId === meId"
          :initials="senderInitials(message.senderId)"
          :avatar-url="senderAvatar(message.senderId)"
          :author-name="isGroup ? senderName(message.senderId) : undefined"
          :read="chatStore.isMessageRead(message)"
          :hide-status="chat.isSaved"
          :highlighted="highlightedId === message.id"
          :quote="quoteFor(message)"
          :forwarded-from="forwardedName(message)"
          :can-reply="!isNotifications"
          @edit="startEdit(message)"
          @remove="onRemove(message)"
          @reply="startReply(message)"
          @jump-reply="jumpToReply(message)"
          @menu="(x, y) => openMessageMenu(message, x, y)"
        />
      </div>

      <p v-if="loadError" class="dialog__no-messages is-error">{{ loadError }}</p>
      <p v-else-if="!messages.length && chat.isSaved" class="dialog__no-messages">
        Сохраняйте сюда заметки, ссылки и файлы — их видите только вы.
      </p>
      <p v-else-if="!messages.length" class="dialog__no-messages">
        Сообщений пока нет — напишите первым.
      </p>
    </div>

    <p v-if="typing" class="dialog__typing">
      {{ typingLabel }}
      <span class="dialog__dots" aria-hidden="true"><i /><i /><i /></span>
    </p>

    <p v-if="sendError" class="dialog__error">{{ sendError }}</p>

    <p v-if="isNotifications" class="dialog__readonly">
      Это системный чат с уведомлениями — отправка сообщений недоступна.
    </p>
    <ChatComposer
      v-else
      ref="composer"
      :chat-id="chat.id"
      :editing="editing"
      :reply-to="replyPreview"
      :busy="isSending"
      @submit="onSubmit"
      @cancel-edit="cancelEdit"
      @cancel-reply="replyingTo = null"
      @typing="emit('typing')"
    />

    <ChatGroupMembers v-if="membersOpen" :chat="chat" @close="membersOpen = false" />

    <ChatDeleteConfirm
      :open="!!pendingRemoval"
      :busy="isRemoving"
      @confirm="confirmRemove"
      @cancel="pendingRemoval = null"
    />

    <ChatPinScopeDialog
      :mode="pinFlow?.mode ?? null"
      :busy="isPinning"
      @choose="onPinScope"
      @cancel="pinFlow = null"
    />

    <ChatForwardPicker
      v-if="forwarding"
      :message="forwarding"
      @close="forwarding = null"
      @forwarded="onForwarded"
    />

    <Teleport to="body">
      <Transition name="message-menu">
        <div
          v-if="messageMenu && menuItems.length"
          ref="messageMenuRoot"
          class="message-menu"
          role="menu"
          :style="{ left: `${messageMenu.x}px`, top: `${messageMenu.y}px` }"
        >
          <button
            v-for="item in menuItems"
            :key="item.key"
            type="button"
            class="message-menu__item"
            :class="{ 'is-danger': item.key === 'remove' }"
            role="menuitem"
            @click="onMessageMenuAction(item.key)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path
                v-if="item.key === 'reply'"
                d="M10 9V5l-7 7 7 7v-4.1c5 0 8.5 1.6 11 5.1-1-5-4-10-11-11z"
              />
              <path
                v-else-if="item.key === 'forward'"
                d="M14 9V5l7 7-7 7v-4.1c-5 0-8.5 1.6-11 5.1 1-5 4-10 11-11z"
              />
              <template v-else-if="item.key === 'pin' || item.key === 'unpin'">
                <path d="M9 4h6l-1 6 3 3H7l3-3z" />
                <path d="M12 13v7" />
                <path v-if="item.key === 'unpin'" d="M4 4l16 16" />
              </template>
              <template v-else-if="item.key === 'edit'">
                <path d="M4 20h4L19 9l-4-4L4 16v4z" />
                <path d="M14 5l4 4" />
              </template>
              <template v-else>
                <path d="M4 7h16" />
                <path d="M9 7V4h6v3" />
                <path d="M6 7l1 13h10l1-13" />
              </template>
            </svg>
            {{ item.label }}
          </button>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.dialog {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: var(--color-ground);
}

.dialog__head {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 72px;
  flex: none;
  padding: 0 20px;
  background: var(--color-lift);
  border-bottom: 1px solid var(--chat-line);
}

.dialog__back {
  display: none;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
}

.dialog__back svg {
  width: 18px;
  height: 18px;
}

.dialog__avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex: none;
  background: var(--color-surface);
  border: 1px solid var(--chat-accent-soft);
  border-radius: var(--chat-radius);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-accent);
}

.dialog__online {
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

.dialog__ident {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.dialog__status {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.dialog__status.is-active {
  color: var(--color-focus);
}

.dialog__title {
  overflow: hidden;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 17px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog__tool {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex: none;
  padding: 0;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--chat-radius);
  color: var(--color-text-muted);
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}

.dialog__tool:hover:not(:disabled),
.dialog__tool.is-active {
  color: var(--color-accent);
  border-color: var(--chat-accent-soft);
}

.dialog__tool svg {
  width: 20px;
  height: 20px;
}

.dialog__feed {
  flex: 1;
  overflow-y: auto;
  overflow-anchor: none;
  padding: 20px;
  background-image: var(--chat-grid);
  background-size: 48px 48px;
}

.dialog__group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog__date {
  display: flex;
  justify-content: center;
  margin: 10px 0 4px;
}

.dialog__date-label {
  padding: 5px 14px;
  background: var(--color-lift);
  border: 1px solid var(--chat-line);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-text-muted);
}

.dialog__no-messages {
  margin: 24px 0;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.dialog__no-messages.is-error {
  color: var(--color-error);
}

.dialog__typing {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  margin: 0;
  padding: 0 20px 8px 62px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-focus);
}

.dialog__dots {
  display: inline-flex;
  gap: 4px;
}

.dialog__dots i {
  width: 5px;
  height: 5px;
  background: var(--color-focus);
  border-radius: 50%;
  animation: dialog-dot 1.2s infinite ease-in-out;
}

.dialog__dots i:nth-child(2) {
  animation-delay: 0.15s;
}

.dialog__dots i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes dialog-dot {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }

  40% {
    opacity: 1;
  }
}

.dialog__error {
  margin: 0;
  flex: none;
  padding: 6px 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-error);
}

.dialog__readonly {
  margin: 0;
  flex: none;
  padding: 14px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  border-top: 1px solid rgba(61, 79, 156, 0.6);
}

@media (max-width: 900px) {
  .dialog__back {
    display: flex;
  }

  .dialog__feed {
    padding-inline: 14px;
  }
}

.pinned {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  padding: 8px 14px 8px 20px;
  background: var(--color-lift);
  border-bottom: 1px solid var(--chat-line);
}

.pinned__main {
  display: flex;
  align-items: stretch;
  gap: 10px;
  flex: 1;
  min-width: 0;
  padding: 2px 0;
  background: none;
  border: none;
  border-left: 3px solid var(--color-accent);
  text-align: left;
  cursor: pointer;
}

.pinned__main:has(.pinned__track) {
  border-left: none;
}

.pinned__track {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 3px;
  flex: none;
}

.pinned__track i {
  flex: 1;
  background: var(--chat-accent-soft);
  border-radius: 2px;
}

.pinned__track i.is-current {
  background: var(--color-accent);
}

.pinned__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding-left: 8px;
}

.pinned__main:has(.pinned__track) .pinned__text {
  padding-left: 0;
}

.pinned__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-accent);
}

.pinned__scope {
  padding: 1px 7px;
  border: 1px solid var(--chat-line);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-weight: 400;
  font-size: 10px;
  color: var(--color-text-dim);
}

.pinned__body {
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pinned__close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--chat-radius);
  color: var(--color-text-dim);
  cursor: pointer;
}

.pinned__close:hover {
  background: var(--color-surface);
  color: var(--color-accent);
}

.pinned__close svg {
  width: 16px;
  height: 16px;
}

.message-menu {
  position: fixed;
  z-index: 150;
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 200px;
  padding: 6px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: 14px;
  box-shadow: var(--shadow-hard);
}

.message-menu__item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 12px;
  background: none;
  border: none;
  border-radius: 10px;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}

.message-menu__item:hover {
  background: var(--color-surface);
  color: var(--color-accent);
}

.message-menu__item svg {
  width: 18px;
  height: 18px;
  flex: none;
  color: var(--color-accent);
}

.message-menu__item.is-danger,
.message-menu__item.is-danger svg,
.message-menu__item.is-danger:hover {
  color: var(--color-error);
}

.message-menu-enter-active,
.message-menu-leave-active {
  transition:
    opacity 0.14s ease,
    transform 0.14s ease;
}

.message-menu-enter-from,
.message-menu-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (prefers-reduced-motion: reduce) {
  .message-menu-enter-active,
  .message-menu-leave-active {
    transition: none;
  }
}
</style>
