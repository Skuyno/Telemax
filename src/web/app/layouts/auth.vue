<template>
  <div class="auth-layout">
    <slot />
  </div>
</template>

<style scoped>
.auth-layout {
  min-height: 100vh;
  background: radial-gradient(circle at 50% 20%, var(--color-ground) 0%, var(--color-void) 75%);
}
</style>
