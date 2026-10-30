# Install Service

Веб-мастер первого запуска: генерирует секреты, пишет `.env` для всех сервисов, поднимает стек через `docker compose` и, если указан домен, автоматически выпускает TLS-сертификат (Let's Encrypt). Не обязателен — кто угодно может продолжать настраивать `.env`-файлы вручную и запускать `docker compose up` как раньше, этот сервис просто автоматизирует тот же путь. Если конфигурация уже полностью настроена вручную, сервис сразу показывает заглушку вместо формы.

## Запуск

Строго из каталога `deploy/`:

```bash
cd deploy
docker compose -f docker-compose.install.yml up -d --build
# открыть http://<host>:8900
docker compose -f docker-compose.install.yml down   # после установки
```

Сервис использует Docker-outside-of-Docker: сам дёргает `docker compose`/`docker run` на хостовом демоне через смонтированный `/var/run/docker.sock`. Поэтому репозиторий монтируется в контейнер **по тому же абсолютному хостовому пути**, что и на хосте (`${PWD}/..` в `docker-compose.install.yml`, где `${PWD}` — это и есть `deploy/`, если команда запущена оттуда) — иначе относительные bind-mount пути внутри `deploy/docker-compose.yml` (например `./initdb`) резолвятся install-контейнером в путь, которого не существует на хосте. Это обязательное условие, а не стилистический выбор; подробный разбор — в комментарии в начале самого `docker-compose.install.yml`.

На Windows это надёжно работает только через WSL2/реальный Linux-шелл — обычный Git Bash на Windows (MSYS) может переписывать POSIX-style пути перед передачей в `docker.exe`, из-за чего такие вложенные bind-mount'ы ведут себя непредсказуемо. На проде (Linux) это штатный, многократно задокументированный паттерн.

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

Добавление нового микросервиса = один новый `install.yml` в его же папке (плюс сам сервис в `deploy/docker-compose.yml`, это и так неизбежно). Правки в коде `install_service` не нужны — в том числе сама HTML-форма рендерится из `source: form` полей всех манифестов автоматически.

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

Уже записанный секрет **никогда не перегенерируется** при повторном запуске (`env_writer.resolve_existing_secrets`) — иначе смена `POSTGRES_PASSWORD` без сброса уже инициализированного volume просто сломает сервисы.

## Домен и TLS

Указание домена при установке — опционально. Если указан: сервис сверяет DNS A-запись домена с публичным IP сервера (дружелюбная предварительная проверка, не единственная защита), поднимает временный HTTP-only конфиг nginx, выпускает сертификат через одноразовый `certbot/certbot` контейнер (настоящая, авторитетная проверка — реальный HTTP-01 challenge), затем переключает nginx на финальный HTTPS-конфиг. Подробности — `app/dns_check.py`, `app/certbot_runner.py`, `app/nginx_setup.py`.

## Структура

```text
app/
  schema.py         пидантик-модели install.yml / shared_secrets.yml
  discovery.py      поиск install.yml по репозиторию, валидация,
                     сбор и резолв секретных ссылок
  secrets.py        генерация случайных секретов
  env_writer.py     резолв секретов + запись .env (идемпотентно)
  compose_runner.py запуск docker compose build/up, поллинг health
  dns_check.py      проверка, что домен указывает на этот сервер
  certbot_runner.py выпуск сертификата через одноразовый certbot-контейнер
  nginx_setup.py    три состояния nginx.conf (без домена / временный / финальный)
  installer.py      вся оркестрация целиком, выполняется в фоновом потоке
  state.py          потокобезопасный прогресс установки
  marker.py         маркер deploy/.installed, гейтит повторные установки
  forms.py          сбор form-полей со всех манифестов для HTML-формы
  repo_root.py      резолв корня репозитория (REPO_ROOT или вывод по пути)
  main.py           FastAPI: форма/заглушка, POST /install, GET /status
  templates/
    index.html      страница — те же шрифты/палитра, что в src/web
  health/           liveness-проверка
shared_secrets.yml
tests/
```

## Запуск тестов и проверки

```text
poetry install --no-root
poetry run pytest -q
```

Все тесты мокают `subprocess`/`socket`/`urlopen` — реальный Docker, DNS или интернет для прогона тестов не нужны.
