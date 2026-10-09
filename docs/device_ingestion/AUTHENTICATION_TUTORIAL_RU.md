# TLM: регистрация, вход и доступ пользователей

Это пошаговое руководство по пользовательской аутентификации: как
зарегистрироваться, получить одобрение, войти, обновить сессию и выйти.
Оно также объясняет cookies, CSRF, роли, административное одобрение
и обращения к Auth endpoints из собственного HTTP-клиента.

**Доступность:** описано дополнение `feat/session-user-access`, snapshot
`480d0cdf6f533c025f781193f3ce7b1ed4ea5099`, проверенное по исходникам
09.10.2026. На момент подготовки `main` находится на commit
`3864893dc5d76a9a5f011e1a3a60a115953413d6` и не содержит этого дополнения.
Документ хранится в `main`, но его наличие не включает Auth или Dashboard
на сервере. Для выполнения шагов нужен отдельный, подготовленный оператором
сервер с кодом, схемой и полной конфигурацией дополнения.
Удалённое развёртывание этим руководством не подтверждается.

Аутентификация **устройства** через `Authorization: Bearer <device-token>`
описана в [руководстве API](API_GUIDE_RU.md#4-аутентификация-и-получение-доступа).
Для входа человека нужны email/password и пользовательские cookies.
Операции Dashboard разобраны в [отдельном tutorial](DASHBOARD_TUTORIAL_RU.md).

## Содержание

1. [Как устроены аккаунт и доступ](#1-как-устроены-аккаунт-и-доступ)
2. [Что получить перед началом](#2-что-получить-перед-началом)
3. [Регистрация и первый вход в браузере](#3-регистрация-и-первый-вход-в-браузере)
4. [Одобрение и блокировка администратором](#4-одобрение-и-блокировка-администратором)
5. [Как работают cookies, CSRF и обновление](#5-как-работают-cookies-csrf-и-обновление)
6. [Справочник Auth endpoints](#6-справочник-auth-endpoints)
7. [Пошаговый пример через curl](#7-пошаговый-пример-через-curl)
8. [Подготовка сервера и первого администратора](#8-подготовка-сервера-и-первого-администратора)
9. [Ошибки и восстановление доступа](#9-ошибки-и-восстановление-доступа)
10. [Проверка результата и источники](#10-проверка-результата-и-источники)

## 1. Как устроены аккаунт и доступ

**Аутентификация** отвечает на вопрос, кто вошёл: email/password проверяет
Supabase Auth, а TLM API получает подтверждённый user UUID. **Авторизация**
определяет, что этому человеку разрешено: TLM проверяет статус, роль, школу
и принадлежность к сессии в PostgreSQL. Успешный login не гарантирует
доступ к телеметрии.

```text
Register with email/password
  -> Auth identity
  -> TLM profile: pending
  -> administrator assigns role/school and approves
  -> login or refresh the workspace
  -> read/manage permitted sessions
  -> logout
```

Регистрация создаёт профиль `pending` с `role: null` и `school_id: null`.
Нельзя получить роль, добавив `role: admin` в registration body или metadata.
В работе дополнения существующие Auth identities тоже получают pending-профили
при первоначальной миграции; наличие старого аккаунта само по себе не даёт доступ.

| Статус | Что видит пользователь | Доступ к данным |
| --- | --- | --- |
| `pending` | `Awaiting administrator approval` | Нужны роль и одобрение администратора |
| `approved` | Workspace в пределах назначенной роли | Разрешён согласно роли и принадлежности |
| `disabled` | `Access disabled` | Телеметрия и управление недоступны |

Pending/disabled пользователь может успешно пройти проверку email/password
и получить свой профиль. Это позволяет показать понятный экран статуса.
Блокировка TLM-профиля не равнозначна удалению Auth account.

| Роль | Доступ после одобрения |
| --- | --- |
| `student` | Чтение сессий, в состав которых пользователь включён |
| `teacher` | Чтение и управление сессиями своей школы |
| `manager` | Чтение всех сессий и общей истории телеметрии |
| `admin` | Чтение всей истории, управление сессиями, школами, доступом и школьными привязками устройств |

Для approved `student` и `teacher` обязательна школа. Для `manager`/`admin`
школа может отсутствовать. Только `admin` назначает роли и статусы через UI/API.
Teacher не одобряет пользователей; student не выбирает свою роль при регистрации.

«Пользовательская сессия входа» — cookies и Auth session.
«Учебная сессия» — лабораторная группа с учениками и устройствами.
Это разные сущности: login не создаёт учебную сессию и не назначает устройство.

## 2. Что получить перед началом

Получите у оператора фактический **TLM origin**, например
`https://tlm-api.example.org`. Это заглушка: замените её адресом своего стенда.
Dashboard открывается по `/` этого origin. Адрес Supabase project не является
адресом TLM Dashboard.

Нужны доступ к сети сервера, доверенный TLS certificate, email для аккаунта
и пароль. Для учебной проверки используйте согласованные TEST-аккаунты.
Данные регистрации сохраняются в реально выбранном Auth/DB окружении.
Database DSN, Supabase management/service keys и device token для login
пользователю не выдаются.

Уточните, что оператор уже:

1. Установил код дополнения и применил его ordered migration.
2. Настроил отдельный user runtime, Auth и внешний origin.
3. Подготовил первого администратора или готов выполнить bootstrap.
4. Согласовал нужные роль и школу.

Если `/` отвечает `404`, не пытайтесь решить это сменой пароля: сервер v1
из `main` не содержит Dashboard. `/health/live` подтверждает жизнь процесса,
но не наличие пользовательского дополнения и не доступность Auth/БД.

## 3. Регистрация и первый вход в браузере

### 3.1. Создайте новый аккаунт

1. Откройте подтверждённый адрес TLM в браузере.
2. Найдите форму `Access your laboratory`.
3. Введите email в `Email` и пароль в `Password`.
4. Нажмите **Register** один раз и дождитесь результата.

При успешной новой регистрации HTTP API возвращает `201` и профиль,
браузер получает cookies, а workspace показывает
**Awaiting administrator approval**. Поле пароля очищается после отправки.

У registration/login body ровно два поля: `email` и `password`.
На уровне TLM email имеет длину 3–254 символа и простой формат
с `@` и доменной частью; password — 8–1024 символа. Supabase Auth может
применять дополнительную password policy. Наличие UI-проверки не заменяет
проверку сервером.

В выбранном пилоте оператор должен отключить email confirmation
в Auth-конфигурации целевого окружения. Tutorial не содержит шага
«перейдите по confirmation email»: этот flow здесь не реализован.
Настройка local Supabase не изменяет hosted project автоматически.

### 3.2. Получите одобрение

Сообщите администратору email, нужную роль и согласованную школу.
Пароль передавать ему не требуется. Администратор найдёт профиль
в `User access` и назначит доступ по разделу 4.

Пока профиль pending, таблицы телеметрии недоступны. Ожидание одобрения
не означает неправильный пароль или сетевой сбой.

После сообщения администратора нажмите **Refresh** в workspace.
Этот action перечитывает профиль; повторная регистрация не нужна.
Если сессия входа уже недействительна, войдите снова через **Log in**.

### 3.3. Войдите в существующий аккаунт

1. Откройте тот же origin.
2. Введите существующие email/password.
3. Нажмите **Log in**.
4. Проверьте email в шапке и роль/статус в workspace.

Успешный login возвращает `200` с профилем, а не raw tokens в JSON.
Видимые разделы определяются текущим TLM-профилем. Для `disabled` вместо
рабочих данных показывается **Access disabled**; обратитесь к администратору.

### 3.4. Выйдите и смените аккаунт

Нажмите **Log out**. Интерфейс возвращается к форме входа и очищает таблицы.
Успешный server logout отзывает текущую Auth session и удаляет cookies.
Затем можно войти другим аккаунтом.

Если provider недоступен во время выхода, приложение очищает cookies
и показывает ошибку отзыва. Возврат к форме сам по себе не подтверждает
успешную удалённую revocation. Access JWT также может оставаться действительным
до истечения срока; блокировка TLM-профиля отдельно запрещает доступ к данным.
Logout имеет scope `local`: это выход из текущей Auth session,
а не команда «выйти со всех устройств».

## 4. Одобрение и блокировка администратором

### 4.1. Одобрите профиль

Войдите как approved `admin`. При необходимости сначала добавьте школу
через `Schools` → `School name` → **Add school**.

В пилоте email confirmation отключено: email в pending-профиле — заявление
пользователя, а не доказательство владения адресом или личности. **До назначения
роли и одобрения независимо проверьте человека и связь с конкретным аккаунтом**:

1. Свяжитесь с человеком лично или по заранее известному доверенному каналу,
   установленному независимо от формы регистрации. Согласуйте его роль и школу.
2. Попросите проверенного человека войти в созданный им аккаунт и показать
   `user_id` из `/v1/auth/me`; сопоставьте этот UUID с выбранным pending-профилем.
3. Одобряйте только сверенный профиль. Если личность или связь с аккаунтом
   не подтверждены, оставьте статус `pending` и не назначайте роль.

Совпадение введённого email, фамилии или metadata само по себе не заменяет
эту проверку. Это операторский шаг: API не выполняет независимую проверку
личности и в выбранном режиме не подтверждает владение email автоматически.

В разделе **User access**:

1. Найдите нужную строку по `Email`.
2. В `Role` выберите `student`, `teacher`, `manager` или `admin`.
3. В `School` задайте согласованную школу; для student/teacher это обязательно.
4. В `Status` выберите `approved`.
5. Нажмите **Save** в этой строке.
6. Дождитесь **Saved** и нажмите общий **Refresh**, чтобы перечитать запись.

Тот же порядок проверки обязателен при программном одобрении.
Для программного управления
используется `PATCH /v1/admin/users/{user_id}` с user cookies и CSRF.
Body обязан содержать все три поля:

```json
{
  "role": "student",
  "school_id": "11111111-1111-4111-8111-111111111111",
  "status": "approved"
}
```

UUID здесь иллюстративный; замените его UUID существующей согласованной школы.
Нельзя передавать этот JSON в register/login: те endpoints запрещают лишние fields.

### 4.2. Заблокируйте или восстановите доступ

Для блокировки выберите `disabled` и нажмите **Save**.
Роль и школа могут сохраняться в профиле для дальнейшего восстановления.
При следующем обращении к защищённым данным сервер проверит статус
в БД и откажет в доступе; смена браузера не обходит проверку.

Для восстановления проверьте роль/школу, выберите `approved` и сохраните.
Пользователь нажимает **Refresh** или входит снова.
Для возврата в `pending` нужно одновременно выбрать `Unassigned`
для **Role** и **School**: pending-профиль требует оба значения `null`.
Нарушение этих зависимостей даёт conflict, даже если каждый field
в отдельности имеет допустимый тип.

UI позволяет администратору менять также собственную роль/статус.
Сначала обеспечьте сохранение согласованного административного доступа:
автоматическая защита «последний admin» в этой реализации не заявлена.

## 5. Как работают cookies, CSRF и обновление

### 5.1. Cookies вместо пользовательского Bearer header

```text
Browser -> GET /v1/auth/csrf -> CSRF cookie
Browser -> POST /v1/auth/login + matching CSRF header + credentials
TLM API -> Supabase Auth -> verified user ID -> TLM profile
TLM API -> access/refresh/CSRF cookies + profile JSON
Browser -> permitted requests with cookies
```

| Cookie | Для чего | Свойства выбранной реализации |
| --- | --- | --- |
| `tlm_access` | Проверка identity через Auth `/user` | `HttpOnly`, `SameSite=Strict`, `Path=/`; `Secure` для HTTPS |
| `tlm_refresh` | Обновление Auth session | Те же свойства, недоступна JavaScript |
| `tlm_csrf` | Сопоставление cookie с `X-CSRF-Token` | Доступна JavaScript, `SameSite=Strict`, `Path=/`; `Secure` для HTTPS |

Frontend не получает access/refresh tokens из JSON и не сохраняет пароль
в dashboard storage. Не копируйте пользовательские cookies в device config.
Device Bearer token не даёт вход в user endpoints.

`tlm_access` получает cookie Max-Age из Auth `expires_in` (fallback 3600 s),
`tlm_refresh` — 30 дней. Cookie lifetime не является обещанием длительности
Auth session: provider policies, отзыв и доступность сервиса влияют отдельно.

### 5.2. CSRF и Origin

Перед **register, login, refresh или logout** сначала нужен
`GET /v1/auth/csrf`. Он возвращает `200 {"status":"ready"}`
и устанавливает `tlm_csrf`. При изменяющем запросе клиент отправляет
это cookie и такое же значение в `X-CSRF-Token`.

То же правило действует для admin/session writes. При наличии `Origin`
сервер сравнивает его с настроенным публичным origin; неверный origin
отклоняется. Dashboard обращается к тому же origin, что и страница.
Это API не содержит настроенного cross-origin frontend flow.

Login, register и успешный refresh заменяют CSRF cookie. Следующий
изменяющий запрос должен прочитать **новое** значение; нельзя один раз
сохранить header при старте и использовать после всех обновлений.
Ответ `403 CSRF token required` часто означает именно устаревший header
или отсутствие cookie jar, а не неверный пароль.

### 5.3. Обновление пользовательской сессии

`POST /v1/auth/refresh` использует `tlm_refresh` из cookie,
проверяет новый access token через provider и выдаёт обновлённые cookies.
JSON-ответ — `{"status":"refreshed"}`. Тело с raw refresh token
не заменяет обязательную cookie.

Dashboard пытается восстановить сессию при загрузке страницы. Если
обычный запрос workspace получает `401`, он выполняет один refresh
и повторяет запрос один раз. Это не фоновый timer и не бесконечный retry.
Refresh error может потребовать нового login; её нельзя трактовать
как изменение пароля без диагностики.

**Refresh** в toolbar перечитывает workspace и при необходимости запускает
Auth recovery. Это не отдельная кнопка управления refresh token.
После изменения ролей server-side проверка прав использует БД,
а старые элементы UI исчезают после перечитывания профиля.

## 6. Справочник Auth endpoints

Все пути относятся к **TLM origin**, а не к Supabase origin.
JSON responses не содержат пароль или access/refresh token.

| Метод и путь | Нужные данные | Успех | Результат |
| --- | --- | --- | --- |
| `GET /v1/auth/csrf` | Без login | `200` | `status: ready`, CSRF cookie |
| `POST /v1/auth/register` | CSRF + JSON email/password | `201` | Профиль нового аккаунта и session cookies |
| `POST /v1/auth/login` | CSRF + JSON email/password | `200` | Текущий профиль и session cookies |
| `GET /v1/auth/me` | Access cookie | `200` | Собственный TLM-профиль, включая pending/disabled |
| `POST /v1/auth/refresh` | CSRF + refresh cookie; body не нужен | `200` | `status: refreshed`, новые cookies |
| `POST /v1/auth/logout` | CSRF + access/refresh cookies; body не нужен | `200` | `status: logged_out`, удаление cookies |

Registration/login body, с учебными заглушками:

```json
{
  "email": "test-user@example.org",
  "password": "REPLACE_WITH_PRIVATE_PASSWORD"
}
```

Не используйте опубликованный example password для реального аккаунта.
Профиль после регистрации имеет такую структуру; UUID/email иллюстративные:

```json
{
  "user_id": "22222222-2222-4222-8222-222222222222",
  "email": "test-user@example.org",
  "role": null,
  "school_id": null,
  "status": "pending"
}
```

Одобрение меняет `role`, `school_id` и `status`, не `user_id`.
У `/me` нет параметра для выбора чужого пользователя; переданный
`user_id` в URL не даёт полномочий.
Поддержка password reset, password change, email confirmation UI,
OAuth/social login, MFA и logout-all в этом дополнении не реализована.
Возможности Supabase как провайдера не включаются автоматически в TLM UI.

## 7. Пошаговый пример через curl

Этот пример нужен интегратору, проверяющему тот же flow без браузера.
Используются Bash, Python 3 и `curl` с чтением headers из файла.
Пароль вводится скрыто и не помещается в shell history/аргументы команды.
Cookie jar и response headers содержат session secrets: работайте
в приватном каталоге вне Git и не публикуйте их.

### 7.1. Получите CSRF cookie

Выберите новый tutorial-каталог и реальный origin без завершающего `/`:

```bash
umask 077
mkdir tlm-auth-tutorial
cd tlm-auth-tutorial
export TLM_API_BASE_URL='https://tlm-api.example.org'
curl --silent --show-error \
  --cookie-jar cookies.txt \
  --output csrf-result.json \
  --write-out '%{http_code}\n' \
  "$TLM_API_BASE_URL/v1/auth/csrf"
python3 -m json.tool csrf-result.json
```

Ожидайте `200` и `ready`. Для согласованного локального сервера
origin может быть `http://127.0.0.1:8000`, если именно так настроено дополнение.
Не отключайте TLS verification для удалённого сервера.

### 7.2. Подготовьте credentials и функции отправки

```bash
cat > prepare_credentials.py <<'PY'
from getpass import getpass
import json

email = input("Email: ").strip()
password = getpass("Password: ")
with open("credentials.json", "x", encoding="utf-8") as stream:
    json.dump({"email": email, "password": password}, stream)
    stream.write("\n")
print("Private credentials file created; no password printed.")
PY
python3 prepare_credentials.py

make_csrf_header() {
  python3 - <<'PY'
from http.cookiejar import MozillaCookieJar
from pathlib import Path

jar = MozillaCookieJar("cookies.txt")
jar.load(ignore_discard=True, ignore_expires=True)
tokens = [cookie.value for cookie in jar if cookie.name == "tlm_csrf"]
if len(tokens) != 1:
    raise SystemExit("Expected one CSRF cookie; keep this jar for one TLM origin")
Path("csrf.headers").write_text(
    "Content-Type: application/json\nX-CSRF-Token: " + tokens[0] + "\n",
    encoding="ascii",
)
PY
}

auth_post() {
  local auth_path="$1"
  shift
  make_csrf_header || return
  curl --silent --show-error \
    --request POST \
    --cookie cookies.txt \
    --cookie-jar cookies.txt \
    --header @csrf.headers \
    --header "Origin: $TLM_API_BASE_URL" \
    --output response.json \
    --dump-header response.headers \
    --write-out '%{http_code}\n' \
    --connect-timeout 5 \
    --max-time 30 \
    "$@" \
    "$TLM_API_BASE_URL$auth_path"
}
```

Helper `prepare_credentials.py` запускается из терминала и создаёт новый
`credentials.json` без overwrite. Определите функции в том же Bash-сеансе.
Header пересоздаётся из актуального
cookie jar перед каждым POST, поэтому rotation CSRF учитывается.
Jar предназначен для одного origin и одного пользовательского сеанса;
не выполняйте конкурирующие refresh с теми же файлами.
`30 s` — выбранный timeout примера, не SLA API.

### 7.3. Register или login

Для **нового согласованного TEST-account**:

```bash
auth_post /v1/auth/register --data-binary @credentials.json
python3 -m json.tool response.json
```

Ожидайте `201` и pending-профиль. Для **уже существующего аккаунта**
используйте login вместо register:

```bash
auth_post /v1/auth/login --data-binary @credentials.json
python3 -m json.tool response.json
```

Ожидайте `200` и текущий профиль. Эти команды — альтернативы по состоянию
аккаунта. Registration не нужно повторять при каждом входе.
Если registration потерял ответ, аккаунт мог уже создаться: попробуйте login
или попросите оператора проверить состояние, прежде чем повторять создание.

`curl` без `--fail` может завершиться успешно как процесс при HTTP error:
всегда проверяйте напечатанный HTTP code и `response.json`.
Ошибка Auth не получает automatic retry в этом примере.

### 7.4. Прочитайте собственный профиль

```bash
curl --silent --show-error \
  --cookie cookies.txt \
  --cookie-jar cookies.txt \
  --output profile.json \
  --write-out '%{http_code}\n' \
  "$TLM_API_BASE_URL/v1/auth/me"
python3 -m json.tool profile.json
```

GET не требует CSRF header. Pending-профиль можно прочитать до одобрения.
После административного изменения повторите этот GET: должен измениться
статус/роль, а не user UUID. `curl` не выполняет browser auto-refresh;
при `401` следующий шаг может восстановить session.

### 7.5. Обновите session и выйдите

```bash
auth_post /v1/auth/refresh
python3 -m json.tool response.json

auth_post /v1/auth/logout
python3 -m json.tool response.json
```

При успехе получите последовательно `200 refreshed` и `200 logged_out`.
Cookie jar обновляется после каждого ответа. После logout `/me` должен
возвращать `401`. Для нового login сначала снова получите CSRF cookie
по 7.1: logout удаляет также `tlm_csrf`.

По завершении удалите учебный файл с password и session material
в соответствии с правилами стенда. Не передавайте `response.headers`,
`cookies.txt`, `credentials.json` и `csrf.headers` как обычные diagnostic logs.

## 8. Подготовка сервера и первого администратора

Эта часть предназначена оператору дополнения. Команды и конфигурация ниже
не поддерживаются сервером из текущего `main`; выполняйте их только
в установленной версии с user/session кодом и на выбранном разрешённом target.
Здесь документируется порядок, а не выполняется deployment.

Проверьте migration history и примените ordered migration
`20261008010000_add_session_user_access.sql` вместе с сохранённой старой
историей. Создайте отдельный ограниченный LOGIN для группы `tlm_user`:

```bash
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config /secure/admin.secret.json \
  --apply user-runtime \
  --output /secure/user-runtime.secret.json
```

Session pooler при необходимости требует `--pooler-project-ref <DEV_PROJECT_REF>`.
Direct connection этот параметр не использует. Не объединяйте `tlm_user`
и `tlm_ingest` в одной runtime identity; существующий ingestion DSN сохраняется.
Для remote PostgreSQL нужен `sslmode=verify-full`.

Полная private server config с правами `0600`:

```json
{
  "TLM_DATABASE_DSN": "<RESTRICTED_INGESTION_DSN>",
  "TLM_USER_DATABASE_DSN": "<SEPARATE_RESTRICTED_USER_DSN>",
  "TLM_SUPABASE_URL": "https://<CONFIRMED_PROJECT_REF>.supabase.co",
  "TLM_SUPABASE_KEY": "<PROJECT_PUBLISHABLE_OR_ANON_AUTH_KEY>",
  "TLM_PUBLIC_ORIGIN": "https://tlm-api.example.org"
}
```

`TLM_PUBLIC_ORIGIN` должен совпадать с фактическим внешним origin,
включая нестандартный port, если он есть: без path, query, fragment
и завершающего `/`. При HTTPS cookies получают `Secure`, даже если
Uvicorn за reverse proxy слушает loopback HTTP. Все четыре user-настройки
обязательны вместе; частичная конфигурация останавливает server startup.
Private server config не копируется в браузер или на устройство.

В выбранном Auth окружении явно настройте пилот без email confirmation.
Supabase для hosted проектов имеет отдельную настройку подтверждения email;
подробности — в [официальном password Auth guide](https://supabase.com/docs/guides/auth/passwords).
Включение recovery/confirmation flows требует дополнительной реализации TLM.
При этом обязательна независимая проверка личности и связи с аккаунтом
перед выдачей доступа по [разделу 4.1](#41-одобрите-профиль), в том числе
для первого администратора. Заявленный email не подтверждает личность.

Запуск установленного дополнения:

```bash
.venv/bin/python -m tlm_device_data_platform.serve_api \
  --config /secure/server.secret.json
```

Зарегистрируйте согласованного будущего администратора. Перед bootstrap
независимо проверьте человека и связь с его аккаунтом по разделу 4.1.
Получите точный
`user_id` из `/v1/auth/me` или операторской проверки выбранной БД.
Первый pending-профиль можно явно повысить:

```bash
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config /secure/admin.secret.json \
  --apply bootstrap-admin \
  --user-id '<EXPLICIT_PENDING_AUTH_USER_UUID>'
```

Команда меняет роль на `admin`, статус на `approved`, школу на `null`.
Она запрещена, если уже существует approved admin, и требует существующий
pending Auth user. Дальнейшее одобрение выполняется через admin UI/API.
Нет default administrator email/password и автоматического повышения
«первого зарегистрировавшегося» пользователя.

Полный технический deployment handoff и схемы — в
[snapshot SESSION_USER_ACCESS.md](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/docs/device_ingestion/SESSION_USER_ACCESS.md)
и [дополнении STAND_SETUP.md](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/docs/device_ingestion/STAND_SETUP.md#дополнение-dashboard-пользователи-и-v2).

## 9. Ошибки и восстановление доступа

Ожидаемое error body: `{"detail":"..."}`. Validation не отражает
введённый password или provider tokens. Proxy/internal failures
могут иметь другой формат.

| Ответ/симптом | Что означает | Действие |
| --- | --- | --- |
| `401 Login required` | Нет access cookie | Login или refresh при наличии refresh cookie |
| `401 Authentication rejected` | Provider отклонил credentials/session | Проверьте email/password и состояние аккаунта; не делайте бесконечные retries |
| `401 Refresh session required` | Нет refresh cookie | Выполните login заново |
| `403 CSRF token required` | Cookie/header отсутствуют или не совпадают | Получите CSRF, сохраните cookies, перечитайте header после login/refresh |
| `403 Invalid request origin` | Origin не совпадает с настроенным | Проверьте фактический URL и `TLM_PUBLIC_ORIGIN` у оператора |
| `403 Administrator approval required` | Профиль не approved | Посмотрите `/me`, дождитесь одобрения/восстановления |
| `403 Role does not permit this action` | Роль не даёт нужную операцию | Используйте сценарий своей роли или согласуйте доступ |
| `403 User profile unavailable` | Auth identity есть, TLM profile не найден | Оператор проверяет migration/profile, не пересоздавайте аккаунт вслепую |
| `409 Session or assignment conflict` при admin Save | Нарушены зависимости role/school/status | Approved student/teacher требуют школу; pending требует null role/school |
| `422 Invalid request fields` | Неверные fields/types/email/password | Передавайте только email/password допустимой длины |
| `503 Authentication provider unavailable` | Auth/network error либо provider `429`/`5xx` | Повторите позже; длительный сбой передайте оператору |
| `503` с сообщением об email confirmation | Provider не выдал usable session | Оператор проверяет pilot Auth configuration; подтверждение email не реализовано |
| `503 User storage unavailable` | Ошибка user DB | Проверить отдельный user DSN, migrations и permissions |
| Cookie не сохраняются | HTTPS/origin/доверие и настройки cookies не соответствуют окружению | Используйте согласованный origin, проверьте server/proxy configuration |
| Register timeout | Ответ неизвестен, account мог создаться | Попробуйте login/операторскую сверку вместо слепой повторной регистрации |

При регистрации с включённым email confirmation snapshot может сообщить
`Authentication rejected` уже на проверке отсутствующего access token,
прежде чем сформировать отдельную ошибку confirmation. Не диагностируйте
настройку provider только по одной конкретной английской фразе.

Забытый пароль, изменение email/password и account deletion не имеют
пользовательского workflow в этом пилоте. Обратитесь к оператору для
согласованного решения через provider; повторная регистрация с другим email
создаёт новую identity и не переносит историю/участие автоматически.

Для диагностики передайте operator время, origin, HTTP code, безопасный
`detail` и user UUID/email по правилам стенда. Password, cookies, CSRF,
DSN и provider keys в сообщение не включайте.

## 10. Проверка результата и источники

Учебный flow завершён, когда пользователь зарегистрирован как pending,
администратор одобрил правильный профиль, пользователь видит свою роль,
может выполнить разрешённый запрос, успешно обновляет session и выходит.
После logout `/me` возвращает `401`; отключённый профиль не читает историю.
Эти критерии описывают ожидаемое поведение, а не новую выполненную проверку
удалённого стенда.

Контракт сверяется с зафиксированными исходниками:

- [user_api.py: routes, models, cookies и CSRF](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/user_api.py).
- [user_access.py: provider verification и проверка профиля](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/user_access.py).
- [provision.py: первый admin и user runtime](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/provision.py).
- [Session migration: роли, статусы и RLS](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/supabase/migrations/20261008010000_add_session_user_access.sql).

Пояснение provider session/access/refresh основано также на
[Supabase user sessions](https://supabase.com/docs/guides/auth/sessions),
а ограничение logout scope и срок действия JWT — на
[Supabase signing out](https://supabase.com/docs/guides/auth/signout).
Порядок tutorial и справочника следует
[Diátaxis](https://diataxis.fr/start-here/), использованному в API guide.
Свойства TLM определяют исходники snapshot; текущие возможности provider
не являются обещанием наличия таких функций в приложении.
