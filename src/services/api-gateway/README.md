# API Gateway

Единая HTTP-точка входа Telemax. Gateway проверяет access JWT, извлекает `user_id` и проксирует запрос в Identity или Communication Service. Собственной базы данных и бизнес-данных у него нет.

## Структура

```text
app/
  main.py          создание FastAPI-приложения
  router.py        маршрутизация и HTTP-прокси
  dependencies.py проверка JWT
  config.py        адреса сервисов и настройки JWT
```

## Маршрутизация

| Пути | Сервис | Авторизация |
|---|---|---|
| `/auth/register`, `/auth/login`, `/auth/refresh` | Identity | публичные |
| `/me`, `/users...` | Identity | access JWT |
| `/chats...` | Communication | access JWT |

Для маршрутов, требующих авторизации, Gateway проверяет подпись, срок действия и `type=access` JWT, затем добавляет `X-User-Id`. Downstream-сервисы доверяют этому заголовку и не должны быть доступны напрямую извне.

Прокси сейчас поддерживает `GET` и `POST`. Маршрут скрыт из OpenAPI, поэтому `/docs` Gateway не является общей документацией всех сервисов.

## Конфигурация

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---:|---|---|
| `JWT_SECRET` | да | — | Секрет проверки JWT |
| `JWT_ALGORITHM` | нет | `HS256` | Допустимый алгоритм JWT |
| `IDENTITY_URL` | нет | `http://identity:8000` | Адрес Identity Service |
| `COMMUNICATION_URL` | нет | `http://communication:8000` | Адрес Communication Service |

Пример находится в `.env.example`.

## Запуск и проверка

Для локальной разработки нужны Python 3.11+ и Poetry. Из каталога сервиса создайте `.env` на основе `.env.example`, затем выполните:

```text
poetry install --no-root
poetry run uvicorn app.main:app --reload
```

Активировать окружение вручную не требуется. Ruff пока устанавливается отдельно от Poetry и запускается командой `ruff check .`; в CI он устанавливается автоматически.

В составе системы Gateway запускается через `docker compose up --build` из каталога `deploy` и публикуется на порту `8000`.
