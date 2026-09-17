<script setup lang="ts">
const config = useRuntimeConfig()
const api = useApi()
const auth = useAuthStore()

const status = ref<'idle' | 'checking' | 'ok' | 'error'>('idle')
const errorMessage = ref('')

async function checkApi() {
  status.value = 'checking'
  errorMessage.value = ''
  try {
    await api('/health')
    status.value = 'ok'
  } catch (e) {
    status.value = 'error'
    errorMessage.value = e instanceof Error ? e.message : 'Unknown error'
  }
}
</script>

<template>
  <div class="home">
    <h1>Telemax Frontend</h1>
    <p>Nuxt-заготовка для клиента. Каркас: Pinia store, API/WS composables, runtime config.</p>

    <section class="card">
      <h2>Конфигурация окружения</h2>
      <ul>
        <li>API base: <code>{{ config.public.apiBase }}</code></li>
        <li>WS base: <code>{{ config.public.wsBase }}</code></li>
      </ul>
    </section>

    <section class="card">
      <h2>Авторизация</h2>
      <p v-if="auth.isAuthenticated">
        Вы вошли как <strong>{{ auth.user?.username }}</strong>
      </p>
      <p v-else>
        Вы не авторизованы. <NuxtLink to="/login">Перейти на страницу входа</NuxtLink>
      </p>
    </section>

    <section class="card">
      <h2>Проверка связи с api-gateway</h2>
      <button @click="checkApi">Проверить /health</button>
      <p v-if="status === 'checking'">Проверяем...</p>
      <p v-else-if="status === 'ok'">✅ api-gateway отвечает</p>
      <p v-else-if="status === 'error'">
        ❌ Ошибка: {{ errorMessage }} (это ожидаемо, если backend не запущен)
      </p>
    </section>
  </div>
</template>

<style scoped>
.home {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 16px;
  font-family: var(--font-mono);
}

h1 {
  font-family: var(--font-heading);
}

.card {
  margin-top: 24px;
  padding: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius);
  background: var(--color-lift);
}

a {
  color: var(--color-accent);
}

button {
  padding: 8px 16px;
  border-radius: var(--radius);
  border: none;
  background: var(--color-accent);
  color: var(--color-ink);
  font-family: var(--font-display);
  font-weight: 700;
  cursor: pointer;
}

button:hover {
  background: var(--color-accent-hover);
}
</style>
