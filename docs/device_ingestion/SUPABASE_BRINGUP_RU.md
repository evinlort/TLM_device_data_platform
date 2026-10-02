# От checkout до записи в Supabase: руководство по пройденному запуску

**Контрольная дата: 2 октября 2026 года.** Ветка оператора:
`feat/esp32-ultrasonic-micropython`. Проверенный при подготовке руководства
исходный commit: `ebe90f24e7d7b1a06f85a543582b5f8e64510e25`.

Документ описывает путь, пройденный на Ubuntu: миграции, Python-окружение,
Session pooler, проверенный TLS, provisioning, запуск TLM API и запись
**программных demo-показаний** в удалённый Supabase. Это не отчёт о работе
HC-SR04: физическая ESP32 на этой стадии ещё не подключалась.

Результаты оператора собраны в разделе 12. Остальные разделы — порядок повторного
запуска, с устранёнными лишними проверками и явно отмеченными исправлениями.
Безопасные диагностические блоки ниже оформлены заново; не каждый из них
исполнялся в сессии именно в таком виде. Проверка кода не заменяет повторную
проверку конкретного компьютера, проекта и credentials.

> **Область этого документационного изменения.** В исходном commit Linux
> `HTTPSender` всё ещё использует `timeout=5`. Оператор локально изменил его
> на `15`, проверил тестами и переустановил пакет. Раздел 8 воспроизводит эту
> правку. Публикация данного руководства сама по себе не меняет Python-код.

## Содержание

1. [Результат и границы](#scope)
2. [Checkout и окружение](#checkout)
3. [Миграции](#migrations)
4. [Session pooler, пароль и CA](#connection)
5. [Приватная конфигурация администратора](#admin)
6. [Регистрация runtime](#runtime)
7. [Регистрация устройства](#device)
8. [Локальное исправление таймаута](#timeout)
9. [Запуск API и новый demo-пакет](#api)
10. [Диагностика и повторная доставка](#diagnostics)
11. [Проверка в Supabase](#verification)
12. [Зафиксированные результаты и продолжение](#handoff)
13. [Источники](#sources)

<a id="scope"></a>
## 1. Результат и границы

Проверенный маршрут:

```text
Ubuntu: demo_sensor:read
  -> Linux edge_agent
  -> SQLite outbox
  -> HTTP http://127.0.0.1:8000/v1/telemetry
  -> TLM API / restricted runtime role
  -> TLS verify-full / Supabase Session pooler
  -> PostgreSQL transaction / COMMIT
  -> ACK
  -> removal from local outbox
```

HTTP без TLS применён **только на loopback одного компьютера**. Соединение
API с удалённым PostgreSQL использует `sslmode=verify-full` и доверенный CA.
Этот запуск не публикует API в Интернет и не открывает его для ESP32.

| Компонент | Для чего нужен |
| --- | --- |
| `tlm.devices` | Регистрация устройства, тип системы, активность |
| `tlm.device_credentials` | SHA-256 индивидуального device token |
| `tlm.telemetry_messages` | История сообщений с JSONB `payload` |
| `tlm_ingest` | Группа прав без возможности LOGIN |
| `tlm_api` | Ограниченный LOGIN для процесса API |
| `.secrets/admin.secret.json` | Административный DSN, только для оператора |
| `.secrets/runtime.secret.json` | DSN ограниченного пользователя, только для API |
| `.secrets/esp32-hcsr04.secret.json` | UUID и token устройства |
| `.secrets/supabase-ca.crt` | Доверенный CA для соединения API с PostgreSQL |

На плату нельзя переносить административный DSN, runtime DSN или Supabase
`service_role`/secret key. CA базы данных также не следует автоматически считать
подходящим CA будущего HTTPS TLM API: это два разных TLS-соединения.

**Не начинать повторное развёртывание с удаления данных.** Не выполнять remote
reset, не удалять outbox ради устранения `pending` и не запускать provisioning
повторно после неопределённого результата COMMIT. Не добавлять схему `tlm` в
exposed schemas Data API: этот backend работает непосредственно через PostgreSQL.
Контракт и ограничения: [PROTOCOL_V1.md](PROTOCOL_V1.md).

<a id="checkout"></a>
## 2. Checkout и Python-окружение

Команды ниже выполняются из корня репозитория. Shell-блоки рассчитаны на **Bash**;
для их выполнения из fish сначала открыть `bash`. Заменять `YOUR_*` фактическими
несекретными параметрами. Пароли и token в shell-команды не вставлять.

Для уже существующего checkout:

```bash
pwd
git branch --show-current
git status --short
```

В сессии рабочая директория была `~/Dev/TLM_device_data_platform`, ветка —
`feat/esp32-ultrasonic-micropython`. Не переключать ветки поверх несохранённых
изменений и не использовать `reset --hard`. В частности, локальная правка
таймаута из раздела 8 должна быть сохранена.

Проверить Python:

```bash
python3 --version
```

В проекте требуется Python 3.11+, у оператора работал Python 3.11.9. Если `.venv`
отсутствует, создать его; существующее окружение без причины не пересоздавать:

```bash
python3 -m venv .venv
```

Проверить интерпретатор и установить текущий checkout с server-зависимостями:

```bash
.venv/bin/python --version
.venv/bin/python -m pip install -c requirements/server.txt '.[server]'
.venv/bin/python -m pip check
.venv/bin/python -m tlm_device_data_platform.provision --help
```

Активация venv не требуется. Ожидается справка с подкомандами `runtime` и `device`.

**Встреченная проблема:** `pip show` показывал пакет версии `0.0.0`, но модуль
`provision` отсутствовал. Была установлена старая wheel-копия. Номер `0.0.0`
не различал старый и новый код. После установки текущего checkout модуль появился.
Изменение файла в `src/` не обновляет уже установленную wheel-копию: после правки
нужно переустановить пакет. Исходные зависимости: [pyproject.toml](../../pyproject.toml).

<a id="migrations"></a>
## 3. Применить миграции к выбранному Supabase-проекту

Перед записью убедиться, что выбран именно разрешённый development-проект,
проверены существующие таблицы и история миграций. Пустая колонка `Remote` не
доказывает, что в базе нет таблиц, созданных вручную.

Подготовить закреплённый в репозитории CLI и привязать проект:

```bash
npm ci
npx --no-install supabase login
npx --no-install supabase link --project-ref YOUR_DEV_PROJECT_REF
npx --no-install supabase migration list
npx --no-install supabase db push --dry-run
```

В пройденной сессии использовался CLI `2.118.0`. Уведомление о новой версии не
было причиной обновлять CLI, lockfile или pip посреди диагностики. Для уже
авторизованного и привязанного checkout повторный `login`/`link` не обязателен;
сначала проверить его целевой project ref, а не полагаться на прошлую сессию.

Ожидаемый план для исходно неприменённых миграций:

```text
20260930233000_create_ingest_messages.sql
20261002010000_add_device_ingestion.sql
```

После проверки плана выполнить **один раз**:

```bash
npx --no-install supabase db push
npx --no-install supabase migration list
```

Контрольная таблица:

```text
Local            | Remote
20260930233000   | 20260930233000
20261002010000   | 20261002010000
```

Старую fixture-миграцию не переписывать. Для HC-SR04 отдельная таблица или новая
миграция не нужны: `distance_cm` позже будет полем JSONB `payload`. В этой сессии
физических `distance_cm` ещё нет. Файлы: [migrations](../../supabase/migrations/).

<a id="connection"></a>
## 4. Выбрать Session pooler, проверить пароль и подготовить CA

### 4.1. Метод подключения

Открыть проект в Supabase Dashboard → **Connect**. В сессии команда

```bash
ip -6 route show default
```

не показала маршрут по умолчанию IPv6. Был выбран **Session pooler**. Это не
универсальный тест всех вариантов IPv6-маршрутизации, а основание выбранного
пути в данном стенде. Transaction pooler в пройденном запуске не использовался.

Из окна **Session pooler** взять точные `host`, `port`, `dbname` и `user`.
Для данного режима порт был `5432`, административный user имеет форму
`postgres.<PROJECT_REF>`. Не вычислять pooler hostname по региону, не брать его
из чужого примера и не заменять hostname одним из IP из сообщения об ошибке.
См. [официальное описание подключений](https://supabase.com/docs/guides/database/connecting-to-postgres).

### 4.2. Секреты и сертификат

Подготовить локальный каталог и исключить его целиком из Git этого checkout:

```bash
mkdir -p .secrets
chmod 700 .secrets
printf '\n.secrets/\n' >> .git/info/exclude
git ls-files -- .secrets
```

Последняя команда не должна вывести файлов. `.gitignore` уже исключает
`*.secret.json`; дополнительное локальное правило защищает весь каталог.
Ignore-правило не удаляет ранее отслеживаемые файлы из индекса или истории.
Если они обнаружены, остановиться и отдельно проверить возможную утечку.
Права `600`/`700` ограничивают доступ, но не шифруют содержимое.

В Dashboard → Database settings → **SSL Configuration** нажать
**Download certificate**. В сессии файл назывался `prod-ca-2021.crt`:

```bash
cp ~/Downloads/prod-ca-2021.crt .secrets/supabase-ca.crt
chmod 600 .secrets/supabase-ca.crt
```

Использовать фактическое имя скачанного файла. Не скачивать доверенный CA
из случайной ссылки и не извлекать его из непроверенного соединения как
единственный источник доверия. Не требуется переключать SSL enforcement
ради скачивания сертификата.

В сессии `sslrootcert=system` не позволил проверить цепочку. Рабочая конфигурация
получилась с CA из Dashboard и `verify-full`. Это наблюдение этого компьютера,
не утверждение о неработоспособности системного trust store во всех установках.
См. [Supabase: PSQL с сертификатом](https://supabase.com/docs/guides/database/psql).

### 4.3. Проверка предполагаемого пароля без его публикации

При установленном `psql` проверить пароль интерактивно. В следующей команде
нет пароля; `-W` запросит его без отображения символов:

```bash
psql -W "host=YOUR_POOLER_HOST port=5432 dbname=postgres user=postgres.YOUR_DEV_PROJECT_REF sslmode=verify-full sslrootcert='$(pwd)/.secrets/supabase-ca.crt' connect_timeout=5" -c 'SELECT current_user;'
```

`password authentication failed` означает неуспешную аутентификацию. Сначала
проверить выбранные project, host и username; не делать вывод только о пароле.
Если пароль неизвестен, оператор может сбросить **Database password** в Dashboard.
Это не пароль аккаунта Supabase. Перед сбросом учесть другие приложения,
использующие старый пароль: их конфигурации потребуется обновить. После сброса
повторить проверку. Пароль не присылать в чат и не сохранять в shell history.

<a id="admin"></a>
## 5. Создать и проверить `admin.secret.json`

### 5.1. Финальные требования, без промежуточного `sslmode=require`

Конфигурация содержит один ключ `TLM_ADMIN_DSN`. Для удалённой базы
[validate_dsn()](../../src/tlm_device_data_platform/postgres_ingestion.py)
требует `sslmode=verify-full`. Просто успешное подключение через
`psycopg.connect()` с `sslmode=require` не означает, что DSN примет provisioning.

В URI финальные параметры выглядят так:

```text
?sslmode=verify-full&sslrootcert=/ABSOLUTE/PATH/.secrets/supabase-ca.crt
```

Путь должен существовать на **API-компьютере**. Не копировать домашний каталог
из чужой команды: вычислить свой абсолютный путь. Внутри строки DSN `~`
не следует использовать вместо полного пути.

При ручной сборке URI пароль должен быть percent-encoded. В сессии необработанный
`%` вызвал `invalid percent-encoded token`; заменой литерального `%` на `%25`
удалось исправить конкретный пароль. Это не универсальный способ кодирования:
другие специальные символы также требуют обработки, а уже закодированный пароль
нельзя кодировать повторно. Полную URI кодировать как пароль тоже нельзя.

### 5.2. Безопасный вариант создания нового файла

Следующий блок — переработанная инструкция для повторного развёртывания:
`getpass` принимает **исходный** пароль, `make_conninfo()` собирает DSN из отдельных
полей, а `write_private_config()` создаёт новый файл с `0600` и отказывается
перезаписывать существующий. Это устраняет ручное редактирование password-части.
Получится допустимый для libpq DSN вида `key=value`, а не URI; TLM принимает
оба формата. [Документация make_conninfo](https://www.psycopg.org/psycopg3/docs/api/conninfo.html).

**Уже работающий `admin.secret.json` не пересоздавать.** Сразу перейти к проверке
5.3. Для нового файла выполнить:

```bash
.venv/bin/python -c '
from getpass import getpass
from pathlib import Path
from psycopg.conninfo import make_conninfo
from tlm_device_data_platform.postgres_ingestion import validate_dsn
from tlm_device_data_platform.private_config import write_private_config

try:
    target = Path(".secrets/admin.secret.json")
    if target.exists():
        raise FileExistsError("Configuration already exists")
    ca = Path(".secrets/supabase-ca.crt").resolve(strict=True)
    host = input("Session pooler host from Connect: ").strip()
    port = input("Session pooler port from Connect: ").strip()
    user = input("Session pooler user from Connect: ").strip()
    database = input("Database name from Connect: ").strip()
    if not all((host, port, user, database)):
        raise ValueError("Connection fields must not be empty")
    password = getpass("Database password (raw, not URL-encoded): ")
    if not password:
        raise ValueError("Password must not be empty")
    dsn = make_conninfo(host=host, port=port, user=user, dbname=database,
                        password=password, sslmode="verify-full", sslrootcert=str(ca))
    validate_dsn(dsn)
    write_private_config(target, {"TLM_ADMIN_DSN": dsn})
    print("ADMIN CONFIG SAVED; no credentials printed")
except Exception as error:
    print("CONFIG FAILED:", type(error).__name__)
    raise SystemExit(1)
'
```

Поля брать строго из Connect, без заглушек. Блок не соединяется с БД и не меняет
её. На сервер или ESP32 этот административный файл не копировать.

### 5.3. Проверка без раскрытия DSN

```bash
stat -c '%a %n' .secrets/admin.secret.json
.venv/bin/python - <<'PY'
from pathlib import Path
import psycopg
from tlm_device_data_platform.postgres_ingestion import validate_dsn
from tlm_device_data_platform.private_config import load_private_config

try:
    config = load_private_config(Path(".secrets/admin.secret.json"), {"TLM_ADMIN_DSN"})
    dsn = config["TLM_ADMIN_DSN"]
    validate_dsn(dsn)
    with psycopg.connect(dsn, connect_timeout=5) as connection:
        connection.execute("SELECT 1").fetchone()
    print("VERIFY-FULL CONNECTION OK")
except Exception as error:
    print("CONNECTION FAILED:", type(error).__name__)
    raise SystemExit(1)
PY
```

Ожидаются `600` и `VERIFY-FULL CONNECTION OK`. Здесь ошибки намеренно не печатают
сырой DSN или traceback: ошибка URI-парсера способна раскрыть часть пароля.
При неуспехе пользоваться таблицей диагностики в разделе 10, а не ослаблять TLS.

<a id="runtime"></a>
## 6. Зарегистрировать и проверить runtime API

Это операция **записи в выбранный Supabase-проект**. Для уже зарегистрированного
runtime повторный provisioning не выполнять. Сначала проверить имеющиеся
`.secrets/runtime.secret.json` и роль `tlm_api`.

Для новой регистрации:

```bash
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config .secrets/admin.secret.json \
  --apply runtime \
  --pooler-project-ref YOUR_DEV_PROJECT_REF \
  --output .secrets/runtime.secret.json
```

`YOUR_DEV_PROJECT_REF` — ref того же проекта, чей endpoint использован в admin
DSN. Параметр задаёт wire username `tlm_api.<PROJECT_REF>` для Session pooler;
`SELECT current_user` внутри PostgreSQL при этом возвращает `tlm_api`.

Контрольный результат:

```text
Provisioning committed. Private configuration saved; no credentials printed.
```

Проверить файл и runtime-соединение **до запуска API**:

```bash
stat -c '%a %n' .secrets/runtime.secret.json
.venv/bin/python - <<'PY'
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from tlm_device_data_platform.postgres_ingestion import PostgresTelemetryRepository, validate_dsn
from tlm_device_data_platform.private_config import load_private_config

try:
    config = load_private_config(Path(".secrets/runtime.secret.json"), {"TLM_DATABASE_DSN"})
    dsn = config["TLM_DATABASE_DSN"]
    validate_dsn(dsn)
    with psycopg.connect(dsn, connect_timeout=5, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL statement_timeout = '5s'")
        row = connection.execute(
            "SELECT current_user AS role, pg_has_role(current_user, %s, %s) AS member",
            ("tlm_ingest", "MEMBER"),
        ).fetchone()
        PostgresTelemetryRepository._check_runtime_role(connection)
        if row is None or row["role"] != "tlm_api" or not row["member"]:
            raise ValueError("Unexpected runtime identity")
        print("ROLE:", row["role"])
        print("MEMBER tlm_ingest:", row["member"])
    print("RUNTIME CHECK OK")
except Exception as error:
    print("RUNTIME CHECK FAILED:", type(error).__name__)
    raise SystemExit(1)
PY
```

В сессии отдельно подтверждены `('tlm_api', True)` и отсутствие запрещённых
привилегий: `(False,)`. Блок выше объединяет эти проверки; приватный метод
используется здесь как диагностика конкретной версии, не как публичный API.

**При `Provisioning failed`: остановиться.** Инструмент сохраняет конфигурацию
до изменения БД. Наличие файла не доказывает успешный COMMIT, отсутствие файла
не следует использовать как единственную проверку состояния. Не удалять
сохранённые credentials и не генерировать новые вслепую.

Через SQL Editor или административный `psql` проверить без записи:

```sql
SELECT rolname, rolcanlogin
FROM pg_roles
WHERE rolname IN ('tlm_api', 'tlm_ingest');
```

До первой успешной регистрации в сессии было только `tlm_ingest | f`. После
успеха должна существовать и LOGIN-роль `tlm_api`. Проверить причину ошибки и
согласованность файла/БД перед любой повторной попыткой.

<a id="device"></a>
## 7. Зарегистрировать устройство и проверить token

Для новой записи устройства:

```bash
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config .secrets/admin.secret.json \
  --apply device \
  --system-type esp32-hcsr04 \
  --output .secrets/esp32-hcsr04.secret.json
stat -c '%a %n' .secrets/esp32-hcsr04.secret.json
```

Ожидаются сообщение об успешном COMMIT и права `600`. UUID и случайный token
создаёт инструмент. `system-type=esp32-hcsr04` — метка регистрации, а не
доказательство подключения физического датчика. В БД хранится hash token;
исходный token сохраняется в приватном файле.

Проверить credential через ограниченную роль и сопоставить UUID с файлом:

```bash
.venv/bin/python - <<'PY'
import hashlib
from pathlib import Path
import psycopg
from tlm_device_data_platform.private_config import load_private_config

try:
    runtime = load_private_config(Path(".secrets/runtime.secret.json"), {"TLM_DATABASE_DSN"})
    device = load_private_config(Path(".secrets/esp32-hcsr04.secret.json"),
                                 {"TLM_DEVICE_ID", "TLM_DEVICE_TOKEN"})
    digest = hashlib.sha256(device["TLM_DEVICE_TOKEN"].encode("ascii")).digest()
    with psycopg.connect(runtime["TLM_DATABASE_DSN"], connect_timeout=5) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL statement_timeout = '5s'")
        row = connection.execute("""
            SELECT c.device_id, d.system_type, d.is_active
            FROM tlm.device_credentials c
            JOIN tlm.devices d USING (device_id)
            WHERE c.token_sha256 = %s AND c.revoked_at IS NULL
              AND (c.expires_at IS NULL OR c.expires_at > clock_timestamp())
              AND d.is_active
        """, (digest,)).fetchone()
    matches = row is not None and str(row[0]) == device["TLM_DEVICE_ID"]
    print("CREDENTIAL MATCH:", matches)
    if not matches:
        raise SystemExit(1)
    print("SYSTEM TYPE:", row[1])
    print("ACTIVE:", row[2])
except Exception as error:
    print("CREDENTIAL CHECK FAILED:", type(error).__name__)
    raise SystemExit(1)
PY
```

Никакие token/hash не печатаются. При уже существующем устройстве пользоваться
его сохранённой конфигурацией, а не выполнять эту регистрацию повторно.

<a id="timeout"></a>
## 8. Воспроизвести локальное исправление HTTP-таймаута

### 8.1. Что измерено

| Проверка оператора | Время |
| --- | --- |
| Подключение runtime к PostgreSQL | 2.14 s |
| Первый `SELECT 1` после подключения | 0.82 s |
| `PostgresTelemetryRepository.accept()` для повтора | 5.74 s |
| HTTP-запрос повтора с увеличенным ожиданием | 6.03 s |

Это отдельные измерения данного стенда, не SLA и не средняя производительность
Supabase. Первый `SELECT 1` при обычном psycopg-соединении может включать
неявный `BEGIN`; его время нельзя объявлять временем одного сетевого round trip.

Изначальный Linux sender использовал:

```python
response = self._opener.open(request, timeout=5)
```

Он несколько раз завершался `network_error`, хотя повтор с ожиданием 30 секунд
получил `200 duplicate`. После локальной замены на `15` подтверждение дошло,
очередь очистилась, затем успешно прошёл новый demo-пакет.

`urllib` задаёт таймаут блокирующих операций, **не гарантированный общий deadline
всего запроса**. Поэтому нельзя объявлять любой запрос длительнее пяти секунд
заведомо невозможным; вывод здесь основан на повторяемом результате стенда.
См. [urllib.request](https://docs.python.org/3.11/library/urllib.request.html).

### 8.2. Точечная правка, без изменения DB/SQLite таймаутов

Посмотреть текущий diff и строки **исходника**, не редактировать `site-packages`:

```bash
git diff -- src/tlm_device_data_platform/edge_agent.py
grep -n 'opener.open' src/tlm_device_data_platform/edge_agent.py
```

Если в исходнике ещё `5`, выполнить контролируемую замену. Если уже `15`, блок
ничего не меняет. При другой структуре кода он останавливается:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path

path = Path("src/tlm_device_data_platform/edge_agent.py")
source = path.read_text(encoding="utf-8")
old = "self._opener.open(request, timeout=5)"
new = "self._opener.open(request, timeout=15)"
if source.count(old) == 1 and new not in source:
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    print("HTTP TIMEOUT UPDATED: 5 -> 15")
elif source.count(new) == 1 and old not in source:
    print("HTTP TIMEOUT ALREADY 15")
else:
    raise SystemExit("Unexpected source; no change made")
PY
```

Это локальное изменение рабочего дерева, не автоматически выполненный commit.
`connect_timeout=5` в PostgreSQL/provisioning и `sqlite3.connect(timeout=5)`
имеют другое назначение; глобальная замена `5` на `15` недопустима.

### 8.3. Проверить именно новый исходник, затем переустановить

Если test-зависимости ещё не установлены:

```bash
.venv/bin/python -m pip install -c requirements/test.txt -c requirements/server.txt '.[test]'
```

Далее:

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_edge_agent.py \
  tests/test_edge_response_failures.py \
  tests/test_pr2_edge_regressions.py -q
```

Оператор получил **`36 passed in 2.59s`**. Это проверка существующих выбранных
тестов после изменения, не новый TDD-цикл и не доказательство поведения при
любой сетевой задержке. Полный database suite нельзя направлять на этот hosted
проект: он предназначен для отдельной одноразовой локальной БД.

Установить обновлённый исходник и проверить реально импортируемую копию:

```bash
.venv/bin/python -m pip install -c requirements/server.txt '.[server]'
.venv/bin/python -m pip check
.venv/bin/python - <<'PY'
import inspect
from tlm_device_data_platform.edge_agent import HTTPSender

print("MODULE:", inspect.getfile(HTTPSender))
for line in inspect.getsource(HTTPSender.send).splitlines():
    if "opener.open" in line:
        print(line.strip())
PY
```

Ожидается `timeout=15`. При будущих изменениях серверного кода перезапускать
процесс API: переустановка пакета не заменяет уже импортированный код процесса.

**Ограничение правки:** `run_agent()` по-прежнему имеет `drain_seconds=10` и
`worker.join(timeout=6)`; это не согласованный общий бюджет выполнения.
Работа новых тестов и текущего demo подтверждена, но медленные/частичные ответы
и завершение worker требуют отдельных regression-тестов. В ESP32
[HTTPTransport.post()](../../firmware/esp32_micropython/tlm_http.py)
содержит `asyncio.wait_for(..., 10)` — его в этой сессии не меняли и на плате
не проверяли. Не увеличивать вместе с ним таймауты DNS/NTP или ECHO вслепую.

<a id="api"></a>
## 9. Запустить API и отправить новый demo-пакет

### 9.1. Терминал A — API

```bash
.venv/bin/python -m tlm_device_data_platform.serve_api \
  --config .secrets/runtime.secret.json
```

Ожидается:

```text
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Оставить терминал работающим. Запуск процесса ещё не доказывает запись в БД.
В [serve_api.py](../../src/tlm_device_data_platform/serve_api.py) явно установлено
`access_log=False`. **Отсутствие строк GET/POST не доказывает, что API не получил
запрос.** Ранний такой вывод при диагностике был неверным.

### 9.2. Терминал B — две проверки доступности

```bash
curl -i --max-time 10 http://127.0.0.1:8000/health/live
```

Ожидаются `200 OK` и `{"status":"alive"}`. Это только liveness, не проверка БД.

```bash
curl -i --max-time 10 -X POST \
  -H 'Content-Type: application/json' \
  --data '{}' \
  http://127.0.0.1:8000/v1/telemetry
```

Ожидается `401 Unauthorized`: device token намеренно не передан. Такой запрос
не проверяет путь записи валидного сообщения. `curl` без `--fail` может завершиться
с exit code `0` при HTTP 401. `$?` относится только к непосредственно предыдущей
команде, не к агенту, запущенному несколько команд назад.

### 9.3. Один новый demo-пакет

Во втором терминале, также из корня checkout:

```bash
.venv/bin/python -m tlm_device_data_platform.edge_agent \
  --config .secrets/esp32-hcsr04.secret.json \
  --api-url http://127.0.0.1:8000/v1/telemetry \
  --sensor tlm_device_data_platform.demo_sensor:read \
  --count 1 \
  --allow-insecure-http
printf 'EXIT_CODE=%s\n' "$?"
```

Это **одна новая программная проба**, не HC-SR04. Контрольный результат:

```text
INFO:__main__:Remaining outbox records by state: {}
EXIT_CODE=0
```

`--count 1` ограничивает число новых проб; ранее накопленный outbox также
обрабатывается. `--count 0` означает непрерывный сбор, а не «только отправить
очередь». Для уже имеющегося `pending` не создавать новые пробы многократным
повторением команды: перейти к разделу 10.

В данной сессии demo-пакеты отправлялись с credential будущего ESP32. Поэтому
одна и та же запись устройства содержит тестовую историю. Не называть её
физическими измерениями и не удалять автоматически при переходе к плате.

<a id="diagnostics"></a>
## 10. Диагностика без утечки секретов и потери очереди

### 10.1. Короткая таблица причин

| Наблюдение | Что проверить и чего не делать |
| --- | --- |
| `No module named ...provision` | Установить текущий checkout в нужный `.venv`; `pip show` с версией `0.0.0` недостаточно |
| `invalid percent-encoded token` | Формат password-части URI; предпочтительно собрать DSN через `make_conninfo`; не публиковать сырой traceback |
| `Provisioning failed (ValueError)` | Локальную конфигурацию, `validate_dsn()`, `verify-full`; ошибка не обязательно означает обращение к БД |
| `root.crt does not exist` | Явно указать абсолютный `sslrootcert` |
| `certificate verify failed` | CA, hostname, путь и время компьютера; не отключать проверку TLS |
| `pending: 1` | Подтверждения ещё нет; сообщение уже может находиться в Supabase |
| `error=None` у pending | Это не доказательство отсутствия попыток: поле `error` заполняется при quarantine, а retry его не обновляет |
| `network_error` | Sender объединяет несколько типов сетевых исключений; это не точная первопричина |
| Пустой терминал Uvicorn | Access-log отключён в `serve_api.py` |
| Файл `.lock` остался | Сам файл не доказывает, что блокировка удерживается живым процессом |
| `duplicate` | Совпадающее сообщение уже сохранено; не создавать для повтора новый `message_id` |

### 10.2. Прочитать состояние SQLite без отдельного `sqlite3` CLI

Агент должен быть остановлен. API можно оставить работающим. Скрипт открывает
существующую БД в read-only режиме и не создаёт пустую вместо отсутствующей:

```bash
.venv/bin/python - <<'PY'
from contextlib import closing
from pathlib import Path
import sqlite3

path = Path.home() / ".local/state/tlm/outbox.sqlite3"
if not path.is_file():
    raise SystemExit("Outbox not found; no database created")
with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
    for row in connection.execute("SELECT id, state, error FROM messages ORDER BY id"):
        print(row)
PY
```

В сессии было `(1, 'pending', None)`. `body` и token для этой проверки не нужны.

### 10.3. Повторить доставку одного существующего сообщения

**Оставить API запущенным; остановить все экземпляры edge agent для этой очереди.**
Блок использует ту же файловую блокировку, что агент, и не вызывает demo reader.
Новые ID не создаются. Если сообщения ещё нет в Supabase, попытка может вставить
его; если оно уже есть — ожидается duplicate ACK. Только валидный ACK разрешает
удаление из локального outbox.

```bash
.venv/bin/python - <<'PY'
import fcntl
import os
from pathlib import Path
from uuid import UUID
from tlm_device_data_platform.edge_agent import Outbox, HTTPSender, deliver_one
from tlm_device_data_platform.private_config import load_private_config

try:
    config = load_private_config(Path(".secrets/esp32-hcsr04.secret.json"),
                                 {"TLM_DEVICE_ID", "TLM_DEVICE_TOKEN"})
    path = Path.home() / ".local/state/tlm/outbox.sqlite3"
    if not path.is_file():
        raise FileNotFoundError("Existing outbox required")
    descriptor = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        outbox = Outbox(path, UUID(config["TLM_DEVICE_ID"]), 10000)
        sender = HTTPSender("http://127.0.0.1:8000/v1/telemetry",
                            config["TLM_DEVICE_TOKEN"], allow_insecure_http=True)
        result = deliver_one(outbox, sender)
        print("action =", result.action)
        print("reason =", result.reason)
        print("remaining =", outbox.counts())
        if result.action not in {"ack", "idle"}:
            raise SystemExit(2)
except Exception as error:
    print("DELIVERY FAILED:", type(error).__name__)
    raise SystemExit(1)
PY
```

Успешный результат оператора после исправления таймаута:

```text
action = ack
reason =
remaining = {}
```

`idle` означает, что pending-сообщений уже нет; проверить `remaining`, поскольку
в очереди могут оставаться quarantined-записи. Не удалять их как «мусор».

### 10.4. Измерить ожидание HTTP без изменения исходного пакета

Только если `pending` сохранился и нужно повторить измерение. API работает,
агент остановлен. Блок читает существующий пакет, делает один POST с ожиданием
30 секунд и печатает только статус/время. **Он не подтверждает и не очищает
локальную очередь.** POST может записать пакет в Supabase.

```bash
.venv/bin/python - <<'PY'
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from tlm_device_data_platform.private_config import load_private_config

started = time.monotonic()
try:
    device = load_private_config(Path(".secrets/esp32-hcsr04.secret.json"),
                                 {"TLM_DEVICE_ID", "TLM_DEVICE_TOKEN"})
    path = Path.home() / ".local/state/tlm/outbox.sqlite3"
    if not path.is_file():
        raise FileNotFoundError("Existing outbox required")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        item = connection.execute(
            "SELECT body FROM messages WHERE state='pending' ORDER BY id LIMIT 1"
        ).fetchone()
    if item is None:
        raise SystemExit("No pending message; nothing sent")
    request = Request("http://127.0.0.1:8000/v1/telemetry", data=item[0], method="POST",
                      headers={"Authorization": "Bearer " + device["TLM_DEVICE_TOKEN"],
                               "Content-Type": "application/json"})
    started = time.monotonic()
    with urlopen(request, timeout=30) as response:
        raw = response.read(4097)
        receipt = json.loads(raw) if len(raw) <= 4096 else {}
        status = receipt.get("status") if isinstance(receipt, dict) else None
        print("HTTP", response.status)
        print("RECEIPT_STATUS", status if status in {"stored", "duplicate"} else "unrecognized")
except HTTPError as error:
    print("HTTP", error.code)
    raise SystemExit(1)
except Exception as error:
    print("REQUEST FAILED:", type(error).__name__)
    raise SystemExit(1)
finally:
    print("SECONDS", round(time.monotonic() - started, 2))
PY
```

В сессии этот путь получил `HTTP 200`, `duplicate`, `6.03 s`. Проверять полную
согласованность ACK и удалять запись должен штатный `deliver_one()`, не этот
измерительный скрипт. Не заменять им постоянный агент.

### 10.5. Что показала прямая проверка DB-слоя

При диагностике оператор вызвал `PostgresTelemetryRepository.accept()` на том
же сохранённом пакете и получил:

```text
DB ACCEPT OK
MESSAGE MATCH: True
DUPLICATE: True
```

Это **не read-only операция**: такой вызов может вставить ещё не сохранённый
пакет. `duplicate=True` подтвердил наличие совпадающего сообщения в БД; он не
позволяет установить, какая именно предыдущая попытка сделала первую вставку.
В сочетании с поздним HTTP ACK и итоговым SELECT это объяснило ситуацию:
истечение клиентского ожидания не отменяет уже выполненный серверный COMMIT.

<a id="verification"></a>
## 11. Проверить строки непосредственно в Supabase

В Dashboard → **SQL Editor** выполнить чтение, заменив `DEVICE_UUID` UUID
своего устройства. UUID — не token. Его можно увидеть в `tlm.devices` через
Dashboard, не выводя целиком приватный JSON-файл.

```sql
SELECT
    device_id,
    message_id,
    stream_id,
    sequence_no,
    received_at,
    payload
FROM tlm.telemetry_messages
WHERE device_id = 'DEVICE_UUID'::uuid
ORDER BY received_at DESC
LIMIT 5;
```

В контрольном выводе сессии были две строки с разными `message_id`, временем
`2026-10-02 18:06:20.306874+00` и `2026-10-02 18:34:00.610898+00`, с payload:

```json
{"test_sensor_1": 21.5, "test_sensor_2": 48}
```

Это известные значения **demo adapter**, не измерения расстояния. Две строки
с `sequence_no=1` допустимы для разных `stream_id`: каждый новый запуск агента
начинает новый поток. Поэтому диагностический SELECT выше включает `stream_id`.

Проверка отсутствия повторных строк по идентификатору сообщения:

```sql
SELECT device_id, message_id, count(*)
FROM tlm.telemetry_messages
WHERE device_id = 'DEVICE_UUID'::uuid
GROUP BY device_id, message_id
HAVING count(*) > 1;
```

Ожидается ноль строк; уникальность также защищена первичным ключом.
`received_at` — время первой вставки на часах БД, **не время COMMIT, измерения
или последнего повтора**. Сортировка по нему не превращает историю в current state.

<a id="handoff"></a>
## 12. Зафиксированные результаты и точка продолжения

### 12.1. Что действительно выполнил оператор

| Этап | Подтверждение из сессии |
| --- | --- |
| Обе миграции | Local и Remote содержат одинаковые две версии |
| Admin → Supabase | `VERIFY-FULL CONNECTION OK` с CA из Dashboard |
| Runtime provisioning | Успешный COMMIT; файл `600` |
| Runtime-соединение | `RUNTIME DB CONNECTION OK` |
| Права runtime | `('tlm_api', True)` и `forbidden=False` |
| Device provisioning | Успешный COMMIT; файл `600` |
| Device credential | Найден, `system_type=esp32-hcsr04`, `active=True` |
| Локальная правка Linux timeout | `5 -> 15`, 36 выбранных тестов прошли |
| Установленная wheel-копия | Подтверждён `opener.open(..., timeout=15)` |
| Повторная доставка | `action=ack`, `remaining={}` |
| Новый demo-пакет | `Remaining outbox records by state: {}` |
| Проверка в Dashboard | Две demo-строки в `tlm.telemetry_messages` |

Это результаты, предоставленные оператором, а не новый запуск его компьютера
или hosted-проекта при написании руководства. Они не являются статусом CI
любого будущего commit. При сбое восстанавливать нужный этап, не начинать
всю процедуру с provisioning или миграций.

### 12.2. Что ещё не сделано

Реальная ESP32, модель платы, USB-порт, MicroPython, подключение HC-SR04,
доступ с Wi-Fi к TLM API и реальные записи `distance_cm` **ещё не проверены**.
API пока привязан к `127.0.0.1`: этот адрес на ESP32 означал бы саму ESP32,
а не компьютер. Домен/сертификат HTTPS API или отдельно разрешённый изолированный
LAN-режим должны быть настроены следующим этапом.

Здесь также не реализованы production deployment, connection pooling в TLM API,
новый общий бюджет таймаутов, изоляция учеников/школ, dashboard и current state.
Увеличение таймаута не заменяет оптимизацию соединений и измерение задержек.

### 12.3. Следующий шаг после этого руководства

Подключить плату по USB и получить список устройств:

```bash
lsusb
```

USB-UART bridge помогает выбрать следующий диагностический шаг, но не всегда
однозначно определяет модель ESP32. До прошивки сверить маркировку модуля/платы
и её документацию. Не стирать flash только на основании найденного USB bridge.

Продолжение: [ESP32 + HC-SR04: схема, USB, MicroPython и приёмка](../../firmware/esp32_micropython/README.md).
Этот будущий аппаратный этап не отмечать выполненным на основании текущих demo-строк.

<a id="sources"></a>
## 13. Источники и границы доказательств

**Сессия оператора 02.10.2026** — источник фактических версий установленного ПО,
результатов команд, отдельных измерений задержки, 36 пройденных тестов и итогового
SQL-вывода. Персональные DSN, token, пароли, содержимое CA и локальные абсолютные
пути в репозиторий не переносились.

**Исходники проекта**, прочитанные для сверки поведения:
[STAND_SETUP.md](STAND_SETUP.md), [PROTOCOL_V1.md](PROTOCOL_V1.md),
[provision.py](../../src/tlm_device_data_platform/provision.py),
[private_config.py](../../src/tlm_device_data_platform/private_config.py),
[postgres_ingestion.py](../../src/tlm_device_data_platform/postgres_ingestion.py),
[serve_api.py](../../src/tlm_device_data_platform/serve_api.py),
[edge_agent.py](../../src/tlm_device_data_platform/edge_agent.py),
[tlm_http.py](../../firmware/esp32_micropython/tlm_http.py).

**Официальные справочники**, использованные отдельно для проверки пояснений,
а не как доказательство запуска стенда:
[Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres),
[Supabase PSQL + CA](https://supabase.com/docs/guides/database/psql),
[PostgreSQL SSL](https://www.postgresql.org/docs/current/libpq-ssl.html),
[libpq connection strings](https://www.postgresql.org/docs/current/libpq-connect.html),
[Psycopg conninfo](https://www.psycopg.org/psycopg3/docs/api/conninfo.html),
[Python 3.11 urllib.request](https://docs.python.org/3.11/library/urllib.request.html).
