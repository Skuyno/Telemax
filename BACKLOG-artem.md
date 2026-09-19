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

## 2026-09-18 — Синхронизация с `dev`

`origin/dev` подтянула страницу личных чатов от `ksenia` (компоненты `chat/*`, `stores/chat.ts`, `index.vue` как экран чатов). Смержено в `artem` без конфликтов; наши файлы (шестерёнка настроек, `middleware/auth.global.ts`, `stores/settings.ts`) не задеты — `index.vue` теперь чужая страница чатов с `layout: false`, это ожидаемо.

---

## 2026-09-18 — API для настроек (второе разовое исключение на бэкенд)

По итогам обсуждения с командой (см. переписку с бэкенд-разработчиком max) решили не заводить отдельный сервис настроек, а разложить их по сервисам-владельцам сущностей: глобальные настройки — в `identity`, настройки чата — в `communication`, как отдельные независимые модули (не смешивая с `users/`/`chats/`). **По явному разрешению пользователя** реализовано полностью (4 коммита, каждый — по конвенции типов из корневого `README.md`):

- **`feat: add user settings endpoint to identity`** — новый модуль `src/services/identity/app/settings/` (`models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`), таблица `user_settings` (1:1 с `users` по `user_id`, поля `notifications_enabled`, `accept_calls`). Эндпоинты `GET/PATCH /me/settings`, авторизация через тот же `X-User-Id`, что и `/me`. Миграция `deac91b0f3e7_add_user_settings_table.py`.
- **`feat: add chat settings module to communication`** — аналогичный модуль `src/services/communication/app/settings/`, отдельная таблица `chat_settings` (composite PK `chat_id + user_id`, поле `notifications_muted`) — намеренно **не** колонка в `ChatMember`, чтобы `chats/` остался только про чаты/сообщения. Единственная точка связи двух модулей — вызов `chats_repository.is_user_in_chat()` из `settings/service.py` для проверки членства (403, если чат чужой). Эндпоинты `GET/PATCH /chats/{chat_id}/settings`. Миграция `d5d6506f04e2_add_chat_settings_table.py`.
- **`feat: route /me/settings and PATCH through api-gateway`** — в `api-gateway/app/router.py` два фикса: `resolve_target` теперь маршрутизирует по сегменту `"me"` (а не точному совпадению `path == "me"`), иначе `/me/settings` не находил сервис; в проксирующий роут добавлен метод `PATCH` (был только `GET`/`POST` — иначе `PATCH` ловил бы тот же `405`, что раньше ловил `OPTIONS` до CORS-фикса).
- **`docs: document settings endpoints in identity and communication README`** — обе таблицы HTTP API дополнены новыми строками.

**Проверено end-to-end** через `docker-compose-local.yml` (docker compose up, реальные HTTP-запросы через gateway): регистрация → логин → `GET/PATCH /me/settings` (дефолт создаётся при первом обращении, патч сохраняется) → создание чата между двумя пользователями → `GET/PATCH /chats/{id}/settings` → проверка 403 на чужом чате. Всё отработало корректно.

Заодно поправил свой локальный `docker-compose-local.yml` (не коммитится, gitignore): у `api-gateway` порты нужно объявлять как `ports: !override`, иначе compose **склеивает** список портов с базовым файлом и остаётся конфликтующий `8000:8000` — та же проблема, о которой писала `ksenia` в своём бэклоге.

---

## 2026-09-18 — Модалка настроек и подключение к API

- **`feat: open settings as a URL-driven modal over the chats screen`** — экран чатов вынесен из `pages/index.vue` в `components/ChatsScreen.vue`, рендерится напрямую в `app.vue` пока пользователь авторизован (не через `<NuxtPage>`), поэтому переход на `/settings` его не размонтирует. `index.vue`/`settings.vue` стали пустыми точками роутинга. Новый `components/SettingsModal.vue` — оверлей 80vw×90vh по центру, крестик закрытия, закрытие кликом по подложке, лёгкое затемнение фона, своя шапка «НАСТРОЙКИ» в стиле сайдбара чатов. Удалён неиспользуемый `layouts/default.vue` (дублировал шестерёнку, которая теперь только в `ChatSidebar.vue`).
- **`feat: wire settings modal to GET/PATCH /me/settings`** — реальное содержимое модалки: карточка профиля (username + дата регистрации из `/me`), два тумблера (`notifications_enabled`, `accept_calls`) через новый `composables/useSettings.ts`, кнопка «Выйти» (чисто клиентский логаут). `stores/settings.ts` упрощён до одного снапшота текущего юзера (раньше был `byUserId`-словарь-заглушка с несуществующим полем `theme`).
- Проверено вживую через Playwright (реальный Chrome, т.к. `chromium-cli`/автозагрузка браузера playwright недоступны в этом окружении — сеть режет скачивание) на полном стеке в докере: регистрация → тумблер → закрытие/переоткрытие модалки → значение осталось (сохранилось на сервере) → логаут.
- PR с этой пачкой (плюс API настроек) был смёржен в `dev` (PR #10 «Страница настроек»). После пуша CI (`ruff check .`) уронил `lint` на трёх мелочах в новых модулях `settings/` (два `__init__.py` без докстринга, одна строка >88 символов) — поправлено отдельным `style`-коммитом и предложено PR-ссылкой на `dev` (`gh` CLI недоступен в этой среде, PR открыт вручную по сгенерированной ссылке сравнения).

---

## 2026-09-18 — Поиск пользователей

Второй фронтендер не мог начинать работу без эндпоинта поиска людей. По той же логике, что и с настройками (см. выше) — не отдельный сервис, а новый маршрут в `identity/app/users/` (данные и так целиком в таблице `users`, отдельный сервис только добавил бы сетевой хоп или дублирование данных).

- **`feat: add user directory search endpoint to identity`** — `POST /users/search`:
  - `tag` — только префикс по `username`, ведущий `@` обрезается, регистр не учитывается;
  - `email`/`phone`/`name` — подстрока в соответствующем поле, регистронезависимо;
  - `query` — тот же поиск подстроки, но сразу по email/phone/name (не по тегу);
  - несколько заданных полей комбинируются через AND; если не задано ни одного — `422`;
  - `limit` — обязательный параметр без дефолта (по требованию пользователя: без зашитого топ-30, пролистывание через увеличение `limit` на каждый следующий запрос — 30, потом 60, потом 90...), сортировка по `username` для стабильной пагинации.
  - Ответ — `UserResponse` (та же схема, что у `/me`/`/users`) без пароля, но **с `id`** — без него результат поиска нельзя было бы использовать (например, для `POST /chats/direct`).
- В модель `User` добавлено поле `phone` (миграция `82ac3e19d573_add_phone_to_users.py`). `email`/`phone`/`display_name` пока всегда `NULL` — эндпоинта их установки ещё нет, так что реально сейчас работает только поиск по тегу; остальное подключится само, как только появится редактирование профиля.
- Тесты (`tests/test_search.py`, 12 штук) заводят пользователей напрямую через новую фикстуру `db_session_maker` в `conftest.py` (обходя HTTP, раз API для email/phone/name ещё нет) — покрыты префикс/подстрока/регистронезависимость/AND-комбинация/лимит-сортировка/422 на пустой фильтр и на отсутствующий `limit`/исключение пароля из ответа. Прогнано локально на одноразовом Postgres в докере (та же конфигурация, что в CI) — 26/26 зелёных, `ruff check .` чист.

---

## 2026-09-19 — Плавное открытие/закрытие модалки настроек

- **`feat: animate settings modal open/close`** — `SettingsModal` обёрнут в `<Transition>` в `app.vue`. Подложка затухает по opacity, панель дополнительно делает лёгкий scale (0.96→1) со сдвигом вверх на 8px — читается как «материализация». Открытие — 0.18с ease-out, закрытие чуть быстрее — 0.14с. Проверено вживую через Playwright (промежуточный кадр перехода зафиксирован скриншотом на 60мс после клика — панель ещё полупрозрачна/смещена).

---

## 2026-09-19 — Разбор архитектурных вопросов по настройкам

Без изменений кода — обсуждение с пользователем по итогам ревью со стороны бэкенд-разработчика:

- **`accept_calls`** в `identity` — признано архитектурной несостыковкой: сервиса звонков не существует физически, а по принципу «настройка живёт там же, где живёт фича» (тот же, что развёл mute чата по `communication`, а не `identity`) это поле должно появиться в будущем calls-сервисе, а не сейчас в `identity`. Решение по удалению — на паузе, ждём подтверждения.
- **`notifications_enabled`** — проверено по всему репозиторию (`grep`): поле нигде не читается ни в `communication`, ни в `ws-gateway`, только хранится. В отличие от `accept_calls` это **не архитектурная ошибка** (место в `identity` правильное — это глобальная настройка юзера, не привязанная к фиче), а недописанная связь: `ws-gateway` при рассылке `chat.message.created` должен бы проверять этот флаг перед отправкой конкретному пользователю, но не проверяет. Зафиксировано как известный TODO для бэкенда.

---

## 2026-09-19 — Синхронизация с `dev` и разбор PR-ревью

`origin/dev` подтянула работу ksenia «Подключение чатов к API и поиск пользователей» (PR #13) — прямой потребитель `POST /users/search`: контракт (`{ tag, limit }` → `UserResponse[]`) совпал один в один без правок с моей стороны. Слияние fast-forward, конфликтов нет, сборка зелёная.

Прошёлся по комментариям ревью (`Skuyno`) на PR #12/#13 через публичный GitHub REST API (`gh` CLI в этой среде недоступен) и точечно ответил каждому правкой:

- **`refactor: rename generic get/update repository functions in settings modules`** — `get`/`update` в `communication/app/settings/repository.py` → `get_chat_settings`/`update_chat_settings`; тот же паттерн поправлен и в `identity/app/settings/repository.py` (`update` → `update_user_settings`) для консистентности, хотя комментарий был только про `communication`.
- **`refactor: separate fetch-or-create from the read path in settings services`** — в обоих `settings/service.py` `update_settings` вызывал `get_or_create_settings` (функцию GET-эндпоинта), что читалось как ошибочное переиспользование read-логики для записи. Вынес общий приватный `_fetch_or_create` (+ `_require_membership` для чатов) — оба паблик-метода вызывают его явно; необходимость самого upsert-перед-patch осталась (иначе `PATCH` нечего патчить), просто теперь это не выглядит как вызов «чужого» метода.
- **`test: use /auth/register instead of direct DB access where possible`** — по комментарию «зачем обходить БД, если есть эндпоинт регистрации»: 6 из 12 тестов в `test_search.py`, которым нужен только `username`, переведены на `client.post("/auth/register", ...)`; `db_session_maker` оставлен только там, где реально нет эндпоинта под `email`/`phone`/`display_name`. Заодно поймал баг в своих же тестовых данных: `username="a4"` короче `min_length=3` — поправил на `a11`/`a12`/`a13`/`a14`.
- **`fix: preserve repeated query params when proxying through api-gateway`** — тот самый баг из комментария ksenia в `useChats.ts` («api-gateway теряет повторяющиеся query-параметры»). Причина: `request.query_params` (Starlette `QueryParams`) передавался в `httpx` как `params=` напрямую; `httpx` трактует его как обычный `Mapping` и вызывает `.items()`, а тот у Starlette схлопывает дубли ключей до последнего значения. Фикс — `request.query_params.multi_items()`, сохраняет все пары. Проверено на живом стеке: `GET /users?ids=A&ids=B` через gateway теперь возвращает обоих, а не только последнего. Воркэраунд ksenia (по одному запросу на `id` в `useChats.ts`) теперь избыточен, но не трогал её файл без отдельного запроса.

Все правки прогнаны через `ruff check .` (чисто) и полный прогон тестов `identity`/`communication` (26 + 12, оба зелёные) на одноразовом Postgres в докере — конфигурация как в CI.

---

## Правила, установленные пользователем по ходу работы

- Работаем только над фронтендом (`src/web/`); бэкенд — только для изучения контрактов API, не редактируем без явного разового разрешения на конкретную правку.
- Не добавлять/обновлять npm-зависимости без необходимости и согласования.
- После крупных изменений — вести и дополнять этот файл (`BACKLOG-artem.md`).
- Перед началом работы и перед PR в `dev` — синхронизировать `artem` с `origin/dev`.
- Коммиты оформлять строго по таблице типов из корневого `README.md` (`feat`/`fix`/`docs`/`sec`/`build`/`ci`/`refactor`/`revert`/`style`/`init`).
