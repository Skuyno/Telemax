<template>
  <div class="layout">
    <header class="layout__header">
      <span class="layout__logo">Телемакс</span>
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
  background: var(--color-lift);
  border-bottom: 1px solid var(--color-line);
}

.layout__logo {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-accent);
}

.layout__content {
  flex: 1;
  display: flex;
}
</style>
