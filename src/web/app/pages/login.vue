<script setup lang="ts">
const username = ref('')
const password = ref('')
</script>

<template>
  <div class="login">
    <h1>Вход</h1>
    <form class="login__form" @submit.prevent>
      <label>
        Логин
        <input v-model="username" type="text" autocomplete="username" />
      </label>
      <label>
        Пароль
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>
      <button type="submit">Войти</button>
    </form>
  </div>
</template>

<style scoped>
.login {
  max-width: 320px;
  margin: 64px auto;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-elevated);
}

.login__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: var(--text-muted);
}

input {
  padding: 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
}

button {
  margin-top: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--accent);
  color: white;
  cursor: pointer;
}
</style>
