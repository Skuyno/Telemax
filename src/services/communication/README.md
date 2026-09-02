# Communication Service

Ядро переписки Telemax. Сервис создаёт личные диалоги, проверяет членство, хранит сообщения и публикует события для realtime-доставки. Пользователей и JWT он не хранит.

## Структура

```text
app/
  chats/       модели, схемы, репозиторий, бизнес-логика и маршруты
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
| `GET /health/db` | Проверить подключение к БД |

Точные схемы доступны по `/docs` и `/openapi.json`. Все пользовательские маршруты ожидают внутренний заголовок `X-User-Id` от API Gateway.

## Взаимодействия

- **PostgreSQL** хранит `chats`, `chat_members`, `direct_chats` и `messages`.
- **Identity Service** проверяет существование второго участника при создании диалога.
- **NATS JetStream** получает событие `chat.message.created` после сохранения сообщения.

Событие содержит `id`, `chat_id`, `sender_id`, `recipient_ids`, `body` и `created_at`. Сейчас WS Gateway передаёт этот JSON клиенту без преобразования.

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
