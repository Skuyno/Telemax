# Backlog — max

Журнал крупных изменений, вносимых в рамках работы над проектом на ветке `max`. Каждая запись — отдельная сессия/пачка изменений, пишем вниз по хронологии (новое снизу).

Параллельные журналы: `BACKLOG-artem.md` (фронтенд-ветка), `BACKLOG-ksenia.md` (фронтенд-ветка).

---

## 2026-09-14 — Внутренний эндпоинт для поиска собеседников по чатам

Коммит `40c9b33` — `feat: add internal endpoint for chat peer lookup`.

Добавлен служебный (internal) роут в сервисе `communication` для получения списка пользователей, с которыми у заданного пользователя есть хотя бы один общий чат. Предназначен для service-to-service вызовов внутри docker-сети (по аналогии с `identity`'s `/internal/users/{user_id}`), наружу через `api-gateway` не проксируется.

- **`src/services/communication/app/internal/router.py`** (новый файл) — `GET /internal/users/{user_id}/chat-peers` → `ChatPeersResponse`.
- **`src/services/communication/app/internal/schemas.py`** (новый файл) — `ChatPeersResponse { user_ids: list[UUID] }`.
- **`src/services/communication/app/internal/__init__.py`** (новый, пустой) — обозначает пакет `internal`.
- **`src/services/communication/app/chats/repository.py`** — новая функция `list_chat_peer_ids(db, user_id)`: через `ChatMember` находит все `chat_id`, где состоит `user_id`, затем возвращает `DISTINCT user_id` остальных участников этих чатов (отсортировано по id).
- **`src/services/communication/app/chats/service.py`** — тонкая обёртка `list_chat_peer_ids`, пробрасывающая вызов в repository-слой (по аналогии с остальными методами сервиса).
- **`src/services/communication/app/main.py`** — зарегистрирован `internal_router` (`app.include_router(internal_router)`), рядом с `chats_router`/`health_router`.

### Как использовать / зачем

Позволяет любому internal-потребителю (например, будущей логике подсказок «с кем чаще всего переписываетесь» или предзагрузке профилей собеседников) одним запросом получить id всех, с кем у пользователя есть общий чат, не гоняя `GET /chats` + перебор участников на клиенте.

### На заметку при мёрже в `dev`

- Эндпоинт не публичный — `api-gateway` его не роутит (в `resolve_target` учтены только `auth`, `users`, `me`, `chats`), так и задумано, менять не нужно если не требуется внешний доступ.
- Стоит свериться, что имя `ChatMember` и путь импорта не разъехались с тем, что сейчас в `dev` после чужих мёржей (страница чатов от `ksenia` активно трогала соседние файлы `chats/*` на фронте, но не на бэкенде — конфликтов по этому файлу на бэкенде быть не должно).

---

## Правила, установленные пользователем по ходу работы над проектом

- Крупные изменения фиксируются в бэклог-файле соответствующей ветки (`BACKLOG-<branch>.md`) в корне репозитория.
- Перед PR в `dev` — синхронизировать ветку с `origin/dev`.
