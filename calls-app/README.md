# Calls App Blueprint

Стартовый каркас проекта для приложения звонков на основе React + Go microservices + LiveKit.

## Структура

- `frontend` — React клиент.
- `gateway` — публичный API gateway.
- `services/*` — микросервисы.
- `libs/*` — общие библиотеки.
- `deploy/*` — docker compose, Caddy, LiveKit и env.

## Быстрый старт

1. Скопировать `.env.example` и заполнить значения.
2. Заполнить `deploy/env/*.env`.
3. Поднять инфраструктуру через `docker compose -f deploy/docker-compose.yml up -d`.
