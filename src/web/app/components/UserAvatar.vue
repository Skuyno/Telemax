<script setup lang="ts">
const props = defineProps<{ url?: string | null; initials: string }>()

const src = useAvatarSrc(() => props.url)
</script>

<template>
  <img v-if="src" class="user-avatar" :src="src" alt="" />
  <template v-else>{{ initials }}</template>
</template>

<style scoped>
.user-avatar {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}
</style>
