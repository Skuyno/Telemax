# Communication Service

Ядро переписки Telemax. Сервис создаёт личные и групповые чаты, проверяет членство, хранит сообщения и публикует события для realtime-доставки. Пользователей и JWT он не хранит.

## Структура

```text
app/
  chats/       модели, схемы, репозиторий, бизнес-логика и маршруты
  pins/        закрепление сообщений (своя модель/сервис/роутер, независимо от chats/)
  settings/    настройки чата (mute уведомлений, закрепление чата), независимо от chats/
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
| `POST /chats/group` | Создать новую группу |
| `GET /chats` | Получить личные и групповые чаты с последним сообщением |
| `GET /chats/{id}/members` | Получить участников диалога |
| `POST /chats/{id}/members` | Добавить участников группы (владелец) |
| `DELETE /chats/{id}/members/{user_id}` | Удалить участника (владелец) или выйти самому |
| `PATCH /chats/{id}` | Переименовать группу (владелец) |
| `PUT /chats/{id}/avatar` | Загрузить/заменить аватар группы (сырое тело, владелец) |
| `DELETE /chats/{id}/avatar` | Удалить аватар группы (владелец) |
| `GET /chats/{id}/avatar` | Получить байты аватара группы (участник чата) |
| `POST /chats/{id}/messages` | Сохранить и отправить сообщение (опционально `reply_to_message_id`) |
| `GET /chats/{id}/messages` | Получить историю с курсором `before_msg_id` |
| `PATCH /chats/{id}/messages/{message_id}` | Отредактировать своё сообщение |
| `DELETE /chats/{id}/messages/{message_id}` | Удалить своё сообщение (soft delete, тело очищается) |
| `POST /chats/{id}/messages/delete` | Удалить несколько своих сообщений одним запросом (`message_ids`, всё-или-ничего) |
| `POST /chats/{id}/messages/forward` | Переслать одно или несколько сообщений из другого чата (`source_chat_id`, `source_message_ids`) |
| `GET /chats/{id}/messages/search` | Поиск по тексту сообщений в чате (`query`, обязательный `limit`) |
| `POST /chats/{id}/messages/{message_id}/pin` | Закрепить сообщение: `{"scope": "me"\|"everyone"}` |
| `DELETE /chats/{id}/messages/{message_id}/pin` | Открепить сообщение: `{"scope": "me"\|"everyone"}` |
| `GET /chats/{id}/messages/pinned` | Список закреплённых сообщений для текущего пользователя |
| `POST /chats/{id}/typing` | Сообщить собеседникам «печатает…» (эфемерно, ничего не сохраняется) |
| `POST /chats/{id}/read` | Отметить чат прочитанным до сообщения `last_read_message_id` |
| `GET /chats/{id}/settings` | Получить настройки чата для текущего пользователя |
| `PATCH /chats/{id}/settings` | Изменить настройки чата (`notifications_muted`, `is_pinned`) |
| `GET /health/db` | Проверить подключение к БД |

`GET /chats` отдаёт `id`, `type` (`direct`/`group`/`notifications`), `title` (`null` для direct), `avatar_url` (только для групп, иначе `null`), `last_message`, `unread_count` и `is_pinned` (личная настройка текущего пользователя, см. «Закрепление чатов» ниже). Последнее поле — число чужих сообщений, созданных позже сохранённой границы прочтения.

`POST /chats/{id}/messages` и `GET /chats/{id}/messages` (а также `.../search`, `.../pinned`, `.../forward`) принимают/отдают `attachment_file_ids: list[UUID]` — id файлов из **file-orchestrator**, прикреплённых к сообщению (см. раздел «Вложения» ниже), и несут `kind` (`"text"`/`"service"`), `reply_to_message_id`, `forwarded_from_message_id`/`forwarded_from_sender_id` и, для служебных сообщений, `service_action`/`service_target_message_id` (см. «Ответы, пересылка и служебные сообщения» ниже).

Точные схемы доступны по `/docs` и `/openapi.json`. Все пользовательские маршруты ожидают внутренний заголовок `X-User-Id` от API Gateway.

### Ответы, пересылка, массовое удаление и служебные сообщения

- **Ответ** — `POST /chats/{id}/messages` с `reply_to_message_id`: должен существовать именно в этом чате и не быть удалён или служебным (`404`/`400`), иначе ничего особого не проверяется. Это живая ссылка (не снэпшот) — если ответ не удалят вместе с оригиналом, превью должно подтягивать актуальный текст оригинала.
- **Пересылка** — `POST /chats/{id}/messages/forward`, `{source_chat_id, source_message_ids: [...], client_msg_id}`. Нужно членство и в исходном, и в целевом чате. Все id должны существовать в `source_chat_id`, не быть удалёнными и не быть служебными — иначе `400`/`404` и **ничего не пересылается** (всё-или-ничего). Пересланные копии независимы от оригиналов (своя строка, скопированные `body`/вложения; `forwarded_from_sender_id` — снэпшот на момент пересылки) и возвращаются в том порядке, в котором исходные сообщения шли в исходном чате, а не в порядке id в запросе. Один `client_msg_id` покрывает всю пачку: каждое пересланное сообщение получает свой собственный `client_msg_id`, детерминированно выведенный из батчевого (`uuid5`), так что повтор того же запроса идемпотентен.
- **Массовое удаление** — `POST /chats/{id}/messages/delete`, `{message_ids: [...]}` (1–100). Все сообщения должны принадлежать этому чату и отправителю — иначе `403`/`404` и ничего не удаляется. События `chat.message.deleted` публикуются по одному на сообщение, как при обычном удалении.
- **Закрепление «для всех» пишет служебное сообщение** в историю чата: `kind: "service"`, `service_action: "message_pinned"`, `service_target_message_id` — id закреплённого сообщения, `sender_id` — кто закрепил. Оно реально хранится и отдаётся как обычное сообщение (в том числе как `last_message` в `GET /chats`), рассылается тем же `chat.message.created`. Закрепление «только для себя» и открепление (в обоих scope) служебных сообщений не создают — как в Telegram. Служебные сообщения нельзя редактировать, нельзя указать как `reply_to_message_id`, нельзя использовать как источник пересылки (`400` во всех трёх случаях).

### Закрепление чатов и сообщений

- **Чат** — личная настройка пользователя, часть `app/settings` (`PATCH /chats/{id}/settings {"is_pinned": true}`); `pinned_at` выставляется сервером, несколько закреплённых чатов в `GET /chats` сортируются последним закреплённым наверх, затем — по свежести последнего сообщения.
- **Сообщение** (`app/pins/`) — любой участник чата может закрепить/открепить, без ограничения по количеству, с развилкой `scope: "me" | "everyone"` и на закреплении, и на откреплении. Три эффективных состояния на пару (сообщение, пользователь): не закреплено / закреплено лично / закреплено для всех (`chat_message_pins` + `message_pin_overrides`, states `personal_pin`/`hidden`). Открепление «для себя» сообщения, закреплённого «для всех», прячет его только из личного списка вызывающего — остальные продолжают видеть глобальный pin.
- Живое обновление и чата, и сообщения идёт через уже существующий `chat.sync_required` (новые `reason`: `message_pinned`/`message_unpinned`) — отдельный NATS-subject не заводился, правок в `ws-gateway` для этого не потребовалось.

### Аватар группы

`PUT`/`DELETE /chats/{id}/avatar` — тот же паттерн, что `PUT/DELETE /me/avatar` в identity: сырое тело (без multipart), `Content-Type` — `image/jpeg|png|webp|gif`, до `MAX_AVATAR_SIZE_BYTES`. Хранится напрямую в SeaweedFS по фиксированному ключу `chat-avatars/{chat_id}` (повторная загрузка просто заменяет блоб), `avatar_url` в БД — не прямой URL SeaweedFS, а собственный `/chats/{id}/avatar?v=<uuid>` (cache-busting суффикс при каждой замене). В отличие от аватара пользователя (видного кому угодно), `GET /chats/{id}/avatar` проверяет членство в чате, а не просто аутентификацию. Менять и удалять может только владелец группы — остальным `403`; и загрузка, и удаление, и переименование используют один и тот же `_require_group_owner`.

### Групповые чаты

```text
POST /chats/group
{ "title": "Команда", "member_ids": ["<uuid>"] }
-> 201 { "id": "<uuid>" }

POST /chats/{id}/members
{ "user_ids": ["<uuid>"] }
-> 204

PATCH /chats/{id}
{ "title": "Новое название" }
-> 204

DELETE /chats/{id}/members/{user_id}
-> 204
```

`member_ids` можно не передавать: группа начинается с одного владельца. Создатель получает роль `owner`, остальные — `member`; повторяющиеся UUID не создают дублей. Название ограничено 128 символами, пробелы по краям удаляются. Повторное создание всегда создаёт новую группу, даже с тем же составом.

Добавлять участников и менять название может только владелец. Участник может выйти, владелец — удалить другого участника, но не себя: передача владения пока не реализована. Повторное добавление/удаление не дублирует членство; повторное добавление может вновь отправить sync. После удаления чат исчезает из списка пользователя, доступ к истории и отправке закрывается; сообщения сохраняются для оставшихся участников.

Ошибки: `403` — нет членства/прав владельца; `404` — неизвестный приглашённый пользователь; `409` — групповая операция над direct-чатом или выход владельца; `400` — название из пробелов; `422` — неверная схема (в том числе пустое/слишком длинное название). Неизвестный пользователь отменяет создание/добавление целиком.

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

- **PostgreSQL** хранит `chats`, `chat_members`, `direct_chats`, `group_chats`, `messages`, `message_attachments`, `chat_read_states`, `chat_settings`, `chat_message_pins` и `message_pin_overrides`.
- **Identity Service** проверяет существование второго участника личного диалога и пакетно проверяет приглашённых в группу через `GET /users?ids=...`.
- **File Orchestrator** проверяет `attachment_file_ids` при отправке сообщения (`POST /internal/files/validate`) и, наоборот, вызывает этот сервис (`GET /internal/chats/{id}/members[/{user_id}]`), чтобы авторизовать доступ к файлу и разослать прогресс загрузки нужным участникам чата.
- **SeaweedFS** хранит байты аватаров групп напрямую (без file-orchestrator) — тот же filer HTTP API, что и у аватаров пользователей в identity, просто с другим ключом (`chat-avatars/{chat_id}` вместо `avatars/{user_id}`).
- **NATS JetStream** — общий с file-orchestrator стрим `CHATS`, `subjects=["chat.>", "file.upload.>"]` (оба сервиса обеспечивают этот список через `add_stream`/`update_stream`). Communication публикует `chat.message.created`, `.updated`, `.deleted`, `.read`, `.typing` и `chat.sync_required`; `file.upload.>` публикует file-orchestrator.

Все события несут `chat_id` и `recipient_ids` (кому доставить); конкретные поля зависят от типа (`id`/`body`/`created_at` для created/updated, `last_read_message_id` для read, `attachment_file_ids` дополнительно для deleted и т.д.) — точный набор полей на конкретный subject смотрите в `app/chats/service.py`. **WS Gateway не пересылает эти события как есть** — `internal/ws/hub.go` разбирает subject и заворачивает каждое в свой конверт `{type, data}` для клиента; см. README `ws-gateway`.

Повторный запрос с тем же сочетанием `sender_id + client_msg_id` возвращает существующее сообщение. Сначала выполняется commit в PostgreSQL, затем публикация в NATS; эти операции не образуют общую транзакцию.

Изменения группы публикуют `chat.sync_required` с `{chat_id, reason, recipient_ids}`. Причины: `created`, `updated`, `members_added`, `member_removed`. Получатели — текущие участники, а при удалении также удалённый пользователь. Клиент получает только `{type: "chat.sync_required", data: {chat_id, reason}}` и перечитывает состояние через REST. При сбое NATS изменение уже может быть сохранено, хотя HTTP-запрос завершится ошибкой; гарантированного восстановления публикации пока нет. На reconnect нужно обновлять список чатов.

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
| `SEAWEEDFS_FILER_URL` | нет | `http://seaweedfs:8888` | Адрес SeaweedFS filer (для аватаров групп) |
| `MAX_AVATAR_SIZE_BYTES` | нет | `5242880` (5 МБ) | Максимальный размер аватара группы |
| `NATS_PORT` | нет | `4222` | Порт NATS |
| `SQL_ECHO` | нет | `false` | Логировать SQL-запросы SQLAlchemy (со значениями параметров — тексты сообщений; включать только локально для отладки) |

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

Тесты используют отдельную БД `test_telemax_communication` на `localhost:5430`; адрес можно переопределить через `TEST_DATABASE_URL`. Используйте только тестовую БД: фикстура очищает чаты после каждого сценария. Identity и NATS замоканы. `create_all` создаёт недостающие таблицы, но не обновляет старые колонки — для проверки миграций запускайте `alembic upgrade head` на отдельной чистой БД, указав её в `POSTGRES_*`.
