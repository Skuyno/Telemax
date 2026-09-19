<script setup lang="ts">
defineProps<{
  modelValue: boolean
  label: string
  hint?: string
  disabled?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()
</script>

<template>
  <label class="toggle-row" :class="{ 'is-disabled': disabled }">
    <span class="toggle-row__text">
      <span class="toggle-row__label">{{ label }}</span>
      <span v-if="hint" class="toggle-row__hint">{{ hint }}</span>
    </span>
    <span
      class="toggle-row__switch"
      :class="{ 'is-on': modelValue }"
      role="switch"
      :aria-checked="modelValue"
    >
      <input
        type="checkbox"
        class="toggle-row__input"
        :checked="modelValue"
        :disabled="disabled"
        @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
      />
      <span class="toggle-row__thumb" />
    </span>
  </label>
</template>

<style scoped>
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 0;
  cursor: pointer;
}

.toggle-row.is-disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.toggle-row__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toggle-row__label {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 15px;
  color: var(--color-text);
}

.toggle-row__hint {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.toggle-row__switch {
  position: relative;
  flex: none;
  width: 52px;
  height: 28px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}

.toggle-row__switch.is-on {
  background: var(--color-accent);
  border-color: var(--color-accent);
}

.toggle-row__input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.toggle-row__thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: var(--color-text-dim);
  transition:
    transform 0.15s ease,
    background 0.15s ease;
}

.toggle-row__switch.is-on .toggle-row__thumb {
  background: var(--color-ink);
  transform: translateX(24px);
}

.toggle-row:focus-within .toggle-row__switch {
  outline: 1px solid var(--color-focus);
  outline-offset: 2px;
}
</style>
