# File Orchestrator Service

Хранение медиа-вложений Telemax. Сервис принимает файлы потоковой загрузкой, хранит их в SeaweedFS, отдаёт обратно по запросу (тоже потоково) и подчищает блобы, когда сообщение с вложением удаляется.

## Структура

- `app/files/` — модель `File` (источник правды по вложениям), схемы, репозиторий, бизнес-логика (`service.py`), публичные роуты и `storage.py` (HTTP-клиент к SeaweedFS).
- `app/internal/` — `POST /internal/files/validate`, используется communication при отправке сообщения с `attachment_file_ids`.
- `app/events.py` — общий с communication JetStream-стрим `CHATS`: публикует `file.upload.progress` / `file.upload.completed`, подписывается на `chat.message.deleted` для удаления блобов.
- `app/health/` — health-check.

## Как это работает

- **Загрузка**: `POST /files?chat_id=...` с сырым телом запроса (без multipart) и заголовками `X-Filename`, `Content-Type`. api-gateway проксирует тело потоково (не буферизует целиком), file-orchestrator стримит его прямо в SeaweedFS через filer (`PUT /attachments/{file_id}`), раз в `upload_progress_interval_bytes` публикует `file.upload.progress` в NATS (ws-gateway разносит это подписчикам чата как `upload.progress`).
- **Скачивание**: `GET /files/{id}` — тоже потоково, file-orchestrator сам читает из SeaweedFS и отдаёт байты (осознанный выбор: полный контроль над авторизацией и доступом, а не отдавать signed URL на SeaweedFS напрямую).
- **Лимиты размера**: два уровня — админский лимит (`max_upload_size_bytes`, по умолчанию `None` = не ограничено) и физическое свободное место на диске SeaweedFS (`GET /status` у volume-сервера). Действует наименьшее из двух, проверяется как по объявленному `Content-Length`, так и по факту полученных байт в процессе стриминга.
- **Удаление**: когда сообщение удаляется, communication публикует `chat.message.deleted` со списком `attachment_file_ids`; file-orchestrator подписан на этот же subject и удаляет блобы + помечает файлы `deleted` в своей базе.
- **Авторизация**: и загрузка, и скачивание проверяют членство в чате через internal-эндпоинт communication (`GET /internal/chats/{chat_id}/members/{user_id}`), без необходимости дублировать данные о членах чата.

## Переменные окружения

См. `.env.example` — `POSTGRES_*`. Остальные (`communication_url`, `seaweedfs_filer_url`, `seaweedfs_volume_url`, `nats_port`, `max_upload_size_bytes`, `upload_progress_interval_bytes`) имеют разумные дефолты в `app/config.py`.
