<script setup lang="ts">
definePageMeta({ layout: false })

const chatStore = useChatStore()

const isNarrow = ref(false)
const showDialogOnNarrow = ref(false)

function onSelect() {
  showDialogOnNarrow.value = true
}

onMounted(() => {
  const media = window.matchMedia('(max-width: 900px)')
  isNarrow.value = media.matches
  media.addEventListener('change', (event) => {
    isNarrow.value = event.matches
  })
})

const showSidebar = computed(() => !isNarrow.value || !showDialogOnNarrow.value)
const showDialog = computed(() => !isNarrow.value || showDialogOnNarrow.value)
</script>

<template>
  <div class="chats">
    <ChatSidebar v-if="showSidebar" @select="onSelect" />

    <template v-if="showDialog">
      <ChatDialog
        v-if="chatStore.activeChat && chatStore.meId"
        :chat="chatStore.activeChat"
        :messages="chatStore.activeMessages"
        :me-id="chatStore.meId"
        @send="chatStore.sendMessage"
        @back="showDialogOnNarrow = false"
      />
      <ChatEmpty v-else :has-chats="chatStore.chats.length > 0" />
    </template>
  </div>
</template>

<style scoped>
.chats {
  display: flex;
  height: 100%;
  --chat-line: rgba(61, 79, 156, 0.6);
  --chat-line-soft: rgba(61, 79, 156, 0.5);
  --chat-accent-soft: rgba(255, 204, 46, 0.45);
}
</style>
