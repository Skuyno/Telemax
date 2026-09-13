<script setup lang="ts">
const config = useRuntimeConfig()
const api = useApi()

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
}

.card {
  margin-top: 24px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-elevated);
}

button {
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--accent);
  color: white;
  cursor: pointer;
}
</style>
