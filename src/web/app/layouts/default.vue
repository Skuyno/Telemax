<template>
  <div class="layout">
    <header class="layout__header">
      <span class="layout__logo">Telemax</span>
    </header>
    <main class="layout__content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.layout__header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}

.layout__logo {
  font-weight: 600;
  letter-spacing: 0.02em;
}

.layout__content {
  flex: 1;
  display: flex;
}
</style>
