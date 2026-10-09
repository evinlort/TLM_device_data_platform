# TLM API: полное руководство пользователя

Это руководство объясняет, что делает TLM API, как получить доступ, отправить
телеметрию, понять ответ и написать клиент, который сохраняет данные при сбоях.
Оно предназначено для разработчика интеграции, оператора лабораторного стенда
и человека, впервые работающего с этим API.

**Область документа:** реализация в `main`, проверенная по исходникам commit
`f6d9182be2a4790d6b5773998d7aa28d3b0ec251` 09.10.2026. Это версия исходников,
а не утверждение о версии конкретного запущенного сервера. В репозитории сервис
называется **TLM Device Data Platform / TLM API**; отдельное название «TLP API»
не определено. Ветка `feat/session-user-access` содержит дополнительные API,
которые на момент этой проверки не объединены в `main`; их статус описан
в [разделе 14](#14-версии-и-дополнения-в-разработке).

Все числовые показания с именами `test_*` ниже — **программные учебные данные**.
Они не являются результатами измерения физического датчика. Выполняйте учебную
отправку на согласованном тестовом устройстве в development-окружении: успешный
запрос добавляет реальную строку истории в выбранную БД.

## Содержание

1. [Что такое TLM API](#1-что-такое-tlm-api)
2. [Адрес сервера и устройство HTTP-запроса](#2-адрес-сервера-и-устройство-http-запроса)
3. [Все доступные endpoints](#3-все-доступные-endpoints)
4. [Аутентификация и получение доступа](#4-аутентификация-и-получение-доступа)
5. [Первый запрос: пошаговая отправка через curl](#5-первый-запрос-пошаговая-отправка-через-curl)
6. [Справочник POST /v1/telemetry](#6-справочник-post-v1telemetry)
7. [ACK, идентификаторы, повтор и порядок сообщений](#7-ack-идентификаторы-повтор-и-порядок-сообщений)
8. [Ошибки и решение проблем](#8-ошибки-и-решение-проблем)
9. [Пример клиента на Python](#9-пример-клиента-на-python)
10. [Отправка через Postman или аналогичный HTTP-клиент](#10-отправка-через-postman-или-аналогичный-http-клиент)
11. [Готовые клиенты: Linux и ESP32](#11-готовые-клиенты-linux-и-esp32)
12. [Подготовка и запуск сервера оператором](#12-подготовка-и-запуск-сервера-оператором)
13. [Проверка записи, ограничения и частые вопросы](#13-проверка-записи-ограничения-и-частые-вопросы)
14. [Версии и дополнения в разработке](#14-версии-и-дополнения-в-разработке)
15. [Источники и устройство документации](#15-источники-и-устройство-документации)

## 1. Что такое TLM API

API — интерфейс, через который одна программа обращается к другой. В этом
проекте устройство или программа-клиент отправляет HTTP-запрос с JSON: кто
отправил сообщение, какое это измерение и какие числовые показания получены.
TLM API проверяет запрос и credential устройства, записывает сообщение
в PostgreSQL и возвращает подтверждение.

Телеметрия — именованные показания устройства. В v1 один запрос содержит
одно сообщение с одним или несколькими показаниями, например расстоянием
`distance_cm`. Реальные имена, единицы и физический смысл задаёт интеграция
конкретного оборудования. API проверяет числовой формат, но не определяет
модель датчика и не подтверждает достоверность измерения.

```text
Device or software client
  -> persistent outbox
  -> HTTPS POST /v1/telemetry + device token
  -> TLM API: validation and device binding
  -> PostgreSQL transaction
  -> COMMIT
  -> JSON acknowledgement
  -> client removes the acknowledged outbox item
```

Supabase сейчас предоставляет PostgreSQL для хранения. Клиент обращается
к **TLM API**, а не к Supabase Data API. Ему не нужны имена SQL-таблиц,
database password, `anon`/publishable key или `service_role` key.

Две прикладные операции в `main`:

- проверка жизни процесса API;
- добавление телеметрии в историю с безопасным повтором того же сообщения.

Чтение истории пользователем, аккаунты, сессии и dashboard относятся к отдельному
дополнению. В текущем `main` нет HTTP-операций для просмотра, изменения или
удаления телеметрии, регистрации устройства, обновления его token или управления
оборудованием. Регистрацию выполняет оператор отдельным CLI.

## 2. Адрес сервера и устройство HTTP-запроса

### 2.1. Base URL

**Base URL** — адрес TLM API без пути конкретной операции. Получите его
у оператора стенда. В руководстве используются такие примеры:

| Назначение | Пример | Когда использовать |
| --- | --- | --- |
| Сетевой сервер | `https://tlm-api.example.org` | Заменить подтверждённым HTTPS-адресом своего API |
| Локальный сервер | `http://127.0.0.1:8000` | Клиент и API работают на одном компьютере |
| Полный URL отправки | `https://tlm-api.example.org/v1/telemetry` | Передать HTTP-клиенту или агенту |

`tlm-api.example.org` — заглушка, не опубликованный endpoint проекта.
Адрес вида `https://<project>.supabase.co` не является адресом TLM API.
`127.0.0.1` на ESP32 или другом компьютере означает само это устройство,
а не компьютер, на котором оператор запустил сервер.

Используйте точный путь `/v1/telemetry`, без завершающего `/`, query string
и fragment. Встроенный Linux-клиент проверяет этот путь; redirect для него
является ошибкой конфигурации. Reverse proxy должен отдавать эти пути напрямую.

Для сети нужен HTTPS с доверенным сертификатом на имя API. HTTP допустим
для loopback и явно согласованной изолированной лабораторной сети. Флаги
небезопасного режима рассмотрены в разделах о клиентах и сервере.

### 2.2. Из чего состоит запрос

```http
POST /v1/telemetry HTTP/1.1
Host: tlm-api.example.org
Authorization: Bearer <DEVICE_TOKEN>
Content-Type: application/json

{"schema_version":1,"device_id":"<DEVICE_UUID>","message_id":"<MESSAGE_UUID>","stream_id":"<STREAM_UUID>","sequence_no":1,"captured_at":null,"payload":{"test_sensor":12.5}}
```

Значения в `<...>` нужно заменить; такой шаблон сам по себе не является валидным
запросом. Метод `POST` отправляет сообщение. Путь выбирает операцию.
`Authorization` передаёт секрет устройства. `Content-Type` сообщает формат
тела. JSON содержит само сообщение. HTTP-клиент обычно вычисляет `Content-Length`
самостоятельно; вручную его задавать не нужно.

| Заголовок | Требование |
| --- | --- |
| `Authorization: Bearer <DEVICE_TOKEN>` | Обязателен для отправки телеметрии |
| `Content-Type: application/json` | Обязателен; `application/json; charset=utf-8` также принимается |
| `Accept: application/json` | Можно передать; специального согласования формата ответов в v1 нет |
| `Content-Length` | Если есть, должен быть корректным неотрицательным ASCII decimal и не превышать 65 536 |

Cookies, username/password, OAuth, `X-API-Key` и заголовок `apikey`
не используются для аутентификации device ingestion v1. Отдельный
`Idempotency-Key` не нужен: идентификатор сообщения находится в JSON.

## 3. Все доступные endpoints

Таблица включает прикладные операции и служебные маршруты, создаваемые FastAPI.
Доступность через внешний адрес также зависит от настройки reverse proxy.

| Метод | Путь | Аутентификация | Назначение |
| --- | --- | --- | --- |
| `GET` | `/health/live` | Не требуется | Проверка жизни процесса |
| `POST` | `/v1/telemetry` | Device Bearer token | Сохранение одного сообщения или подтверждение идентичного повтора |
| `GET`, `HEAD` | `/openapi.json` | Не требуется | Автоматически созданное описание прикладных маршрутов |
| `GET`, `HEAD` | `/docs` | Не требуется | Страница Swagger UI |
| `GET`, `HEAD` | `/redoc` | Не требуется | Страница ReDoc |
| `GET`, `HEAD` | `/docs/oauth2-redirect` | Не требуется | Служебная HTML-страница Swagger UI; не login endpoint TLM |

У прикладных `/health/live` и `/v1/telemetry` нет отдельно объявленных `HEAD`
или `OPTIONS`. В `main` также нет прикладного маршрута `/`: при доступе к корню
самого приложения ожидается `404`. Reverse proxy может иметь собственный ответ.

### 3.1. GET /health/live

Запрос без тела и без token:

```bash
curl --silent --show-error --include \
  "$TLM_API_BASE_URL/health/live"
```

Ответ приложения:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"alive"}
```

`alive` означает, что процесс обслуживает HTTP. Endpoint **не обращается к БД**
и не проверяет migrations, доступность storage, token или готовность записать
телеметрию. При недоступной БД health может оставаться `200`.
Отдельного readiness endpoint в этой версии нет.

### 3.2. POST /v1/telemetry

Принимает одно JSON-сообщение. Новый пакет получает `201` и `status: stored`;
идентичный повтор — `200` и `status: duplicate`. Обе формы подтверждают
сохранённое сообщение. Полный контракт и все ошибки описаны в разделах 6–8.

### 3.3. Страницы документации и OpenAPI

Откройте `<BASE_URL>/docs` или `<BASE_URL>/redoc` в браузере. Для загрузки
спецификации:

```bash
curl --silent --show-error \
  "$TLM_API_BASE_URL/openapi.json" \
  --output openapi.json
```

**Ограничение текущей реализации:** сервер разбирает JSON и заголовки вручную
из `Request`. Поэтому generated OpenAPI показывает `/health/live` и
`/v1/telemetry`, но не содержит полной схемы тела, описания Bearer security,
всех ошибок и ответа `201`. Для telemetry там автоматически указан общий `200`.
Swagger UI не предоставляет полностью настроенный ввод этого запроса;
сгенерированный по этой спецификации SDK также потребует ручного дополнения.
Используйте проверенный контракт ниже и примеры `curl`/Python.

`/docs/oauth2-redirect` появляется как стандартный маршрут Swagger UI.
Его наличие не означает поддержку OAuth в device API.

## 4. Аутентификация и получение доступа

### 4.1. Что нужно получить у оператора

Для готового стенда запросите:

1. Base URL и доступ к сети API.
2. UUID зарегистрированного устройства: `TLM_DEVICE_ID`.
3. Его секрет: `TLM_DEVICE_TOKEN`.
4. При необходимости доверенный CA и порядок установки доверия для API.
5. Согласованные имена датчиков, единицы, правила времени и режим test/real data.

Оператор обычно передаёт приватный `device.secret.json`:

```json
{
  "TLM_DEVICE_ID": "<PROVISIONED_DEVICE_UUID>",
  "TLM_DEVICE_TOKEN": "<PROVISIONED_DEVICE_TOKEN>"
}
```

В конфигурацию Linux-клиента можно добавить `TLM_API_URL` с полным URL
`https://<API_HOST>/v1/telemetry`. UUID и token берутся из provisioning,
а не генерируются клиентом вместо регистрации.

### 4.2. Как работает token

Операторский CLI генерирует секрет из 32 случайных байтов в URL-safe формате;
обычный результат имеет 43 символа. HTTP endpoint принимает token длиной
43–128 символов из `A-Z`, `a-z`, `0-9`, `_`, `-`. Корректный формат ещё
не означает, что token зарегистрирован или активен. Token — непрозрачный секрет,
не JWT: декодировать его для получения роли или срока действия не нужно.

Каждый telemetry request должен содержать:

```http
Authorization: Bearer <PROVISIONED_DEVICE_TOKEN>
```

Без кавычек вокруг token, без перевода строки, без добавочного текста.
В документации используется каноническое написание `Bearer`.
Секрет проверяется при каждом запросе, включая повтор уже сохранённого сообщения.

В БД хранится SHA-256 digest token. Сервер проверяет, что credential существует,
не отозван, не истёк и устройство активно. Затем он сравнивает связанный
UUID с `device_id` в JSON. Нельзя отправлять данные другого устройства,
просто изменив JSON.

| Ситуация | Ответ |
| --- | --- |
| Заголовок отсутствует или имеет неверный формат | `401` |
| Token неизвестен, отозван, истёк; устройство неактивно | `401` |
| Активный token принадлежит другому `device_id` | `403` |
| Credential подходит | Сервер продолжает обработку сообщения |

При `401` приложение добавляет `WWW-Authenticate: Bearer`. Оно не раскрывает
клиенту, какая именно проверка credential не прошла.
Уже аутентифицированный запрос может завершиться одновременно с отзывом token;
отзыв не является отменой всех начатых транзакций.

### 4.3. Где хранить credential

Храните приватный JSON вне Git, с владельцем пользователя запуска и правами
`0600` на Linux. Встроенные сервер и агент отклоняют небезопасные права,
недопустимые ключи конфигурации и симлинк вместо файла.
Не помещайте token в query string или payload, общие примеры, логи и screenshots.
При использовании Postman не сохраняйте его в публичной или общей коллекции.

Device token, database DSN и Supabase keys — разные credentials:

| Credential | Кому нужен | Для чего |
| --- | --- | --- |
| `TLM_DEVICE_TOKEN` | Устройству/клиенту | HTTP-запросы телеметрии своего устройства |
| `TLM_DATABASE_DSN` | TLM API | Подключение к PostgreSQL под ограниченным runtime LOGIN |
| `TLM_ADMIN_DSN` | Оператору | Provisioning и согласованные административные операции |
| Supabase Auth/Data API keys | Не нужны клиенту v1 | Не заменяют token TLM |

HTTP login, token refresh и self-service registration для устройств отсутствуют.
При потере или компрометации token обратитесь к оператору. Автоматического
workflow ротации в `main` нет; повторный запуск `provision device` не является
ротацией существующего credential.

## 5. Первый запрос: пошаговая отправка через curl

Пример рассчитан на Bash, Python 3 и `curl` с чтением заголовков из файла.
API и тестовое устройство должны быть уже подготовлены оператором.
Шаги отправляют одно **программное учебное** показание `test_sensor`.

### 5.1. Выберите сервер и конфигурацию

Подставьте фактический адрес и путь к выданному приватному JSON:

```bash
export TLM_API_BASE_URL='https://tlm-api.example.org'
export TLM_DEVICE_CONFIG='/secure/device.secret.json'
```

Для API на этом же компьютере допустимо вместо HTTPS-примера задать
`http://127.0.0.1:8000`. В этих переменных нет необходимости хранить сам token.

Проверьте жизнь процесса:

```bash
curl --silent --show-error --include \
  "$TLM_API_BASE_URL/health/live"
```

Ожидайте `200` и `{"status":"alive"}`. Если запрос не проходит, сначала
исправьте URL, сеть или TLS; health ещё не проверяет credential и storage.

### 5.2. Один раз создайте учебное сообщение

Работайте в отдельном приватном каталоге вне Git. `umask` ограничивает доступ
к создаваемым файлам. Каталог с фиксированным именем должен быть новым:

```bash
umask 077
mkdir tlm-api-tutorial
cd tlm-api-tutorial
python3 - <<'PY'
import json
import os
from pathlib import Path
import re
from uuid import UUID, uuid4

config = json.loads(Path(os.environ["TLM_DEVICE_CONFIG"]).read_text())
device_id = str(UUID(config["TLM_DEVICE_ID"]))
token = config["TLM_DEVICE_TOKEN"]
if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
    raise SystemExit("Invalid device token format")
message = {
    "schema_version": 1,
    "device_id": device_id,
    "message_id": str(uuid4()),
    "stream_id": str(uuid4()),
    "sequence_no": 1,
    "captured_at": None,
    "payload": {"test_sensor": 12.5},
}
with open("telemetry.json", "x", encoding="utf-8") as stream:
    json.dump(message, stream, allow_nan=False, indent=2)
    stream.write("\n")
with open("device.headers", "x", encoding="ascii") as stream:
    stream.write(f"Authorization: Bearer {token}\n")
    stream.write("Content-Type: application/json\n")
print("Created telemetry.json and a private device.headers file; no token printed.")
PY
```

`telemetry.json` содержит сообщение без token. `device.headers` содержит секрет:
не публикуйте его. У UUID автоматически правильный формат. `captured_at: null`
показывает разрешённый режим без достоверного времени измерения.

Этот шаг создаёт новое измерение. **При повторной доставке не выполняйте
генерацию снова:** сохранённый `telemetry.json` должен остаться тем же.
Для нового учебного опыта используйте другой новый каталог.

### 5.3. Отправьте файл

```bash
curl --silent --show-error \
  --request POST \
  --header @device.headers \
  --data-binary @telemetry.json \
  --connect-timeout 5 \
  --max-time 15 \
  --dump-header receipt.headers \
  --output receipt.json \
  --write-out '%{http_code}\n' \
  "$TLM_API_BASE_URL/v1/telemetry"
```

Здесь token не передаётся как literal в аргументах команды. `curl` не следует
redirect и не делает автоматические повторы. `--max-time 15` — выбранный
лимит учебного клиента, не обещание времени ответа API.
Если ваш `curl` не поддерживает `--header @file`, используйте Python-пример
из раздела 9 или поддерживаемую оператором версию клиента.

Для первого сохранения ожидайте напечатанный HTTP code `201`. Посмотреть JSON:

```bash
python3 -m json.tool receipt.json
```

Структура ответа выглядит так; UUID и время ниже — иллюстрация, а не данные
конкретного стенда:

```json
{
  "status": "stored",
  "device_id": "11111111-1111-4111-8111-111111111111",
  "message_id": "22222222-2222-4222-8222-222222222222",
  "received_at": "2026-10-09T09:00:00.123456+00:00"
}
```

Сверьте `device_id` и `message_id` с отправленным файлом. `curl` без
`--fail` может завершиться с code `0` даже при HTTP `401` или `503`:
смотрите именно HTTP code и тело. Ошибка DNS/TLS/timeout также не является ACK.

### 5.4. Повторите ровно тот же файл

Повторно выполните **только команду отправки из 5.3**. При успешном первом
COMMIT теперь ожидайте `200`, `status: duplicate`, те же UUID и первоначальный
`received_at`. Новая строка при таком повторе не создаётся.

Если первый ответ потерялся, повтор может вернуть `201` или `200`:
оба корректных ACK завершают доставку. Нельзя предполагать отсутствие записи
из-за timeout и заменять `message_id`.

После работы уберите временный `device.headers` из используемого каталога
согласно правилам хранения секретов стенда. Сохраните неподтверждённый
`telemetry.json` для восстановления доставки.

## 6. Справочник POST /v1/telemetry

### 6.1. Запрос

- Метод: `POST`.
- Путь: `/v1/telemetry`.
- Аутентификация: Bearer token устройства.
- Тип тела: UTF-8 JSON object.
- Query и path parameters: не предусмотрены.
- Один запрос: одно сообщение; batch-массив не принимается.
- Максимальный размер тела: **65 536 байтов (64 KiB)**, включая JSON-синтаксис
  и пробелы. Лимит относится к байтам, не к числу символов.

Все **семь** полей обязательны, включая `captured_at`, даже если оно `null`.
Неизвестные envelope fields запрещены.

| Поле | JSON-тип | Требование и назначение |
| --- | --- | --- |
| `schema_version` | integer | Ровно `1`; `1.0`, `true` и строка `"1"` не подходят |
| `device_id` | string | UUID зарегистрированного устройства; должен соответствовать token |
| `message_id` | string | UUID одного сообщения; новый для нового измерения, неизменный при повторе |
| `stream_id` | string | UUID потока сбора; новый при новом запуске клиента, сохранённый в старой очереди |
| `sequence_no` | integer | От `1` до `9223372036854775807` включительно; позиция внутри потока |
| `captured_at` | string или null | Время измерения с зоной в принимаемом формате либо `null` |
| `payload` | object | От 1 до 128 именованных числовых показаний |

Полный пример с синхронизированным временем; значения `test_*` искусственные:

```json
{
  "schema_version": 1,
  "device_id": "11111111-1111-4111-8111-111111111111",
  "message_id": "22222222-2222-4222-8222-222222222222",
  "stream_id": "33333333-3333-4333-8333-333333333333",
  "sequence_no": 1,
  "captured_at": "2026-10-09T12:00:00.123456+03:00",
  "payload": {
    "test_sensor_1": 12.5,
    "test_sensor_2": 7
  }
}
```

Эти UUID валидны как строки, но не являются зарегистрированными credentials.
Для выполняемого запроса замените `device_id` своим зарегистрированным UUID
и сгенерируйте собственные message/stream IDs.

### 6.2. Правила payload

Имя датчика соответствует выражению:

```text
[A-Za-z0-9][A-Za-z0-9_.-]{0,63}
```

Первый символ — ASCII letter или digit. Далее разрешены ASCII letters,
digits, `_`, `.`, `-`. Всего 1–64 символа. Например, `distance_cm`,
`sensor.1`, `channel-2` допустимы; `bad name`, `_sensor`, `температура`
и пустое имя — нет.

Значение — конечное JSON-число: integer или float. Ноль и отрицательные числа
допустимы на уровне протокола; физическую допустимость задаёт драйвер/интеграция.
Boolean не считается числом. Запрещены строки с числами, `null`, arrays,
вложенные objects, `NaN`, `Infinity`, `-Infinity` и float overflow вроде `1e999`.
Размеры запросов и возможности PostgreSQL также ограничивают представление;
API не обещает неограниченную числовую точность или поддержку произвольных
чисел любого размера.

Не добавляйте `units`, `device_id`, `received_at` и другие metadata в payload
как вложенные структуры. Согласуйте имена и единицы заранее: например,
имя `distance_cm` обозначает сантиметры только по контракту вашей интеграции.
В v1 нет каталога sensor types, автоматического перевода единиц и
проверки физических диапазонов на сервере.

### 6.3. Правила времени

Принимается конкретное подмножество RFC3339:

```text
YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)
```

Обязательны дата, `T`, часы/минуты/секунды и зона. Дробная часть необязательна;
если есть, содержит 1–6 цифр. `T` и `Z` пишутся в верхнем регистре.
Дата и время должны существовать; leap second `:60` не поддерживается.

| Значение | Результат |
| --- | --- |
| `"2026-10-09T09:00:00Z"` | Принимается |
| `"2026-10-09T12:00:00.123456+03:00"` | Принимается; нормализуется в UTC |
| `null` | Принимается; достоверное время измерения отсутствует |
| `"2026-10-09T09:00:00"` | Отклоняется: нет зоны |
| `"2026-10-09"` | Отклоняется: нет времени |
| `"2026-10-09T09:00:00.123456789Z"` | Отклоняется: больше 6 дробных цифр |

Используйте `null`, если устройство не имеет синхронизированных часов.
Не заменяйте его временем отправки при повторе. Сервер не подтверждает
достоверность часов устройства и не задаёт SLA точности `captured_at`.

`received_at` создаёт БД при первой вставке. Его нельзя прислать в envelope:
это неизвестное поле, которое даст `422`. `received_at` — время вставки
на часах БД, а не время физического измерения и не точный timestamp COMMIT.

### 6.4. JSON и transport

Корневой JSON должен быть object, не array, string или `null`.
Повторяющиеся JSON keys запрещены на всех уровнях, даже с одинаковыми значениями.
Пропущенные/лишние поля, malformed JSON и invalid UTF-8 дают `422`.
Сжатое тело не распаковывается этой реализацией: отправляйте обычный JSON
без `Content-Encoding: gzip`. Multipart/form-data и URL-encoded form
не являются поддерживаемыми форматами.

Сервер проверяет размер как по `Content-Length`, так и при чтении body stream.
Отсутствующий `Content-Length` не отменяет лимит. Чтение тела ограничено
10 секундами; это не общий deadline всей обработки запроса.

### 6.5. Успешный ответ

| HTTP code | `status` | Значение |
| --- | --- | --- |
| `201 Created` | `stored` | Новое сообщение записано; COMMIT завершился до формирования ACK |
| `200 OK` | `duplicate` | Такое же сообщение уже существует; прежняя запись подтверждена |

Тело обеих форм содержит четыре поля:

| Поле | Тип | Значение |
| --- | --- | --- |
| `status` | string | `stored` или `duplicate` согласно HTTP code |
| `device_id` | string | Канонический UUID устройства |
| `message_id` | string | Канонический UUID подтверждённого сообщения |
| `received_at` | string | Timestamp первоначальной вставки с timezone |

Пример ответа на повтор:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"duplicate","device_id":"11111111-1111-4111-8111-111111111111","message_id":"22222222-2222-4222-8222-222222222222","received_at":"2026-10-09T09:00:00.123456+00:00"}
```

Ответ не возвращает payload, stream position или token. Успешный ACK подтверждает
хранение сообщения, а не физическую правильность показаний, обновление dashboard
или исполнение команды устройством.

## 7. ACK, идентификаторы, повтор и порядок сообщений

### 7.1. Когда сообщение считается доставленным

Принимайте ACK, только если одновременно выполнены условия:

1. HTTP code равен `201` или `200`.
2. JSON корректен и содержит object.
3. `status` равен соответственно `stored` или `duplicate`.
4. `device_id` и `message_id` соответствуют отправленному сообщению.
5. `received_at` присутствует как timestamp string.

HTTP `200` с HTML-страницей reverse proxy, пустым телом, чужим UUID или
неожиданным статусом не является ACK. При таком ответе сохраните исходный
пакет и выясните причину. После валидного ACK можно удалить **только это**
сообщение из локальной очереди.

### 7.2. Идемпотентность

Идемпотентность здесь означает, что повторная доставка одного сообщения
не создаёт дополнительную строку. Основной ключ — `(device_id, message_id)`.
Дополнительно уникальна позиция `(device_id, stream_id, sequence_no)`.

| Отправка | Результат |
| --- | --- |
| Новый message ID и свободная stream position | `201 stored` |
| Тот же message ID, stream, sequence, captured_at и payload | `200 duplicate` |
| Тот же message ID, но изменён хотя бы один сравниваемый параметр | `409` |
| Новый message ID, но уже занятая позиция того же stream | `409` |

Сравнение выполняется по разобранным значениям и PostgreSQL JSONB,
а не по пробелам или порядку JSON keys. UUID приводятся к UUID-значениям,
время — к UTC. Клиент всё равно должен сохранять и повторять исходные bytes:
это предотвращает незаметную подмену payload или времени.

Не меняйте ID при timeout. Не пытайтесь «исправить» уже сохранённое сообщение
под прежним ID: API не поддерживает update. Новый message ID допустим для
нового измерения, но не как способ скрыть conflict или обойти retry.

### 7.3. Потоки, sequence и restart

При запуске сборщик выбирает новый `stream_id` и начинает `sequence_no` с `1`.
Для следующих новых сообщений того же потока увеличивайте sequence.
Для каждого нового сообщения используйте новый `message_id`.

При restart старая очередь сохраняет прежние stream/message IDs, sequence,
payload и captured_at. Только вновь собранные измерения принадлежат новому
stream. Sequence можно снова начать с `1`, поскольку stream ID другой.

Сервер обеспечивает уникальность позиции, но **не требует последовательного
поступления, отсутствия пропусков или возрастающего времени**. Сообщения
могут приходить поздно и не по порядку. `stream_id` не является account/session ID.

### 7.4. Надёжная доставка

Для собственного долговременно работающего клиента:

1. Прочитайте реальные sensor values и создайте envelope.
2. Надёжно сохраните envelope до первой сетевой отправки.
3. Отправляйте сохранённый пакет с исходными ID.
4. После валидного ACK удалите его из очереди.
5. При временной ошибке сохраните пакет и повторите с задержкой.
6. При постоянной ошибке данных сохраните пакет отдельно для диагностики.
7. При credential/endpoint/TLS configuration failure остановите доставку
   и привлеките оператора.

```text
persist -> send -> valid ACK -> remove
                -> timeout / 408 / 429 / 5xx -> retain -> delayed retry
                -> invalid data / conflict -> retain for diagnosis
                -> credential / endpoint failure -> retain -> operator
```

Timeout означает только, что клиент не получил полный ответ вовремя.
COMMIT мог уже произойти. После восстановления тот же пакет получит
`200 duplicate`, если строка сохранена, либо `201 stored`, если её ещё нет.
Это модель повторяемой доставки с устранением дублей в storage,
а не гарантия отсутствия любых потерь вне API или «exactly once» для оборудования.

## 8. Ошибки и решение проблем

### 8.1. Формат ошибки

Ожидаемые ошибки приложения возвращают JSON с `detail`:

```json
{"detail":"Invalid device credential"}
```

Storage failure:

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
Retry-After: 5

{"detail":"Storage unavailable; retain and retry"}
```

Reverse proxy, HTTP server и необработанная внутренняя ошибка могут вернуть
другой формат, включая text/HTML. Не предполагайте, что любой error body — JSON.
Не записывайте token или приватные DSN в диагностический вывод.

### 8.2. Полная таблица ответов и действий клиента

| HTTP code / ситуация | Причина | Действие |
| --- | --- | --- |
| `200 duplicate` | Идентичное сообщение уже сохранено | Проверить ACK, завершить доставку |
| `201 stored` | Новое сообщение сохранено | Проверить ACK, завершить доставку |
| `400` | Некорректный `Content-Length`; возможна transport error | Сохранить пакет, проверить HTTP-клиент |
| `401` | Недопустимый credential или неактивное устройство | Остановить автоматическую доставку; проверить provisioning с оператором |
| `403` | Token принадлежит другому UUID | Исправить binding конфигурации; не менять ID старой очереди вслепую |
| `404` | Путь/версия не существует | Проверить URL и версию сервера |
| `405` | Метод не поддерживается | Использовать `POST` для telemetry и `GET` для health |
| `408` | Тело не прочитано полностью за лимит или соединение прервано | Повторить исходный пакет после восстановления сети |
| `409` | Message ID или stream position конфликтуют с историей | Сохранить исходный пакет, исследовать генерацию ID; не менять ID для обхода |
| `413` | Тело больше 65 536 bytes | Исправить формирование новых пакетов; сохранить отклонённый |
| `415` | Не тот `Content-Type` | Использовать `application/json` и обычный JSON body |
| `422` | JSON/schema/UUID/time/payload не проходит validation | Исправить источник новых сообщений; сохранить исходный для диагностики |
| `429` | Ограничение со стороны infrastructure | Сохранить пакет, учесть `Retry-After`, повторить позже |
| `500`–`599` | Storage, server или proxy недоступны | Сохранить пакет и повторить позже; при длительной ошибке обратиться к оператору |
| `3xx` | Redirect, например неверный trailing slash | Использовать точный URL; встроенные клиенты останавливаются |
| Network timeout/disconnect | Ответ не подтверждён | Сохранить пакет и повторить с теми же ID |
| TLS verification failure | Недоверенный/неподходящий сертификат или часы | Исправить доверие/hostname/часы; не отключать verification |
| `200/201` с неправильным body | Нет валидного ACK | Сохранить пакет; повторить после диагностики |

Собственного rate limiting endpoint не реализует: `429` может поступать
от инфраструктуры. Серверный CLI задаёт `limit_concurrency=32`; отказ при
нагрузке Uvicorn также может быть `503` с другим телом. Эти настройки
не являются гарантией 32 устройств, requests per second или общего SLA.

Обычный backoff собственного клиента может расти, например, 1, 2, 4, 8 секунд
до выбранного ограничения. Это рекомендация к клиенту, не wire protocol.
Не посылайте бесконечные немедленные повторы. Ответ API о storage failure
содержит числовой `Retry-After: 5`. Поведение готового Linux-клиента описано
в разделе 11; он поддерживает числовые секунды, не HTTP-date формат заголовка.

### 8.3. Сообщения validation

Текущая реализация может вернуть такие `detail` при `422`:

| `detail` | Что проверить |
| --- | --- |
| `Unexpected or missing envelope fields` | Ровно семь обязательных envelope fields |
| `Unsupported schema_version` | Integer `1` |
| `Identifiers must be UUID strings` | Тип UUID fields; значения переданы строками |
| `sequence_no must be a positive signed bigint` | Integer и диапазон sequence |
| `captured_at must be RFC3339 or null` | Зону, формат, дробные секунды |
| `payload must contain 1 to 128 sensor readings` | Object, число показаний |
| `Invalid sensor name` | Разрешённые ASCII symbols и длину |
| `Sensor readings must be numbers, not booleans` | Числа вместо strings/boolean/null/objects |
| `Sensor readings must be finite` | Float overflow / infinity |
| `Non-finite numbers are not allowed` | `NaN`/`Infinity` JSON literals |
| `Duplicate JSON keys are not allowed` | Повторяющиеся keys на любом уровне |
| `Message size is outside the permitted range` | Например, пустое тело |
| `Malformed telemetry envelope` | JSON encoding, invalid UUID, невозможную дату и другие ошибки разбора |

Текст полезен для человека. Логику клиента стройте прежде всего на HTTP code
и ACK contract, а не на разборе английской фразы как стабильного error code.
Если одновременно нарушено несколько правил, ответ показывает первую
обнаруженную проверкой ошибку; исправьте её и повторно проверьте документ.

### 8.4. Диагностика по симптомам

| Симптом | Проверка |
| --- | --- |
| `Connection refused` | Запущен ли API, правильны ли host/port и listener |
| `Could not resolve host` | DNS, правильное имя API, доступность сети |
| Другой компьютер не видит localhost API | Сервер по умолчанию loopback; нужен HTTPS proxy или согласованный внешний listener |
| Health работает, telemetry даёт `503` | Database DSN, migrations, права runtime, БД и server logs у оператора |
| `401` после успешной JSON validation | Правильный private file, отсутствие лишних символов, credential state |
| `403` | UUID и token относятся к одному устройству? |
| `422` у обычного POST | Body отправлен как JSON object? Есть `captured_at`? Не добавлен `received_at`? |
| `409` после retry | Не пересозданы ли captured_at/payload/sequence или IDs? |
| Повтор даёт `201` вместо `200` | Не создаётся ли новый message ID? Первый запрос действительно мог не сохранить строку |
| Browser fetch не работает, curl работает | В `main` не настроен CORS; нужен согласованный backend/same-origin доступ |
| Swagger не даёт ввести body/token | Ограничение generated OpenAPI; используйте это руководство |

Для обращения к оператору сохраните время проблемы, base URL, HTTP code,
безопасный error body, device/message IDs и версию клиента. Token и DSN
не включайте. При неизвестном исходе COMMIT сначала повторите тот же пакет
или попросите оператора сверить историю; не создавайте заменяющее измерение.

## 9. Пример клиента на Python

Этот скрипт отправляет **уже сохранённый** `telemetry.json` из раздела 5.
Он не генерирует новые данные, не удаляет очередь и не делает скрытых повторов.
Для работы нужны Python 3.11+ и установленный пакет проекта; дополнительные
HTTP libraries не нужны.

Сохраните код как `send_saved_telemetry.py` в приватном tutorial-каталоге.
Если используете venv репозитория, задайте абсолютный путь к его Python
при запуске из этого каталога.

```python
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError

from tlm_device_data_platform.edge_agent import FatalDelivery, HTTPSender
from tlm_device_data_platform.private_config import load_private_config
from tlm_device_data_platform.telemetry_v1 import TelemetryV1


def main():
    config = load_private_config(
        Path(os.environ["TLM_DEVICE_CONFIG"]),
        {"TLM_DEVICE_ID", "TLM_DEVICE_TOKEN", "TLM_API_URL"},
    )
    body = Path("telemetry.json").read_bytes()
    message = TelemetryV1.parse(body)
    if str(message.device_id) != config["TLM_DEVICE_ID"]:
        raise SystemExit("Device binding mismatch; original file retained")
    base_url = os.environ["TLM_API_BASE_URL"].rstrip("/")
    allow_http = os.environ.get("TLM_ALLOW_INSECURE_HTTP") == "1"
    sender = HTTPSender(
        base_url + "/v1/telemetry",
        config["TLM_DEVICE_TOKEN"],
        allow_insecure_http=allow_http,
    )
    result = sender.send(body)
    print(json.dumps({
        "action": result.action,
        "reason": result.reason,
        "retry_after": result.retry_after,
        "message_id": str(message.message_id),
    }))
    return 0 if result.action == "ack" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FatalDelivery, ValueError, OSError, HTTPError, URLError) as error:
        print(f"Delivery stopped ({type(error).__name__}); original file retained")
        raise SystemExit(1)
```

Запуск; путь ниже заменить реальным абсолютным путём venv:

```bash
/path/to/repository/.venv/bin/python send_saved_telemetry.py
```

Для выбранного локального/изолированного HTTP нужен явный opt-in:

```bash
export TLM_ALLOW_INSECURE_HTTP=1
/path/to/repository/.venv/bin/python send_saved_telemetry.py
```

`action: ack` означает, что встроенный sender проверил `200/201`, соответствующий
статус, совпадение UUID и наличие `received_at` как строки. `retry` означает
сохранить файл и повторить позже; `quarantine` — сохранить для диагностики
постоянной ошибки данных. Credential/endpoint/redirect/TLS verification failure
вызывает остановку. В примере при любом результате файл остаётся на диске,
поэтому следующий запуск безопасно повторяет то же сообщение.

Используется реальный `HTTPSender` проекта с default timeout `15.0 s` и
отключённым следованием redirect. `urllib` timeout относится к блокирующим
операциям и не является строгим общим deadline. Этот пример показывает
одну доставку; для постоянного сбора используйте агент с durable outbox.

## 10. Отправка через Postman или аналогичный HTTP-клиент

Для ручного HTTP-клиента нужны те же параметры:

| Настройка | Значение |
| --- | --- |
| Method | `POST` |
| URL | `<BASE_URL>/v1/telemetry` |
| Authorization type | Bearer Token |
| Token | Выданный `TLM_DEVICE_TOKEN`, без слова `Bearer` в самом поле token |
| Header | `Content-Type: application/json` |
| Body | Raw JSON из сохранённого `telemetry.json` |
| Redirect policy | Отключить автоматическое следование redirect |
| TLS verification | Оставить включённой; настроить доверенный CA при необходимости |

Сверьте ответ по разделу 7. Чтобы проверить duplicate, повторите тот же
body без переменных, которые генерируют UUID или timestamp при каждой отправке.
Динамический `message_id` превращает проверку retry в новое сообщение.
Token держите в приватном локальном хранилище клиента; экспортируемый пример
или коллекция должны содержать заглушку.

## 11. Готовые клиенты: Linux и ESP32

API не обязывает использовать конкретный клиент. Готовые реализации полезны
тем, что уже сохраняют пакет до отправки, проверяют ACK и повторяют его
без изменения идентичности.

### 11.1. Linux-агент

После установки пакета и фактического sensor driver:

```bash
.venv/bin/python -m tlm_device_data_platform.edge_agent \
  --config /secure/device.secret.json \
  --api-url https://tlm-api.example.org/v1/telemetry \
  --sensor your_installed_driver:read
```

`your_installed_driver:read` — заглушка для реально установленной функции.
Драйвер предоставляет функцию без аргументов, возвращающую непустой словарь
реальных numeric readings. Ошибка драйвера не превращается в нулевое показание.

| Параметр | Значение/поведение |
| --- | --- |
| `--config` | Приватный JSON; token берётся из файла или `TLM_DEVICE_TOKEN` environment |
| `--sensor` | Обязательный `module:function` |
| `--api-url` | Полный `/v1/telemetry` URL; также `TLM_API_URL` в environment/config |
| `--device-id` | Device UUID; обычно достаточно значения private config |
| `--outbox` | По умолчанию `~/.local/state/tlm/outbox.sqlite3` |
| `--max-records` | По умолчанию 10 000 записей, включая quarantined |
| `--count` | `0` — непрерывно; положительное число ограничивает новые измерения |
| `--unsynchronized-clock` | Отправлять `captured_at: null` |
| `--allow-insecure-http` | Явное разрешение лабораторного HTTP |

Номинальный интервал новых измерений — 10 секунд. Collection и delivery
независимы; медленная сеть не блокирует сбор, но sensor driver всё ещё
может задержать его. Outbox использует SQLite WAL и `synchronous=FULL`.
Ею владеет один процесс. При заполнении старые записи не вытесняются.

| Результат доставки | Поведение Linux-агента |
| --- | --- |
| Валидный ACK | Удаляет только подтверждённую запись |
| Network failure, invalid ACK, `408`, `429`, `5xx` | Сохраняет pending, backoff от 1 до 60 s |
| Числовой `Retry-After` | Может продлить ожидание до 3600 s |
| `400`, `409`, `413`, `422` | Сохраняет bytes в quarantine; другие pending могут доставляться |
| Остальные non-success HTTP, redirect, credential/endpoint failure | Останавливает агент; очередь сохраняется |
| TLS verification failure | Останавливает агент; очередь сохраняется |

После ограниченного сбора default drain составляет `16.0 s`, затем bounded
sender join — до `6.0 s`. Это не строгий общий deadline и не отмена серверного
COMMIT. Если остались pending/quarantined записи, агент не сообщает успешное
пустое завершение. Подробности shutdown — в
[инструкции стенда](STAND_SETUP.md#источник-датчиков-и-запуск-агента).

Для **только программной** проверки на тестовом устройстве:

```bash
.venv/bin/python -m tlm_device_data_platform.edge_agent \
  --config /secure/test-device.secret.json \
  --api-url http://127.0.0.1:8000/v1/telemetry \
  --sensor tlm_device_data_platform.demo_sensor:read \
  --outbox /private/tutorial/demo-outbox.sqlite3 \
  --count 3 \
  --allow-insecure-http
```

Путь outbox должен принадлежать пользователю запуска; используйте отдельную
очередь для tutorial. `demo_sensor` даёт `test_sensor_1`/`test_sensor_2`,
не hardware measurements. Он не заменяет драйвер физического оборудования.

### 11.2. ESP32 MicroPython

ESP32 использует тот же endpoint и credential, отдельный MicroPython-клиент
и flash outbox. Сохраните `TLM_DEVICE_ID`, `TLM_DEVICE_TOKEN`, полный
`TLM_API_URL`, Wi-Fi и CA settings в private device config.
Пример ключей — в
[config.example.json](../../firmware/esp32_micropython/config.example.json).

В выбранном HC-SR04-клиенте payload содержит реальное `distance_cm`.
`captured_at` всегда `null`; наличие NTP для TLS не превращает его в
доверенный capture timestamp. Для HTTPS нужно настроить CA и подходящие
часы, сохранив verification.

В актуальной реализации `main` sampling и delivery последовательны:
пока сообщение pending, firmware повторяет его и не делает новое измерение.
При длительной сетевой ошибке интервалы пропускаются. Старый backlog
доставляется до новых измерений. Flash outbox сохраняет старые IDs
при restart; default capacity — 512 файлов с учётом quarantine и backlog.
Следовательно, Linux и ESP32 имеют разные offline collection policies,
хотя wire protocol одинаков.

Подключение, USB, firmware и аппаратная приёмка описаны в
[ESP32 README](../../firmware/esp32_micropython/README.md) и
[полном руководстве физического стенда](ESP32_REAL_HARDWARE_BRINGUP_RU.md).
Эта API-инструкция не является новой аппаратной проверкой.

## 12. Подготовка и запуск сервера оператором

Этот раздел нужен тому, кто создаёт стенд. Пользователь уже работающего API
может начать с раздела 4. Изложенные команды — инструкции; при написании
руководства они не выполнялись на удалённом проекте.

### 12.1. Установите сервер и подготовьте схему

Из корня repository на API-хосте:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -c requirements/server.txt '.[server]'
.venv/bin/python -m pip check
```

После изменения checkout переустановите non-editable пакет: обычный `git pull`
не обновляет ранее установленную wheel-копию.

Сначала выберите разрешённую development-БД и проверьте фактическую migration
history. Миграции применяются по порядку; старый fixture contract сохраняется.
Полный локальный и remote порядок — в [STAND_SETUP.md](STAND_SETUP.md).
Для текущего v1 таблицы создаёт
[20261002010000_add_device_ingestion.sql](../../supabase/migrations/20261002010000_add_device_ingestion.sql).
Не открывайте схему `tlm` через Supabase Data API. Для подготовки стенда
не требуется remote database reset.

Создайте private `admin.secret.json` вне Git, права `0600`:

```json
{"TLM_ADMIN_DSN":"<CONFIRMED_ADMIN_POSTGRESQL_DSN>"}
```

У remote DSN должны быть явный host, `sslmode=verify-full` и доверенный root CA,
когда он нужен провайдеру. Endpoint direct/session pooler берётся из настроек
выбранного проекта. Transaction pooler не заявлен как проверенный runtime
вариант этого пилота.

### 12.2. Зарегистрируйте runtime и устройство

Следующие команды **меняют выбранную БД**. `--apply` — обязательное явное
указание provisioning tool; выполняйте их только на согласованном target.

```bash
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config /secure/admin.secret.json \
  --apply runtime \
  --output /secure/runtime.secret.json

.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config /secure/admin.secret.json \
  --apply device \
  --system-type 'TEST software API tutorial' \
  --output /secure/test-device.secret.json
```

`TEST software API tutorial` явно маркирует учебное устройство. Для настоящего
стенда укажите фактический system type. По умолчанию UUID и token нового
устройства генерирует CLI. `--device-id <UUID>` допустим для согласованного
постоянного UUID новой записи, не для перезаписи существующей.

Runtime получает отдельный LOGIN `tlm_api` с группой `tlm_ingest`.
Допустим `--role tlm_api_<SUFFIX>` с lowercase буквами/цифрами/underscore
в suffix. При выбранном session pooler добавьте к `runtime`
`--pooler-project-ref <DEV_PROJECT_REF>`: wire username отличается от role
и имеет вид `tlm_api.<PROJECT_REF>`.

Результаты:

| Файл | Содержимое | Куда передать |
| --- | --- | --- |
| `runtime.secret.json` | `TLM_DATABASE_DSN` ограниченного LOGIN | Только API-хосту |
| `test-device.secret.json` | `TLM_DEVICE_ID`, `TLM_DEVICE_TOKEN` | Тестовому клиенту |
| `admin.secret.json` | `TLM_ADMIN_DSN` | Остаётся у оператора |

Файлы создаются с правами `0600` без overwrite. Recovery material записывается
до database mutation. Если provisioning упал или потерял ответ на COMMIT,
файл сохраняется: его наличие не доказывает успешную регистрацию.
Сверьте состояние выбранной БД перед повтором; не удаляйте recovery file
и не генерируйте замену вслепую.

### 12.3. Запустите API

```bash
.venv/bin/python -m tlm_device_data_platform.serve_api \
  --config /secure/runtime.secret.json
```

Default listener — `127.0.0.1:8000`. Для внешнего доступа настройте HTTPS
reverse proxy к loopback или используйте TLS самого сервера:

```bash
.venv/bin/python -m tlm_device_data_platform.serve_api \
  --config /secure/runtime.secret.json \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-certfile /secure/fullchain.pem \
  --ssl-keyfile /secure/key.pem
```

Если TLS обслуживается reverse proxy, он должен передавать точные пути
и `Authorization`/`Content-Type`, поддерживать размер body и разумные timeout.
Не публикуйте внутренний loopback listener отдельным небезопасным способом.
Для явно изолированного LAN HTTP у сервера есть `--allow-insecure-lan`;
его включение не включает HTTP на клиенте автоматически.

Сервер может читать `TLM_DATABASE_DSN` из environment вместо файла.
Передавать ему admin DSN нельзя: запись под owner/superuser/BYPASSRLS или
другой недопустимо привилегированной identity отклоняется.
Runtime разрешены чтение необходимых таблиц и ограниченный INSERT истории,
но не изменение/удаление истории и не provisioning credentials.
Эти backend privileges не являются пользовательской изоляцией по школам.

Server CLI имеет default concurrency limit 32 и keep-alive timeout 5 s.
Storage adapter использует connection timeout 5 s, statement timeout 5 s,
lock timeout 2 s. Это разные ограничения на этапы, не общий SLA запроса.
Сервисный менеджер, monitoring и production deployment должны быть настроены
оператором отдельно; для записи не достаточно успешного `/health/live`.

## 13. Проверка записи, ограничения и частые вопросы

### 13.1. Как проверить историю

Для клиента валидный ACK является подтверждением. Отдельного HTTP GET
истории в `main` нет. Оператор может проверить выбранную БД через SQL:

```sql
SELECT device_id, message_id, stream_id, sequence_no,
       captured_at, received_at, payload
FROM tlm.telemetry_messages
WHERE device_id = '<PROVISIONED_DEVICE_UUID>'::uuid
ORDER BY received_at DESC, message_id
LIMIT 20;
```

Для проверки конкретного пакета добавьте условие:

```sql
SELECT device_id, message_id, captured_at, received_at, payload
FROM tlm.telemetry_messages
WHERE device_id = '<PROVISIONED_DEVICE_UUID>'::uuid
  AND message_id = '<SENT_MESSAGE_UUID>'::uuid;
```

Это операторские SQL-запросы, не device requests. На устройство не передаются
database credentials. Новый пакет — одна строка с JSONB payload.
Duplicate не добавляет строку и не изменяет первоначальный `received_at`.

Сортировка по `received_at` показывает порядок вставки на сервере.
После offline replay последняя полученная запись может содержать старое
измерение. Таблица current state и гарантии «самого актуального значения»
в этой реализации отсутствуют.

### 13.2. Возможности и границы

| Вопрос | Ответ для `main` |
| --- | --- |
| Можно отправить много sensors? | Да, 1–128 чисел в одном payload, при body не больше 64 KiB |
| Можно отправить массив сообщений? | Нет, отдельный POST для каждого сообщения |
| Можно отправить image/string/event object? | Нет, payload v1 содержит только числовые readings |
| Можно добавить произвольный metadata field? | Нет, envelope fields фиксированы |
| Нужны Supabase SDK/keys на устройстве? | Нет |
| Можно получить token через HTTP? | Нет, operator provisioning CLI |
| Можно читать/искать/выгружать историю через v1 HTTP? | Нет, operator SQL или отдельное дополнение |
| Есть пагинация, filters, webhooks, SSE/WebSocket? | Не реализованы |
| Есть OAuth/JWT пользовательская auth в `main`? | Не реализована; device token — непрозрачный Bearer secret |
| Есть browser CORS? | Middleware CORS не настроен; cross-origin integration требует отдельного решения |
| Есть MQTT? | Этот API использует HTTP JSON |
| Есть команды actuator, dashboard, sessions? | В `main` не реализованы; статус дополнения — ниже |
| Есть retention и automatic cleanup? | Не заданы и не реализованы как гарантия API |
| Какой rate limit и uptime SLA? | Contract этого лабораторного пилота их не обещает |
| Обязателен интервал 10 s для любого клиента? | Это политика готовых сборщиков, не validation HTTP endpoint |
| Отрицательное показание запрещено? | На уровне API нет; driver должен проверять физический диапазон |
| Timeout означает потерю данных? | Нет; сохраните пакет и повторите тот же ID |
| Можно очистить outbox после любого `200`? | Только после валидного совпадающего ACK |
| Кто задаёт measurement time? | Устройство; при недостоверных часах `null` |
| Повтор меняет timestamp хранения? | Нет, duplicate возвращает первоначальный `received_at` |

Append-only относится к API и ограниченному runtime. Это не обещание, что
администратор БД технически не может изменять данные, и не защита от потери
самого накопителя клиента. Наличие software tests не подтверждает поведение
каждого вида оборудования и не заменяет его отдельную приёмку.

### 13.3. Что считать успешным знакомством с API

Пользователь смог получить `alive`, отправить тестовый пакет с `201 stored`,
повторить его с `200 duplicate`, сверить UUID и первоначальный `received_at`,
объяснить различие `401`/`403`/`409`/`422` и сохранить пакет при timeout.
Оператор отдельно может подтвердить одну строку по message ID в выбранной БД.
Это приёмка учебного программного сценария, не hardware certification.

## 14. Версии и дополнения в разработке

Version prefix `/v1` относится к telemetry JSON contract. Для него всегда
передавайте `schema_version: 1`. Package version `0.0.0` не является
индикатором развернутого набора endpoints. Endpoint, который возвращает
version/Git SHA сервера, в текущем `main` отсутствует; версию уточняйте
у оператора. Не выводите её из того, что localhost или `/health/live` отвечают.

На момент проверки branch `feat/session-user-access`, commit
`480d0cdf6f533c025f781193f3ce7b1ed4ea5099`, содержит расширение с dashboard,
Auth, user profiles, schools, учебными сессиями, device context и v2 telemetry.
Оно не является частью описанного выше `main`. Новые маршруты требуют
отдельной схемы и полной серверной конфигурации дополнения.

| Область дополнения | Назначение |
| --- | --- |
| `/v1/auth/...` | Пользовательские register/login/refresh/logout/me с cookie authentication |
| `/v1/admin/...` | Административная работа с users/schools/devices |
| `/v1/sessions...` | Создание и просмотр сессий, состав, start/finish и чтение telemetry |
| `GET /v2/devices/{device_id}/context` | Device token получает текущий context назначения |
| `POST /v2/telemetry` | Сообщение с зафиксированной принадлежностью к session |
| `/` и dashboard assets | Пользовательский интерфейс дополнения |

Пошаговые руководства по этому дополнению:

- [Регистрация, вход, одобрение, cookies/CSRF, refresh и logout](AUTHENTICATION_TUTORIAL_RU.md).
- [Dashboard: экраны, роли, создание сессии и чтение истории](DASHBOARD_TUTORIAL_RU.md).

Этот перечень — навигация по разработке, не контракт работающего `main`.
Cookie authentication пользователей не заменяет device Bearer token.
Чтобы читать документацию именно этого branch snapshot:

- [Session/user-access handoff в ветке](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/docs/device_ingestion/SESSION_USER_ACCESS.md).
- [Protocol v2 в ветке](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/docs/device_ingestion/PROTOCOL_V2.md).

После объединения и реального развёртывания дополнения этот справочник следует
обновить по фактическим routes, схемам и validation. Нельзя получить v2,
просто изменив `schema_version` или URL запроса к серверу `main`.

## 15. Источники и устройство документации

Руководство объединяет практический tutorial, справочник, инструкции
для отдельных задач и объяснение delivery semantics. Такое разделение
потребностей читателя опирается на
[Diátaxis](https://diataxis.fr/start-here/).
Порядок «method/path/headers/auth/body → request → response» и учебные
запросы ориентированы на
[GitHub REST API getting started](https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api?tool=curl).
Явное описание каждой operation и её authentication согласуется с
[OpenAPI: API Endpoints](https://learn.openapis.org/specification/paths.html)
и [OpenAPI: Security](https://learn.openapis.org/specification/security.html).
Внешние источники определяют структуру документации; факты о TLM взяты
из репозитория, а не перенесены из чужого API.

Основные локальные источники:

| Источник | Что определяет |
| --- | --- |
| [ingestion.py](../../src/tlm_device_data_platform/ingestion.py) | Routes, HTTP headers, status codes, body read и error mapping |
| [telemetry_v1.py](../../src/tlm_device_data_platform/telemetry_v1.py) | Envelope, numeric/UUID/time validation и ограничения |
| [postgres_ingestion.py](../../src/tlm_device_data_platform/postgres_ingestion.py) | Credential binding, COMMIT, duplicate/conflict и storage settings |
| [serve_api.py](../../src/tlm_device_data_platform/serve_api.py) | Listener, TLS, concurrency settings |
| [provision.py](../../src/tlm_device_data_platform/provision.py) | Получение runtime/device credentials |
| [edge_agent.py](../../src/tlm_device_data_platform/edge_agent.py) | Linux outbox, ACK validation и retry policy |
| [PROTOCOL_V1.md](PROTOCOL_V1.md) | Протокольные решения пилота |
| [STAND_SETUP.md](STAND_SETUP.md) | Полная установка стенда |
| [SUPABASE_BRINGUP_RU.md](SUPABASE_BRINGUP_RU.md) | Операторский запуск с Supabase и диагностика |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Причины реализации и handoff проверки |

При расхождении с будущей версией сервера сверяйте фактический checkout,
его routes и deploy version. Исторические Git/CI/hardware записи в других
документах не являются проверкой нового развёртывания.
