<script setup lang="ts">
definePageMeta({ layout: false, middleware: 'administration' })
</script>

<template>
  <div class="admin-page">
    <header class="admin-page__head">
      <NuxtLink to="/" class="admin-page__back" aria-label="Назад к чатам">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </NuxtLink>
      <h1 class="admin-page__title">Администрирование</h1>
    </header>

    <div class="admin-page__body">
      <NuxtLink to="/administration/users" class="admin-card">
        <span class="admin-card__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </span>
        <span class="admin-card__text">
          <span class="admin-card__name">Управление пользователями</span>
          <span class="admin-card__hint">Создание аккаунтов администраторов и пользователей</span>
        </span>
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--color-ground);
}

.admin-page__head {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 72px;
  padding: 0 28px;
  border-bottom: 1px solid var(--color-line);
}

.admin-page__back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--color-text-muted);
  transition: color 0.15s ease;
}

.admin-page__back:hover {
  color: var(--color-accent);
}

.admin-page__back svg {
  width: 20px;
  height: 20px;
}

.admin-page__title {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 20px;
  color: var(--color-text);
}

.admin-page__body {
  padding: 28px;
}

.admin-card {
  display: flex;
  align-items: center;
  gap: 18px;
  max-width: 420px;
  padding: 20px;
  background: var(--color-lift);
  border: 1px solid var(--color-line);
  border-radius: var(--radius);
  transition: border-color 0.15s ease;
}

.admin-card:hover {
  border-color: var(--color-accent);
}

.admin-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex: none;
  background: var(--color-surface);
  border-radius: var(--radius);
  color: var(--color-accent);
}

.admin-card__icon svg {
  width: 24px;
  height: 24px;
}

.admin-card__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.admin-card__name {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 15px;
  color: var(--color-text);
}

.admin-card__hint {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
