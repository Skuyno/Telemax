# Administration Service

Управление аккаунтами для admin/superuser — единственная забота этого сервиса. Никакой собственной базы данных: каждое чтение и изменение идёт через internal-API `identity`, которая владеет пользователями и ролями. Administration — это слой авторизации («кто кем может управлять»), а не хранилище.

## Структура

```text
app/
  accounts/    схемы, бизнес-логика (проверка ролей) и HTTP-маршруты
  health/      liveness-проверка (без БД — проверять нечего)
  roles.py     константы ролей и MANAGEABLE_ROLES — копия identity/app/roles.py,
               держать в синхроне вручную (см. комментарий в файле)
  config.py    конфигурация из окружения
  main.py      сборка FastAPI-приложения
```

## HTTP API

Путь остаётся `/admin/accounts` — тем же, что раньше отдавала `identity` напрямую, чтобы контракт для фронтенда не менялся при переносе.

| Метод и путь | Назначение | Доступ |
|---|---|---|
| `POST /admin/accounts` | Создать admin- или user-аккаунт | admin/superuser |
| `DELETE /admin/accounts/{id}` | Удалить аккаунт | admin/superuser |
| `GET /admin/accounts` | Список аккаунтов (пагинация `limit`/`offset`) | admin/superuser |
| `GET /admin/accounts/username-available?username=...` | Проверка занятости логина в реальном времени | admin/superuser |
| `GET /health` | Liveness | внутренний |

Все маршруты ожидают заголовок `X-User-Id` от API Gateway (как и остальные сервисы). Роль вызывающего здесь не хранится — на каждый запрос она заново запрашивается у `identity` (`GET /internal/users/{id}`), чтобы решение всегда было по актуальным данным (роль могла смениться или аккаунт — быть удалён после выдачи токена).

## Роли

- **superuser** может создавать/удалять `admin`- и `user`-аккаунты.
- **admin** может создавать/удалять только `user`-аккаунты.
- **user** не имеет доступа ни к одному `/admin/...` маршруту (`403`).
- Роль `superuser` никогда не участвует как цель — её нельзя создать через `POST /admin/accounts` (схема `CreateAccountRequest.role` физически не пропускает такое значение) и нельзя удалить через `DELETE /admin/accounts/{id}` (identity сама отказывает на уровне `/internal/accounts`, независимо от того, что решила administration).
- Удалить самого себя через `DELETE /admin/accounts/{id}` нельзя — тоже проверяется дважды: и здесь (до похода к identity), и в самой identity.

Таблица правил — `app/roles.py` (`MANAGEABLE_ROLES`). Точная копия лежит в `identity/app/roles.py` с той же структурой — если правила меняются, обновлять оба файла.

## Взаимодействия

- **Identity Service** — источник правды по пользователям/ролям. Вызывается на каждый запрос сюда: `GET /internal/users/{id}` (роль вызывающего и — при удалении — роль цели), `POST/GET /internal/accounts`, `DELETE /internal/accounts/{id}?caller_id=...`.

## Конфигурация

| Переменная | Обязательная | По умолчанию | Назначение |
|---|---:|---|---|
| `IDENTITY_URL` | нет | `http://identity:8000` | Адрес Identity Service |

Пример находится в `.env.example`.

## Запуск и проверки

```text
poetry install --no-root
poetry run uvicorn app.main:app --reload
poetry run pytest -q
```

Нет базы данных — для тестов ничего поднимать не нужно, все вызовы к `identity` мокаются. Для отдельного запуска нужен доступный `Identity Service`. В составе системы используется `docker compose up --build` из каталога `deploy`.

Сервис доверяет заголовку `X-User-Id`, который выставляет API Gateway, поэтому его порт не должен публиковаться наружу.
