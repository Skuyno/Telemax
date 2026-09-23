# Communication Service

Ядро переписки Telemax. Сервис создаёт личные диалоги, проверяет членство, хранит сообщения и публикует события для realtime-доставки. Пользователей и JWT он не хранит.

## Структура

```text
app/
  chats/       модели, схемы, репозиторий, бизнес-логика и маршруты
  settings/    настройки чата (mute уведомлений), независимо от chats/
  health/      проверка PostgreSQL
  events.py    подключение и публикация событий NATS JetStream
  config.py    конфигурация из окружения
  database.py  SQLAlchemy engine и фабрика сессий
migrations/    миграции Alembic
tests/         интеграционные тесты чатов и истории
```

## HTTP API

| Метод и путь | Назначение |
|---|---|
| `POST /chats/direct` | Создать или получить личный диалог |
| `GET /chats` | Получить диалоги пользователя с последним сообщением |
| `GET /chats/{id}/members` | Получить участников диалога |
| `POST /chats/{id}/messages` | Сохранить и отправить сообщение |
| `GET /chats/{id}/messages` | Получить историю с курсором `before_msg_id` |
| `PATCH /chats/{id}/messages/{message_id}` | Отредактировать своё сообщение |
| `DELETE /chats/{id}/messages/{message_id}` | Удалить своё сообщение (soft delete, тело очищается) |
| `GET /chats/{id}/messages/search` | Поиск по тексту сообщений в чате (`query`, обязательный `limit`) |
| `POST /chats/{id}/typing` | Сообщить собеседникам «печатает…» (эфемерно, ничего не сохраняется) |
| `POST /chats/{id}/read` | Отметить чат прочитанным до сообщения `last_read_message_id` |
| `GET /chats/{id}/settings` | Получить настройки чата для текущего пользователя |
| `PATCH /chats/{id}/settings` | Изменить настройки чата (например, `notifications_muted`) |
| `GET /health/db` | Проверить подключение к БД |

`GET /chats` теперь также отдаёт `unread_count` на каждый чат — число сообщений от собеседника, отправленных позже вашего последнего `POST /chats/{id}/read`.

`POST /chats/{id}/messages` и `GET /chats/{id}/messages` (а также `.../search`) принимают/отдают `attachment_file_ids: list[UUID]` — id файлов из **file-orchestrator**, прикреплённых к сообщению (см. раздел «Вложения» ниже).

Точные схемы доступны по `/docs` и `/openapi.json`. Все пользовательские маршруты ожидают внутренний заголовок `X-User-Id` от API Gateway.

### Internal-эндпоинты (`/internal/...`)

Не проходят через X-User-Id — вызываются другими сервисами напрямую, без пользовательского контекста.

| Метод и путь | Кто вызывает | Назначение |
|---|---|---|
| `GET /internal/users/{user_id}/chat-peers` | ws-gateway | Id всех, с кем у пользователя есть общий чат (для presence-снапшота) |
| `GET /internal/chats/{chat_id}/members/{user_id}` | file-orchestrator | Состоит ли пользователь в чате (авторизация загрузки/скачивания файла) |
| `GET /internal/chats/{chat_id}/members` | file-orchestrator | Id всех участников чата (кому разослать `file.upload.progress`/`.completed` по WS) |

### Непрочитанные сообщения и отметка о прочтении

Это работает не через отдельный флаг на сообщении, а через таблицу `chat_read_states` (`chat_id`, `user_id`, `last_read_message_id`, `last_read_at`):

1. `POST /chats/{id}/read` с `{ last_read_message_id }` создаёт/обновляет строку через `chats_service.mark_chat_read` → `chats_repository.set_read_state` (`app/chats/repository.py`).
2. Сообщение считается непрочитанным, если оно не от текущего пользователя и создано **позже** его `last_read_at` в этом чате; если строки для пользователя вообще нет — непрочитанными считаются все чужие сообщения. Логика — в `chats_repository.count_unread_bulk`.
3. Готовое число отдаётся как `unread_count` прямо в `GET /chats` — отдельный запрос на подсчёт не нужен.

Клиент может оптимистично занулить счётчик сразу после успешного `POST .../read`, не дожидаясь повторного `GET /chats`.

### Вложения (message attachments)

Файлы физически хранятся в **file-orchestrator** (метаданные) + **SeaweedFS** (байты) — этот сервис хранит только связь `message_id <-> file_id` в таблице `message_attachments` (composite PK, `file_id` не FK — указывает на строку в чужой БД).

1. Клиент сначала загружает файл в file-orchestrator (`POST /files?chat_id=...` через API Gateway), получает `file_id`.
2. `POST /chats/{id}/messages` принимает `attachment_file_ids: list[UUID]` — перед сохранением сообщения они валидируются через file-orchestrator (`POST /internal/files/validate`: файл должен существовать, быть `status=ready` и принадлежать этому чату); невалидный id — `400`.
3. При успешной вставке (не при идемпотентном повторе того же `client_msg_id`) id вложений привязываются к сообщению; `GET`/`POST .../messages` и `.../search` возвращают их в `attachment_file_ids`.
4. При удалении сообщения (`DELETE .../messages/{id}`) id вложений уходят в payload `chat.message.deleted` — по этому же subject подписан file-orchestrator, он и удаляет сами блобы из SeaweedFS.

Подробности эндпоинтов file-orchestrator и SeaweedFS — в его собственном `README.md`.

## Взаимодействия

- **PostgreSQL** хранит `chats`, `chat_members`, `direct_chats`, `messages`, `message_attachments`, `chat_read_states` и `chat_settings`.
- **Identity Service** проверяет существование второго участника при создании диалога.
- **File Orchestrator** проверяет `attachment_file_ids` при отправке сообщения (`POST /internal/files/validate`) и, наоборот, вызывает этот сервис (`GET /internal/chats/{id}/members[/{user_id}]`), чтобы авторизовать доступ к файлу и разослать прогресс загрузки нужным участникам чата.
- **NATS JetStream** — стрим `CHATS` теперь общий с file-orchestrator, `subjects=["chat.message.>", "file.upload.>"]` (оба сервиса идемпотентно обеспечивают этот список при подключении: `add_stream`, а если уже существует — `update_stream`). В `chat.message.>` попадают `chat.message.created`, `chat.message.updated`, `chat.message.deleted`, `chat.message.read` и `chat.message.typing`; `file.upload.>` целиком публикует file-orchestrator.

Все события несут `chat_id` и `recipient_ids` (кому доставить); конкретные поля зависят от типа (`id`/`body`/`created_at` для created/updated, `last_read_message_id` для read, `attachment_file_ids` дополнительно для deleted и т.д.) — точный набор полей на конкретный subject смотрите в `app/chats/service.py`. **WS Gateway не пересылает эти события как есть** — `internal/ws/hub.go` разбирает subject и заворачивает каждое в свой конверт `{type, data}` для клиента; см. README `ws-gateway`.

Повторный запрос с тем же сочетанием `sender_id + client_msg_id` возвращает существующее сообщение. Сначала выполняется commit в PostgreSQL, затем публикация в NATS; эти операции не образуют общую транзакцию.

## Конфигурация

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---:|---|---|
| `POSTGRES_USER` | да | — | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | да | — | Пароль PostgreSQL |
| `POSTGRES_DB` | да | — | База данных сервиса |
| `POSTGRES_HOST` | нет | `db` | Адрес PostgreSQL |
| `POSTGRES_PORT` | нет | `5432` | Порт PostgreSQL |
| `IDENTITY_URL` | нет | `http://identity:8000` | Адрес Identity Service |
| `FILE_ORCHESTRATOR_URL` | нет | `http://file-orchestrator:8000` | Адрес File Orchestrator Service |
| `NATS_PORT` | нет | `4222` | Порт NATS |

Пример находится в `.env.example`.

## Запуск и проверки

Для локальной разработки нужны Python 3.11+ и Poetry. Из каталога сервиса создайте `.env` на основе `.env.example`, затем выполните:

```text
poetry install --no-root
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
poetry run pytest -q
```

Активировать окружение вручную не требуется. Для отдельного запуска должны быть доступны PostgreSQL, Identity Service и NATS. В составе системы используется `docker compose up --build` из каталога `deploy`.
