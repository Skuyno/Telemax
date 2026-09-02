# Identity Service

Сервис пользователей и аутентификации. Регистрирует пользователей, проверяет пароль, выпускает JWT и отдаёт публичные данные профиля. Не хранит чаты и сообщения.

## Структура

```text
app/
  users/       модели, схемы, бизнес-логика и HTTP-маршруты
  internal/    маршруты для других сервисов
  health/      проверка PostgreSQL
  config.py    конфигурация из окружения
  database.py  SQLAlchemy engine и фабрика сессий
migrations/    миграции Alembic
tests/         тесты аутентификации и токенов
```

## HTTP API

| Метод и путь | Назначение | Доступ |
|---|---|---|
| `POST /auth/register` | Регистрация пользователя | публичный |
| `POST /auth/login` | Получение access и refresh JWT | публичный |
| `POST /auth/refresh` | Получение нового access по refresh JWT | публичный, нужен refresh JWT |
| `GET /me` | Профиль текущего пользователя | через API Gateway |
| `GET /users?ids=...` | Профили нескольких пользователей | через API Gateway |
| `GET /internal/users/{id}` | Проверка существования пользователя | внутренний |
| `GET /health/db` | Проверка подключения к БД | внутренний |

Точные схемы запросов и ответов доступны в Swagger UI по `/docs` и в OpenAPI JSON по `/openapi.json` при запущенном сервисе.

## Токены

- Access JWT живёт 15 минут и содержит `sub`, `exp`, `type=access`.
- Refresh JWT живёт 30 дней и дополнительно содержит `ver`.
- Refresh-токен не ротируется. `token_version` уже проверяется, но операций, которые увеличивают его и отзывают сессии, пока нет.
- Пароли хешируются Argon2.

## Конфигурация

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---:|---|---|
| `POSTGRES_USER` | да | — | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | да | — | Пароль PostgreSQL |
| `POSTGRES_DB` | да | — | База данных сервиса |
| `POSTGRES_HOST` | нет | `db` | Адрес PostgreSQL |
| `POSTGRES_PORT` | нет | `5432` | Порт PostgreSQL |
| `JWT_SECRET` | да | — | Секрет подписи JWT |
| `JWT_ALGORITHM` | нет | `HS256` | Алгоритм подписи JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | нет | `15` | Срок жизни access JWT в минутах |
| `REFRESH_TOKEN_EXPIRE_DAYS` | нет | `30` | Срок жизни refresh JWT в днях |

Пример находится в `.env.example`.

## Запуск и проверки

Для локальной разработки нужны Python 3.11+ и Poetry. Из каталога сервиса создайте `.env` на основе `.env.example`, затем выполните:

```text
poetry install --no-root
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
poetry run pytest -q
```

Активировать окружение вручную не требуется: `poetry run` использует окружение этого сервиса. Для запуска всей системы выполните `docker compose up --build` из каталога `deploy`.

Сервис доверяет заголовку `X-User-Id`, который выставляет API Gateway, поэтому его порт не должен публиковаться наружу.
