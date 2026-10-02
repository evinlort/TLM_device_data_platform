# Запуск лабораторного стенда

## Что запускается

```text
sensor adapter → пакет каждые 10 секунд → SQLite outbox → HTTPS
  → POST /v1/telemetry → проверка token/device_id → PostgreSQL transaction
  → COMMIT → подтверждение → удаление из outbox
```

Сервер и агент — разные процессы. Серверу нужен PostgreSQL credential; устройству
нужен только собственный token и адрес TLM API. На устройстве нет Supabase key,
имён таблиц или пароля БД. В текущем пилоте нет dashboard, current_state,
управления исполнительными механизмами и изоляции учеников/школ.

Код агента рассчитан на Linux/Python 3.11+ (например, Linux-часть UNO Q).
Это не firmware для ESP32. Конкретный драйвер физических датчиков необходимо
подключить через `module:function`; тип платы и разводка этим кодом не угадываются.

## Подготовка Python

В корне checkout ветки `feat/device-ingestion-v1`:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -c requirements/test.txt -c requirements/server.txt '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -m 'not database'
```

Для сервера без test tools используйте `.[server]` вместо `.[test]`.
Для устройства без сервера достаточно `pip install .`; драйвер реальных датчиков
устанавливается отдельно. После изменения исходников переустановите пакет.
Все команды запуска через `python -m` работают в Bash и fish без активации venv.

## Локальная одноразовая БД для CI и разработки

Нужны Docker и Node.js (точный CI baseline: 22.23.2). Используется закреплённый
Supabase CLI 2.118.0, не автоматически скачанная latest-версия.

```bash
npm ci
npx --no-install supabase start
npx --no-install supabase db reset --local
npx --no-install supabase test db
```

**`db reset --local` удаляет локальные данные. Не выполняйте его на работающем
стенде с нужной историей.** CLI может публиковать порты на `0.0.0.0`; локальный
stack со стандартными keys, Studio и служебными API нельзя открывать в Интернет
или недоверенную сеть. Ограничьте доступ firewall/изолированной сетью Docker.
Вывод `start/status` содержит локальные credentials; не публикуйте его.

Для полного Python suite задайте `TLM_TEST_ADMIN_DSN` из локального CLI status.
GitHub workflow получает его автоматически, без печати. DB-тесты намеренно
падают без этой переменной и отказываются подключаться к нелокальным адресам.
Они создают собственные временные LOGIN/device records, выполняют настоящий TCP
HTTP и удаляют только эти test records. Они не должны запускаться на рабочей БД.

```bash
.venv/bin/python -m pytest
npx --no-install supabase stop --no-backup
```

После любого сбоя startup/test локальный stack тоже нужно остановить.
В CI cleanup выполняется через `always()`.

## Применение схемы к отдельному development-проекту

Это отдельная операция оператора, не действие обычного PR CI. Сначала подтвердите
project reference, окружение, текущую схему и migration history. Старое сообщение
«проект пустой» не является свежей проверкой. Не используйте production target.

```bash
npx --no-install supabase link --project-ref <DEV_PROJECT_REF>
npx --no-install supabase migration list
npx --no-install supabase db push --dry-run
```

После проверки плана примените `npx --no-install supabase db push`.
Никакой remote reset для подключения устройства не требуется.
Новая схема находится в `supabase/migrations/20261002010000_add_device_ingestion.sql`.
Не переписывайте старую миграцию `ingest_messages` и не подменяйте историю ручным
SQL Editor без согласования с migration history. Не публикуйте схему `tlm` через
Data API: сервер обращается к ней по PostgreSQL.

## Регистрация runtime и устройства

Создайте вне Git приватный JSON-файл `admin.secret.json` с правами `0600`,
владельцем которого является пользователь запуска:

```json
{"TLM_ADMIN_DSN": "<operator PostgreSQL connection string>"}
```

Для remote DSN обязательно `sslmode=verify-full` и доверенный root certificate
через `sslrootcert`, когда он нужен провайдеру. Используйте endpoint из панели
конкретного проекта. Не угадывайте адрес pooler/регион. Для постоянно работающего
API подходят direct connection или session pooler; runtime-тестирование с
transaction pooler в этом пилоте не заявлено.

Регистрация требует явного `--apply` и сохраняет credentials в новые файлы:

```bash
.venv/bin/python -m tlm_device_data_platform.provision --admin-config /secure/admin.secret.json --apply runtime --output /secure/runtime.secret.json
.venv/bin/python -m tlm_device_data_platform.provision --admin-config /secure/admin.secret.json --apply device --system-type <ACTUAL_SYSTEM_TYPE> --output /secure/device.secret.json
```

Для session pooler добавьте к команде `runtime` параметр
`--pooler-project-ref <DEV_PROJECT_REF>`: wire username будет `tlm_api.<ref>`,
а PostgreSQL role останется `tlm_api`. При повторной установке новая регистрация
не должна незаметно заменять существующий runtime или device. Имена и файлы
не перезаписываются. `--device-id` задаётся только для согласованного постоянного
UUID новой записи; замена контроллера не требует новой записи устройства.

Конфигурация сохраняется **до** изменения БД. При ошибке или потере ответа на
COMMIT файл остаётся для восстановления. Его наличие само по себе не означает,
что регистрация успешна. Проверьте БД перед повтором; не удаляйте файл автоматически
и не генерируйте новые credentials вслепую. Инструмент не реализует ротацию token.
Административный файл не передавать серверу или устройству.

## Запуск сервера

На API-хосте:

```bash
.venv/bin/python -m tlm_device_data_platform.serve_api --config /secure/runtime.secret.json
```

По умолчанию слушает `127.0.0.1:8000`. Для устройства в сети используйте HTTPS
reverse proxy к этому loopback-порту или запустите с `--host 0.0.0.0`,
`--ssl-certfile /secure/fullchain.pem`, `--ssl-keyfile /secure/key.pem`.
Сертификат должен соответствовать имени хоста и быть доверенным для устройства.
Небезопасный LAN HTTP требует отдельного `--allow-insecure-lan` и допустим только
в изолированной лаборатории. Не отключайте проверку сертификатов ради удобства.

`GET /health/live` — только проверка жизни процесса. Она не означает доступность
БД. API откажется записывать под owner/superuser/BYPASSRLS identity.
На рабочем стенде процесс должен управляться менеджером сервисов и рестартоваться
после сбоя; production deployment в текущий CI не включён.

## Источник датчиков и запуск агента

Установленный sensor module предоставляет функцию без аргументов:

```python
def read() -> dict[str, int | float]:
    # Read the actual configured hardware here; never return invented fallback data.
    ...
```

Каждый вызов должен возвращать реальные именованные числовые показания и
завершаться за ограниченное время. Ошибка драйвера останавливает сбор, а не
записывается как нулевое показание. Единицы определяются документацией устройства.
Сеть не блокирует сбор, но зависший sensor driver всё ещё может его остановить.

Скопируйте только `device.secret.json` на устройство, сохраните права `0600`:

```bash
.venv/bin/python -m tlm_device_data_platform.edge_agent --config /secure/device.secret.json --api-url https://<TLM_API_HOST>/v1/telemetry --sensor your_installed_driver:read
```

Адрес можно сохранить в том же JSON под ключом `TLM_API_URL`.
Для часов без синхронизации UTC добавьте `--unsynchronized-clock`: captured_at
будет null. Не выдавайте локальное неточное время за достоверное UTC.
Один процесс владеет одной очередью; другой экземпляр с тем же outbox не запускается.
По умолчанию outbox: `~/.local/state/tlm/outbox.sqlite3`, 10 000 записей.
Это ограничение пилота, не гарантия времени offline для всех устройств.

При заполнении очередь ничего не вытесняет, агент останавливается.
ACK удаляет только подтверждённое сообщение. 400/409/413/422 переводят сообщение
в quarantine, сохраняя его байты; остальные продолжают отправляться.
401/403/ошибочный endpoint/redirect требуют оператора и останавливают агент.
5xx/timeout/429 оставляют сообщение в очереди и вызывают backoff до 60 секунд;
числовой Retry-After учитывается. Нужны контроль свободного диска и резервирование
очереди: физическая поломка накопителя этим кодом не устраняется.

## Явно программная проба

Только для проверки ПО замените `--sensor` на
`tlm_device_data_platform.demo_sensor:read` и добавьте `--count 3`.
Будут три пакета через 10 секунд с `test_sensor_1` и `test_sensor_2`.
Это **не показания физических датчиков**. HTTP на localhost требует ещё
`--allow-insecure-http` у агента. В реальном режиме этот параметр не нужен.

## Приёмка физического стенда

Проверьте запись показаний правильного устройства, затем отключите его сеть,
убедитесь, что outbox растёт, восстановите сеть и проверьте опустошение pending
без дублей в БД. После рестарта проверьте отправку прежних сообщений и новый stream_id.
SQL для оператора:

```sql
SELECT device_id, message_id, stream_id, sequence_no,
       captured_at, received_at, payload
FROM tlm.telemetry_messages
WHERE device_id = '<DEVICE_UUID>'::uuid
ORDER BY received_at DESC
LIMIT 20;
```

Сортировка по received_at показывает порядок получения, **не актуальное состояние
физической установки** после replay. Таблица current_state не реализована.

До предоставления настоящего sensor driver, выбранного dev-проекта и API-хоста
проверен программный путь с локальным Supabase, а не развёрнутый физический стенд.
