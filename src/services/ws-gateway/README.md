# WS Gateway

Go-сервис realtime-доставки. Он принимает WebSocket-подключения, проверяет JWT, хранит локальный реестр соединений, получает события из NATS и отправляет их подключённым пользователям. Основную БД и бизнес-логику сервис не содержит.

## Структура

```text
cmd/main.go          запуск сервера и сборка зависимостей
internal/auth/       проверка JWT
internal/broker/     подписка на NATS JetStream
internal/presence/   online/offline в Redis
internal/ws/         WebSocket-клиент и реестр соединений
```

## Интерфейсы

| Метод и путь | Назначение |
|---|---|
| `GET /health` | Проверка процесса WS Gateway |
| `GET /ws?token=<JWT>` | Установка WebSocket-соединения |

При подключении принимается только валидный access JWT, подписанный HS256. Идентификатор пользователя берётся из `sub`.

Gateway подписан на `chat.message.*` (весь wildcard, не только `created`). Поле `recipient_ids` в событии определяет получателей, но клиенту уходит **не** исходный JSON события из NATS — `internal/ws/hub.go` (`HandleNatsEvent` → `buildOutboundEvent`) смотрит на subject и заворачивает событие в конверт `{type, data}` под конкретный случай:

| Subject | `type` в конверте | `data` |
|---|---|---|
| `chat.message.created` | `message.created` | `message_id, chat_id, sender_id, body, created_at` |
| `chat.message.updated` | `message.updated` | то же + `edited_at` |
| `chat.message.deleted` | `message.deleted` | `message_id, chat_id, sender_id` (тело уже не передаётся) |
| `chat.message.read` | `message.read` | `chat_id, user_id, last_read_message_id` |
| `chat.message.typing` | `typing` | `chat_id, user_id` |

Обратите внимание: id сообщения в конверте называется **`message_id`**, а не `id`, как в REST-ответах `/chats/{id}/messages` — это разные поля с одним и тем же смыслом, маппить их придётся отдельно.

Входящие от клиента сообщения по WebSocket **полностью игнорируются** (`ReadPump` в `internal/ws/client.go` только читает и отбрасывает — обработчика нет): WebSocket используется исключительно для доставки от сервера клиенту, отправка нового сообщения всегда идёт через REST (`POST /chats/{id}/messages`).

## Соединение и presence

- Ping отправляется примерно каждые 54 секунды, Pong ожидается не дольше 60 секунд.
- Presence хранится в Redis как `user:{id}:online` с TTL 70 секунд.
- На одно соединение выделена очередь из 256 событий; при переполнении новое событие отбрасывается.
- Presence считает соединения, а не связывает статус с одним конкретным сокетом: `Hub` хранит набор активных соединений на пользователя, и `updatePresence(userID, false)` вызывается только когда закрылось **последнее** из них (`internal/ws/hub.go`, ветка `unregister`). Закрытие одной вкладки/устройства при ещё живом другом соединении presence не трогает.

## Конфигурация

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---:|---|---|
| `JWT_SECRET` | да | — | Секрет проверки JWT |
| `NATS_URL` | нет | `nats://nats:4222` | Адрес NATS |
| `REDIS_URL` | нет | `redis:6379` | Адрес Redis |
| `PORT` | нет | `8080` | HTTP/WebSocket-порт сервиса |

Пример находится в `.env.example`.

## Запуск и проверки

```text
go run ./cmd/main.go
go test ./...
go vet ./...
```

Для отдельного запуска нужны NATS с JetStream и Redis. В Compose сервис публикуется на порту `4333`.
