# Backlog — artem

Журнал крупных изменений, вносимых в рамках работы над проектом на ветке `artem`. Каждая запись — отдельная сессия/пачка изменений, от новой сверху нет — пишем вниз по хронологии.

---

## 2026-09-13 — Инициализация Nuxt-фронта

Создан фронтенд-проект (`Nuxt 4`) — изначально в `web/` в корне репозитория, позже перенесён в `src/web/` (правильное расположение).

- Стек: Nuxt 4, Vue 3, Pinia (`@pinia/nuxt`), VueUse (`@vueuse/nuxt`). Новые зависимости добавлялись только на этом, самом первом шаге — дальше действует правило не трогать `package.json` без необходимости и согласования.
- `nuxt.config.ts`: `runtimeConfig.public.apiBase` / `wsBase` — адреса api-gateway (`:8000`) и ws-gateway (`:4333`), настраиваются через `.env` (`NUXT_PUBLIC_API_BASE`, `NUXT_PUBLIC_WS_BASE`).
- Каркас:
  - `app/stores/auth.ts` — Pinia-стор с токенами и пользователем.
  - `app/stores/chat.ts` — заготовка под чаты/сообщения.
  - `app/composables/useApi.ts` — обёртка над `$fetch` с подстановкой `Authorization: Bearer` и разлогином+редиректом на `/login` при `401`.
  - `app/composables/useWs.ts` — подключение к ws-gateway.
  - `app/types/auth.ts`, `app/types/chat.ts` — базовые типы.
  - `app/layouts/default.vue`, `app/pages/index.vue` (тестовая страница с проверкой `/health`), `app/pages/login.vue` (первая, черновая версия формы).

---

## 2026-09-17 — Изучение auth-эндпоинтов бэкенда

Прочитан код `identity` и `api-gateway` (без изменений — только исследование, согласно правилу «бэкенд только изучаем»). Ключевые выводы, на которых строится вся auth-логика фронта:

- `POST /auth/register` — `{ username (3-32), password (8-256) }` → `201 { id }`; `409` если username занят.
- `POST /auth/login` — `{ username, password }` → `{ access_token, refresh_token, token_type }`; `401 Invalid credentials`.
- `POST /auth/refresh` — `{ refresh_token }` → новый `access_token`, тот же `refresh_token` (ротации нет).
- `GET /me` (Bearer) → `{ id, username, email, display_name, created_at }` — `email`/`display_name` сейчас всегда `null` (registration их не принимает).
- Токен шлётся как `Authorization: Bearer <access_token>`; gateway сам валидирует JWT (HS256), внутрь сервисов пробрасывает `X-User-Id`.
- Logout-эндпоинта и смены пароля нет — логаут только на клиенте (сброс токенов из стора).
- Только `GET`/`POST` проксируются gateway.

---

## 2026-09-17 — Дизайн-система и страница логина/регистрации

По макету («Вход» — тёмная синяя палитра, Unbounded/Space Grotesk/IBM Plex Mono, острые углы, жёсткие тени) сделано:

- **`app/assets/styles/`** — новая папка с токенами:
  - `colors.css` — все цвета из макета (`--color-ground`, `--color-lift`, `--color-accent`, `--color-error` и т.д.).
  - `fonts.css` — `--font-display` (Unbounded), `--font-heading` (Space Grotesk), `--font-mono` (IBM Plex Mono), `--radius: 0`, `--shadow-hard`.
  - `base.css` — глобальный reset/фон (заменил старый `app/assets/css/main.css`, который удалён).
  - Шрифты подключены через `<link>` на Google Fonts в `nuxt.config.ts` (`app.head.link`) — без новых npm-пакетов.
- **`app/layouts/auth.vue`** — отдельный layout без общей шапки, для страницы логина (полноэкранный фон с сеточным паттерном).
- **`app/pages/login.vue`** — полностью переписана под макет: логотип «Телемакс», слоган, карточка с вкладками «Войти / Регистрация», моно-лейблы капсом, амбер-кнопка.
- **Механизм авторизации**:
  - `app/composables/useAuth.ts` — `login()` и `register()` бьют в реальные `/auth/login` / `/auth/register`; после регистрации (она не возвращает токены) автоматически логинит и подтягивает `/me`.
  - `app/types/auth.ts` — обновлён под реальные поля бэкенда (`access_token`, `refresh_token`, `display_name` и т.п.).
  - `app/utils/apiError.ts` — разбор ошибок FastAPI (`detail` строкой или массивом 422-ошибок) для читаемых сообщений под полями формы.
- `app/layouts/default.vue`, `app/pages/index.vue` обновлены под новые цветовые токены (чтобы не остались битые ссылки на старые CSS-переменные).

---

## 2026-09-17 — Docker для фронта

- **`src/web/Dockerfile`** — двухэтапная сборка: `node:22-alpine` builder (`npm ci` + `npm run build`) → лёгкий рантайм-образ только с `.output`, запуск `node .output/server/index.mjs` на порту 3000.
- **`src/web/.dockerignore`** — исключает `node_modules`, `.nuxt`, `.output`, `.env` и т.д.
- **`deploy/docker-compose.yml`** — добавлен сервис `web` (билд из `../src/web`, порт `3000:3000`, `NUXT_PUBLIC_API_BASE`/`NUXT_PUBLIC_WS_BASE` из env хоста, зависит от `api-gateway`/`ws-gateway`).
  - Также исправлена проблема: файл содержал смешанные CRLF/LF окончания строк, из-за чего редактор ругался на `DUPLICATE_KEY` — файл приведён к единому CRLF.

---

## 2026-09-17 — Тестовое окружение: `.env` и `docker-compose-local.yml`

Настроены `.env`-файлы для локального теста (везде используются одни и те же тестовые креды, JWT_SECRET синхронизирован между identity/api-gateway/ws-gateway — иначе валидация токена молча ломается):

- `deploy/.env`, `src/services/identity/.env`, `src/services/communication/.env`, `src/services/api-gateway/.env`, `src/services/ws-gateway/.env`, `src/web/.env`.

`deploy/docker-compose-local.yml` (гитигнорится по паттерну `docker-compose*.yml`, локальный оверрайд для конкретного хоста) — подобраны свободные внешние порты, т.к. на хосте уже заняты `5000`, `8000`, `5432`:

- `api-gateway`: `8080:8000` (было `5000:8000` — конфликт)
- `db`: добавлен `5433:5432` (для удобного подключения GUI-клиентом; `5432` занят локальным postgres)
- `ws-gateway`: `4333:4333` — без изменений
- `web`: `3000:3000` — без изменений, `NUXT_PUBLIC_API_BASE` указывает на `http://localhost:8080`

---

## 2026-09-17 — Разовое исключение: CORS в api-gateway

Обнаружено, что форма логина/регистрации не работает: браузер шлёт preflight `OPTIONS /auth/register`, gateway отвечает `405` (роут заявлен только для `GET`/`POST`, `CORSMiddleware` отсутствовал вовсе) — запрос обрывается ещё до отправки `POST`. Это блокирует любую работу фронта с API, а обойти CORS-preflight с фронта невозможно (ограничение браузера).

**По явному разовому разрешению пользователя** внесена **только эта одна правка** в бэкенд:
- `src/services/api-gateway/app/main.py` — добавлен `CORSMiddleware` (`allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`, без `allow_credentials`, т.к. авторизация через Bearer-токен, а не cookies).

Больше никаких изменений в `src/services/*` не вносилось и не планируется без отдельного согласования.

---

## 2026-09-17 — Роутинг после авторизации, шестерёнка настроек

- **`app/middleware/auth.global.ts`** — глобальный редирект: неавторизованный пользователь на любой странице → `/login`; авторизованный на `/login` → `/`. Сессия пока не персистентна (стор in-memory, сбрасывается по F5) — как только добавим сохранение сессии (localStorage/refresh-flow), поведение «сразу открывается главная» заработает само собой, без правок middleware.
- **`app/pages/index.vue`** — упрощена до чистого полотна (фон `--color-ground`), весь тестовый контент (проверка `/health`, конфиг, статус авторизации) убран.
- **`app/layouts/default.vue`** — в шапку справа добавлена иконка-шестерёнка (SVG), ссылка на `/settings`, подсветка акцентным цветом при наведении.
- **`app/pages/settings.vue`** — новая пустая страница настроек, тот же стиль полотна, что и на главной.
- **`app/stores/settings.ts`** + **`app/types/settings.ts`** — заготовка индивидуальных настроек пользователя: `byUserId: Record<string, UserSettings>`, геттер `current` берёт настройки текущего юзера (`authStore.user.id`) с дефолтами. Пока один плейсхолдер-параметр `theme`; будет расширяться по мере проектирования UI настроек.

---

## Правила, установленные пользователем по ходу работы

- Работаем только над фронтендом (`src/web/`); бэкенд — только для изучения контрактов API, не редактируем без явного разового разрешения.
- Не добавлять/обновлять npm-зависимости без необходимости и согласования.
- После крупных изменений — вести и дополнять этот файл (`BACKLOG-artem.md`).
