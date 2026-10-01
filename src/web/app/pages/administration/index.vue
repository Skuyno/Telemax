<script setup lang="ts">
definePageMeta({ layout: false, middleware: 'administration' })

const orbit = [
  { icon: 'shield', tone: 'accent', angle: -90, radius: 150, size: 44 },
  { icon: 'profile', tone: 'signal', angle: -30, radius: 150, size: 44 },
  { icon: 'user', tone: 'neutral', angle: 30, radius: 150, size: 44 },
  { icon: 'key', tone: 'accent', angle: 90, radius: 150, size: 44 },
  { icon: 'at', tone: 'signal', angle: 150, radius: 150, size: 44 },
  { icon: 'user', tone: 'neutral', angle: 210, radius: 150, size: 44 },
  { icon: 'add', tone: 'signal', angle: 180, radius: 95, size: 34 },
  { icon: 'lock', tone: 'signal', angle: 0, radius: 95, size: 34 },
] as const
</script>

<template>
  <div class="tmx-page">
    <AdminHeader title="Администрирование" icon="shield" highlight back="/" />

    <main class="wrap">
      <NuxtLink to="/administration/users" class="hero">
        <div class="hero-text">
          <span class="hero-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </span>
          <div>
            <h2>Управление<br />пользователями</h2>
            <p>Создание аккаунтов администраторов и пользователей</p>
          </div>
          <span class="btn-primary">
            Открыть
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M5 12h14" />
              <path d="M13 6l6 6-6 6" />
            </svg>
          </span>
        </div>

        <div class="hero-art" aria-hidden="true">
          <span class="glow" />
          <span class="ring ring-lg" />
          <span class="ring ring-sm" />
          <span class="core">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <circle cx="9" cy="8" r="3.4" />
              <path d="M3.5 19a5.5 5.5 0 0 1 11 0z" />
              <circle cx="16.5" cy="9" r="2.6" />
              <path d="M13 19a4.4 4.4 0 0 1 8 0z" />
            </svg>
          </span>
          <AdminOrbitTile v-for="(tile, index) in orbit" :key="index" v-bind="tile" />
        </div>
      </NuxtLink>
    </main>
  </div>
</template>

<style scoped>
.tmx-page {
  position: relative;
  min-height: 100vh;
  background: radial-gradient(900px 520px at 80% -10%, #1a2668 0%, #101a49 45%, var(--color-ink) 100%);
}

.tmx-page::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(120, 150, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 150, 255, 0.05) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(to bottom, transparent 30%, #000);
}

.wrap {
  position: relative;
  display: grid;
  place-items: center;
  min-height: calc(100vh - 76px);
  padding: 44px 36px;
}

.wrap > * {
  width: 100%;
  max-width: 1000px;
}

.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  min-height: 300px;
  overflow: hidden;
  background:
    linear-gradient(120deg, var(--color-surface) 0%, rgba(24, 36, 96, 0.16) 100%),
    var(--color-lift);
  border-radius: 20px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 204, 46, 0.28),
    0 24px 60px rgba(0, 0, 0, 0.45);
  color: inherit;
  text-decoration: none;
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.hero:hover {
  box-shadow:
    inset 0 0 0 1px rgba(255, 204, 46, 0.5),
    0 24px 60px rgba(0, 0, 0, 0.45);
  transform: translateY(-2px);
}

.hero:hover .btn-primary {
  background: var(--color-accent-hover);
}

.hero-text {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 22px;
  padding: 40px;
}

.hero-icon {
  display: grid;
  place-items: center;
  width: 60px;
  height: 60px;
  background: rgba(255, 204, 46, 0.14);
  border-radius: 17px;
  box-shadow: inset 0 0 0 1px rgba(255, 204, 46, 0.35);
  color: var(--color-accent);
}

.hero-icon svg {
  width: 28px;
  height: 28px;
}

h2 {
  margin: 0;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 28px;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

p {
  max-width: 340px;
  margin: 10px 0 0;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.65;
  color: var(--color-text-muted);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  align-self: flex-start;
  height: 46px;
  padding: 0 20px;
  background: var(--color-accent);
  border-radius: 12px;
  box-shadow: 0 10px 26px rgba(255, 204, 46, 0.28);
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 14px;
  color: var(--color-ink);
  transition: background 0.15s ease;
}

.btn-primary svg {
  width: 17px;
  height: 17px;
}

.hero-art {
  position: relative;
  overflow: hidden;
}

.glow,
.ring,
.core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.glow {
  width: 520px;
  height: 520px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(255, 204, 46, 0.18) 0%,
    rgba(255, 204, 46, 0.04) 35%,
    transparent 60%
  );
}

.ring {
  border-radius: 50%;
}

.ring-lg {
  width: 300px;
  height: 300px;
  box-shadow: inset 0 0 0 1px rgba(255, 204, 46, 0.22);
}

.ring-sm {
  width: 190px;
  height: 190px;
  box-shadow: inset 0 0 0 1px rgba(79, 216, 255, 0.25);
}

.core {
  display: grid;
  place-items: center;
  width: 84px;
  height: 84px;
  background: linear-gradient(140deg, var(--color-accent), var(--color-accent-pressed));
  border-radius: 24px;
  box-shadow: 0 0 50px rgba(255, 204, 46, 0.45);
  color: var(--color-ink);
}

.core svg {
  width: 38px;
  height: 38px;
}

@media (max-width: 860px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .hero-art {
    display: none;
  }

  .wrap {
    padding: 24px 16px;
  }
}
</style>
