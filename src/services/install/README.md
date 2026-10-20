# Install Service

Веб-мастер первого запуска: генерирует секреты, пишет `.env` для всех сервисов и поднимает стек через `docker compose`. Не обязателен — кто угодно может продолжать настраивать `.env`-файлы вручную и запускать `docker compose up` как раньше, этот сервис просто автоматизирует тот же путь.

Статус: на этом этапе реализованы только обнаружение и валидация манифестов (`app/discovery.py`, `app/schema.py`). Сама форма установки, генерация/запись `.env` и запуск `docker compose` будут добавлены следующими шагами.

## Расширяемость — единственная точка добавления нового сервиса

Install Service **не знает по имени** ни про один сервис. Вместо этого каждый сервис сам описывает свои переменные окружения в `install.yml` — рядом со своим `.env.example`:

```text
deploy/install.yml
src/services/identity/install.yml
src/services/communication/install.yml
src/services/file-orchestrator/install.yml
src/services/api-gateway/install.yml
src/services/ws-gateway/install.yml
```

Добавление нового микросервиса = один новый `install.yml` в его же папке (плюс сам сервис в `deploy/docker-compose.yml`, это и так неизбежно). Правки в коде `install_service` не нужны.

### Формат `install.yml`

```yaml
vars:
  POSTGRES_DB:
    source: fixed          # известное заранее значение
    value: telemax_identity
  JWT_SECRET:
    source: secret         # ссылка на общий секрет (см. shared_secrets.yml)
    ref: jwt_secret
  SUPERUSER_USERNAME:
    source: form           # спрашивается у пользователя при установке
    field: superuser_username
    label: "Имя суперпользователя"
    required: true
```

Итоговый `.env` всегда пишется в `<папка install.yml>/.env` — путь не указывается явно, это фиксированная конвенция.

### `shared_secrets.yml`

Секреты, которые нужны сразу нескольким сервисам (`postgres_password`, `jwt_secret`), зарегистрированы один раз в `src/services/install/shared_secrets.yml`. Секрет, нужный только одному сервису, регистрировать не обязательно — `discovery.resolve_secret_spec` подставит дефолтную генерацию (`random_token`, 32 байта) для любой незнакомой ссылки.

## Структура

```text
app/
  schema.py       пидантик-модели install.yml / shared_secrets.yml
  discovery.py    поиск install.yml по репозиторию, их валидация,
                  сбор секретных ссылок
  health/         liveness-проверка
  main.py         сборка FastAPI-приложения
shared_secrets.yml
tests/
```

## Запуск и проверки

```text
poetry install --no-root
poetry run pytest -q
```
