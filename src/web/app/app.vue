<script setup lang="ts">
const route = useRoute()
const auth = useAuthStore()

// Chats stay mounted across "/" and "/settings" so opening settings never
// unmounts the chats screen underneath — settings renders as an overlay
// on top of it instead, driven purely by the current route path.
// /administration/* are real standalone pages, not an overlay, so chats
// must NOT render underneath them (unlike /settings).
const showChats = computed(
  () =>
    auth.isAuthenticated &&
    route.path !== '/login' &&
    !route.path.startsWith('/administration'),
)
const showSettings = computed(() => route.path === '/settings')
</script>

<template>
  <ChatsScreen v-if="showChats" />
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
  <Transition name="settings-modal">
    <SettingsModal v-if="showSettings" />
  </Transition>
</template>
