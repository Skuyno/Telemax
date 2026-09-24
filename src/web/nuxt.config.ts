// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: ['@pinia/nuxt', '@vueuse/nuxt'],

  css: [
    '~/assets/styles/colors.css',
    '~/assets/styles/fonts.css',
    '~/assets/styles/base.css',
  ],

  app: {
    head: {
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Unbounded:wght@700&family=Space+Grotesk:wght@600&family=IBM+Plex+Mono:wght@400;500&display=swap',
        },
      ],
    },
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      // С путём /ws: ws-gateway слушает только его, корень отвечает 404.
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || 'ws://localhost:4333/ws',
      // На проде можно закрыть самостоятельную регистрацию (только вход
      // по уже выданным учёткам) — по умолчанию открыта, как сейчас.
      authNewUser: process.env.NUXT_PUBLIC_AUTH_NEW_USER !== 'false',
    },
  },
})
