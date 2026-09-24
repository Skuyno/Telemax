# Identity Service

Сервис пользователей и аутентификации. Регистрирует пользователей, проверяет пароль, выпускает JWT и отдаёт публичные данные профиля. Не хранит чаты и сообщения.

## Структура

```text
app/
  users/       модели, схемы, бизнес-логика и HTTP-маршруты
  settings/    глобальные настройки пользователя, независимо от users/
  internal/    маршруты для других сервисов, включая управление аккаунтами
  health/      проверка PostgreSQL
  roles.py     константы ролей (каноническая копия — вторая в administration)
  config.py    конфигурация из окружения
  database.py  SQLAlchemy engine и фабрика сессий
migrations/    миграции Alembic
tests/         тесты аутентификации, токенов и поиска пользователей
```

## HTTP API

| Метод и путь | Назначение | Доступ |
|---|---|---|
| `POST /auth/register` | Регистрация пользователя | публичный |
| `POST /auth/login` | Получение access и refresh JWT | публичный |
| `POST /auth/refresh` | Получение нового access по refresh JWT | публичный, нужен refresh JWT |
| `GET /me` | Профиль текущего пользователя | через API Gateway |
| `PATCH /me` | Изменить `display_name`/`email` | через API Gateway |
| `POST /me/password` | Сменить пароль (текущий + новый), отзывает refresh-токены | через API Gateway |
| `POST /password/reset` | Сбросить пароль со страницы настроек (только новый, без текущего), отзывает refresh-токены | через API Gateway |
| `GET /users?ids=...` | Профили нескольких пользователей | через API Gateway |
| `POST /users/search` | Поиск пользователей по тегу/email/телефону/имени | через API Gateway |
| `GET /me/settings` | Настройки текущего пользователя | через API Gateway |
| `PATCH /me/settings` | Изменить настройки (например, `notifications_enabled`, `accept_calls`) | через API Gateway |
| `GET /internal/users/{id}` | Профиль пользователя (включая роль) | внутренний |
| `GET /health/db` | Проверка подключения к БД | внутренний |
| `POST /internal/accounts` | Создать admin- или user-аккаунт (без проверки прав — их уже проверил вызывающий) | внутренний |
| `DELETE /internal/accounts/{id}?caller_id=...` | Удалить аккаунт (проверяет только неснимаемые инварианты — см. «Роли») | внутренний |
| `GET /internal/accounts` | Список аккаунтов (пагинация `limit`/`offset`) | внутренний |
| `GET /internal/accounts/username-available?username=...` | Проверка занятости логина | внутренний |

Точные схемы запросов и ответов доступны в Swagger UI по `/docs` и в OpenAPI JSON по `/openapi.json` при запущенном сервисе.

**Публичного `/admin/...` API у identity больше нет** — управление аккаунтами (создание/удаление, с проверкой того, кто кем может управлять) теперь отдельный сервис `administration`, см. его README. Identity лишь исполняет запрос через `/internal/accounts/...`, доверяя, что `administration` уже проверил роль вызывающего.

## Роли

Три роли, хранятся в `users.role`: `superuser`, `admin`, `user`. Кто кем может управлять — решает `administration` (`app/roles.py` там); identity хранит данные и обеспечивает только неснимаемые инварианты, которые должны выполняться независимо от того, кто спрашивает:

- **superuser** — единственный аккаунт, создаётся автоматически при первом старте сервиса (см. `ensure_superuser_seeded` в `app/main.py`) с логином/паролем из `SUPERUSER_USERNAME`/`SUPERUSER_PASSWORD` (по умолчанию `admin`/`admin123` — обязательно сменить перед реальным деплоем). Его нельзя удалить никому и никогда — `DELETE /internal/accounts/{id}` всегда отвечает `403` на цель с ролью `superuser`, вне зависимости от того, кто и с каким `caller_id` спрашивает.
- Аккаунт не может удалить сам себя через `DELETE /internal/accounts/{id}?caller_id=...` (`400`, если `id == caller_id`) — тоже проверяется здесь, а не в `administration`.
- **user** — обычный аккаунт, создаётся через `POST /auth/register` (самостоятельная регистрация никогда не создаёт admin/superuser) или через `administration`.

## Токены

- Access JWT живёт 15 минут и содержит `sub`, `exp`, `type=access`.
- Refresh JWT живёт 30 дней и дополнительно содержит `ver`.
- Refresh-токен не ротируется. `token_version` проверяется при рефреше и увеличивается в `POST /me/password` и `POST /password/reset` — обе операции отзывают все ранее выданные refresh-токены (текущий access остаётся рабочим до истечения своих 15 минут). Разница между ними только в том, что `/password/reset` не требует текущий пароль (более простой флоу для страницы настроек) — не более слабая проверка, а иная: вызывающий всё ещё должен быть аутентифицирован (валидный access-токен).
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
| `SQL_ECHO` | нет | `false` | Логировать SQL-запросы SQLAlchemy (со значениями параметров — email, хэши паролей; включать только локально для отладки) |
| `ALLOW_REGISTRATION` | нет | `true` | Разрешить `POST /auth/register`. На проде с закрытой регистрацией — `false` (сервер отвечает `403`, независимо от того, показывает ли фронтенд кнопку) |
| `SUPERUSER_USERNAME` | нет | `admin` | Логин автосоздаваемого superuser-аккаунта — сменить перед реальным деплоем |
| `SUPERUSER_PASSWORD` | нет | `admin123` | Пароль автосоздаваемого superuser-аккаунта — сменить перед реальным деплоем |

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
