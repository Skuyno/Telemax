<template>
  <span class="saved" aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M6 3h12v18l-6-4.5L6 21z" />
    </svg>
  </span>
</template>

<style scoped>
.saved {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--color-accent);
}

.saved svg {
  width: 45%;
  height: 45%;
}
</style>
