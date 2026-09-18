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
  padding: 14px 0;
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
  font-size: 14px;
  color: var(--color-text);
}

.toggle-row__hint {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-dim);
}

.toggle-row__switch {
  position: relative;
  flex: none;
  width: 40px;
  height: 22px;
  background: var(--color-ground);
  border: 1px solid var(--color-line);
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
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: var(--color-text);
  transition: transform 0.15s ease;
}

.toggle-row__switch.is-on .toggle-row__thumb {
  background: var(--color-ink);
  transform: translateX(18px);
}
</style>
