# WS Gateway

Go-сервис realtime-доставки. Он принимает WebSocket-подключения, проверяет JWT, хранит локальный реестр соединений, получает события из NATS и отправляет их подключённым пользователям. Основную БД и бизнес-логику сервис не содержит.

## Структура

```text
cmd/main.go              запуск сервера и сборка зависимостей
internal/auth/           проверка JWT
internal/broker/         подписка на NATS JetStream
internal/communication/  HTTP-клиент списка собеседников для presence
internal/presence/       online/offline в Redis
internal/ws/             WebSocket-клиент и реестр соединений
```

## Интерфейсы

| Метод и путь | Назначение |
|---|---|
| `GET /health` | Проверка процесса WS Gateway |
| `GET /ws?token=<JWT>` | Установка WebSocket-соединения |

При подключении принимается только валидный access JWT, подписанный HS256. Идентификатор пользователя берётся из `sub`.

Gateway подписан на `chat.message.*`, `chat.sync_required` и `file.upload.*`. Поле `recipient_ids` определяет получателей (включая все их подключения), но не передаётся клиенту. `internal/ws/hub.go` (`HandleNatsEvent` → `buildOutboundEvent`) преобразует NATS-событие в конверт `{type, data}`:

| Subject | `type` в конверте | `data` |
|---|---|---|
| `chat.message.created` | `message.created` | `message_id, chat_id, sender_id, body, created_at` |
| `chat.message.updated` | `message.updated` | то же + `edited_at` |
| `chat.message.deleted` | `message.deleted` | `message_id, chat_id, sender_id` (тело уже не передаётся) |
| `chat.message.read` | `message.read` | `chat_id, user_id, last_read_message_id` |
| `chat.message.typing` | `typing` | `chat_id, user_id` |
| `chat.sync_required` | `chat.sync_required` | `chat_id, reason` |
| `file.upload.progress` | `upload.progress` | `file_id, chat_id, uploader_id, bytes_uploaded, size_bytes` |
| `file.upload.completed` | `upload.completed` | `file_id, chat_id, uploader_id, size_bytes` |

Для created/updated также передаётся `attachment_file_ids`.

Обратите внимание: id сообщения в конверте называется **`message_id`**, а не `id`, как в REST-ответах `/chats/{id}/messages` — это разные поля с одним и тем же смыслом, маппить их придётся отдельно.

Отправка пользовательских сообщений идёт через REST (`POST /chats/{id}/messages`). По WS клиент может отправить служебную команду `{"type":"presence.sync"}` — повторный snapshot статусов собеседников, не чаще раза в пять секунд. Неизвестные команды и некорректный JSON не исполняются.

### Синхронизация групп

```json
{"type":"chat.sync_required","data":{"chat_id":"<uuid>","reason":"members_added"}}
```

`reason`: `created`, `updated`, `members_added`, `member_removed`. Это сигнал перечитать данные, а не полное состояние группы: обновить `GET /chats` и при необходимости участников через REST. Удалённый участник также получает сигнал; если чат исчез из списка, нужно закрыть его и очистить локальные данные. После reconnect обновляйте список независимо от событий: доставка сигнала в браузер не гарантирована. Обработчик на фронтенде ещё требуется.

## Соединение и presence

- Ping отправляется примерно каждые 54 секунды, Pong ожидается не дольше 60 секунд.
- Presence хранится в Redis как `user:{id}:online` с TTL 70 секунд.
- Начальный snapshot и переходы `presence` видны только пользователям с общим чатом; после изменения состава можно запросить `presence.sync`.
- На одно соединение выделена очередь из 256 событий; при переполнении новое событие отбрасывается.
- Presence считает соединения, а не связывает статус с одним конкретным сокетом: `Hub` хранит набор активных соединений на пользователя, и `updatePresence(userID, false)` вызывается только когда закрылось **последнее** из них (`internal/ws/hub.go`, ветка `unregister`). Закрытие одной вкладки/устройства при ещё живом другом соединении presence не трогает.

## Конфигурация

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---:|---|---|
| `JWT_SECRET` | да | — | Секрет проверки JWT |
| `NATS_URL` | нет | `nats://nats:4222` | Адрес NATS |
| `REDIS_URL` | нет | `redis:6379` | Адрес Redis |
| `COMMUNICATION_URL` | нет | `http://communication:8000` | Список собеседников для presence |
| `PORT` | нет | `8080` | HTTP/WebSocket-порт сервиса |

Пример находится в `.env.example`.

## Запуск и проверки

```text
go run ./cmd/main.go
go test ./...
go vet ./...
```

Для отдельного запуска нужны NATS с JetStream и Redis. В Compose сервис публикуется на порту `4333`.
