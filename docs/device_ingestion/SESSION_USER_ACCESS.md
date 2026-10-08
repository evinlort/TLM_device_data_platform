# Доступ пользователей и учебные сессии — handoff

## Область работы

Дополнение реализуется в `feat/session-user-access` от `origin/main`
`f6d9182be2a4790d6b5773998d7aa28d3b0ec251` (refs проверены при начале работы).
PR #6 объединён; открытых PR на момент проверки не было. CI для этого merge SHA
не найден. Эти сведения — контрольная точка, а не утверждение о будущем HEAD.

Основание ролей, школ и управления устройствами — явно переданный пользователем
план «Доступ к телеметрии по пользователям и учебным сессиям». Он расширяет v1:
student читает свои сессии; teacher читает и управляет сессиями своей школы;
manager читает всю историю; admin читает всю историю и управляет доступом,
школами, сессиями и школьными привязками уже зарегистрированных устройств.
Pending/disabled не получают телеметрию. Роль и статус проверяются в БД.

Удалённый target подтверждён в плане: development `zcpclncljcfvlloetbpv`.
В начале сессии в `.secrets/` был только CA certificate. Административный DSN,
Supabase URL/key, новый user runtime DSN и конфигурация управления Auth не
восстановлены; пользователю запрошены пути к приватной конфигурации и способ
запуска API. Remote migration history, dry-run, push, настройка hosted Auth,
развёртывание и remote TEST-сценарий **ещё не выполнены**. Remote reset не нужен.
Коммиты/push и точный CI опубликованного SHA записываются только после фактического
выполнения и при наличии разрешения. Merge, удаление веток и protection не входят.

## Схема и права

Ordered migration `20261008010000_add_session_user_access.sql` сохраняет обе
старые migrations и `public.ingest_messages`. Добавляет schools, user_profiles,
sessions, session_participants, session_devices, active_device_sessions и
device_contexts, nullable telemetry.session_id и версии 1/2.

Auth INSERT trigger создаёт pending-профиль, игнорируя metadata. Уже существующие
Auth users также получают pending-профили. Пароли остаются в Supabase Auth.
Первый admin назначается оператором по UUID существующего pending Auth user;
bootstrap запрещён, если approved admin уже существует.

Отдельная NOLOGIN-группа `tlm_user` не наследует `tlm_ingest`. Её runtime LOGIN
не видит device_credentials, не меняет телеметрию и не получает lifecycle-column
UPDATE. `UserRepository` отклоняет owner, superuser, BYPASSRLS, CREATEROLE,
CREATEDB, REPLICATION и членство в tlm_ingest. Проверенный Auth user ID задаётся
через transaction-local `set_config`; соединение и транзакция завершаются после
каждого запроса. Это доверенная backend identity, а не credential для браузера.
Схема tlm остаётся приватной, без доступа anon/authenticated/service_role.

RLS защищает чтение и управление. SQL helpers имеют фиксированный search_path
и явный EXECUTE grant только нужным backend roles. Roster triggers блокируют
изменение состава после старта, включая владельца таблиц. Partial mutable
snapshot не используется: исторические назначения остаются отдельно от активной
занятости, где device_id — primary key. Start/finish берут row locks; устройства
блокируются в порядке UUID. Start повторно проверяет статусы/школы участников и
устройств, требует непустые списки и атомарно назначает context revision.
Finish освобождает устройство, увеличивает revision и сохраняет roster.

Старый SQL assertion о трёх RLS-таблицах теперь явно проверяет три исходные
таблицы ingestion. Новая проверка отдельно требует RLS на всех десяти таблицах
схемы tlm. Старые contract assertions не ослаблены.

## Auth, API и браузер

`SupabaseAuth` использует httpx: signup, password grant, refresh grant,
server `/user` на каждый пользовательский запрос, logout scope=local.
Auth metadata и переданные user/session/device IDs не дают полномочий.
Ошибки validation не отражают password input, provider detail или tokens.

API: `/v1/auth/{csrf,register,login,refresh,logout,me}`;
`/v1/admin/schools`, `/v1/admin/users[/{user_id}]`,
`/v1/admin/devices[/{device_id}]`; `/v1/sessions`, `/v1/sessions/options`,
`PUT /v1/sessions/{id}/roster`, `POST .../{start,finish}`,
`GET .../telemetry`, `GET /v1/telemetry`.
Telemetry pagination: limit 1..200, offset, детерминированный порядок
received_at/device_id/message_id; next_offset=null заканчивает страницу.
Это не snapshot pagination и не гарантия retention.

Dashboard `/` и assets входят в тот же Python package/FastAPI process.
Auth tokens — HttpOnly cookies, SameSite=Strict, Secure для HTTPS; CSRF cookie
сравнивается с X-CSRF-Token, Origin проверяется для каждой записи. Сначала клиент
получает `/v1/auth/csrf`. Browser refresh обновляет cookies и CSRF, не открывая
tokens JavaScript. Logout очищает cookies и отзывает refresh-сессию; при сбое
provider сообщает ошибку отзыва. Supabase access JWT может оставаться действующим
до expiry после logout; блокировка профиля действует через проверку БД.
Пароль не сохраняется в dashboard storage; поле очищается после отправки.

Ссылки на provider contract:
[password Auth](https://supabase.com/docs/guides/auth/passwords),
[server user verification](https://supabase.com/docs/reference/python/auth-getuser),
[logout scopes и expiry JWT](https://supabase.com/docs/guides/auth/signout).
Восстановление пароля и подтверждение email не входят в пилот.

## Протокол v2 и клиентский контекст

v1 сохранён. v2 подробно описан в [PROTOCOL_V2.md](PROTOCOL_V2.md).
Session ID берётся из подтверждённого контекста при сборе, а не из времени
captured_at/received_at. Пакет сохраняется до отправки, не переписывается при
смене группы. Сервер принимает завершённые сессии по историческому назначению.
Duplicate сравнивает версию и session_id; изменённая принадлежность известного
message_id возвращает 409, в том числе при подстановке чужой сессии.

Linux хранит контекст в SQLite metadata той же durable outbox. Отдельный worker
обновляет его каждые две секунды после завершения предыдущего запроса. Startup
ждёт попытки обновления; offline может использовать ранее сохранённый контекст.
Без первого успешного контекста измерений v2 нет. После успешной доставки,
обнаруженной после offline, сбор ждёт нового контекста. Смена session_id создаёт
новый stream; count считает измерения независимо от stream sequence.
Context worker закрывается до освобождения очереди и не применяет поздний ответ.
Обнаружение восстановления связи происходит по успешному HTTP, а не по предположению
о Wi-Fi; до этого offline-контекст остаётся источником принадлежности.

ESP32 сохраняет последовательный persist → ACK режим. Контекст запрашивается
перед новым измерением при доступной сети. Во время недоступности API используется
последний сохранённый контекст; без него датчик не читается. Context sidecar
с checksum, staging/rename и flush расположен рядом с outbox и не занимает slot.
Коррупция требует оператора; автоматического format или замены на null нет.
После ACK следующий сбор сначала обновляет контекст. Pending старые packets
имеют приоритет, включая v1. Transport выбирает endpoint по исходному packet.

Dashboard показывает desired session/revision в API, подтверждение новой группы
по полученному v2 packet, последнюю подтверждённую ненулевую группу по максимальному
историческому context_revision и отдельно последнюю полученную принадлежность.
Поздний пакет старой группы не отменяет подтверждение новой. v2 передаёт только
session_id, поэтому пакет с null **не доказывает конкретную revision** отключения
группы; dashboard её не объявляет подтверждённой. Последний packet не является
current sensor state. Аппаратный v2 тест не выполнялся.

## TDD и локальная валидация

RED → GREEN → REFACTOR зафиксированы в локальных `var/*-red.log` и последующих
logs (не коммитятся; ниже воспроизводимые команды, а не требование доверять log).

- SQL RED: 11/12 отсутствующих объектов/ролей, исходная fixture таблица прошла.
  GREEN: 72 pgTAP assertions после ordered migration и повторно после local reset.
  Включены RLS, metadata escalation, immutability, lifecycle privileges,
  освобождение устройства и revision. Отдельный PostgreSQL upgrade test применяет
  старые migrations, сохраняет opaque fixture bytes и v1 history, затем новую
  migration; исходные колонки и received_at остаются идентичными, session_id=NULL.
- Auth RED: отсутствующий provider/repository; GREEN: настоящий TCP HTTP →
  локальный Supabase Auth → ограниченный PostgreSQL LOGIN. Дополнительные RED
  выявили INSERT RETURNING RLS visibility, roster lock filtering и 403 вместо
  требуемого 409 изменённой принадлежности. Исправлены policy/порядок checks.
  Проверяется refresh token rotation и фактический отказ Auth после logout.
- Изоляция: student своей/чужой сессии, teacher школ, manager/admin global history,
  pending/disabled, cross-school create, forged JWT/IDs, self elevation, CSRF,
  Origin, redaction invalid password. Concurrent start даёт ровно 200/409.
- Клиенты RED: отсутствующая context persistence и разрешённый сбор до startup
  refresh. GREEN: mixed replay/reboot, offline, stream change, независимый Linux
  refresh, отсутствие ESP32 measurements без первого context. Настоящие Linux
  sender и те же ESP32 transport sources дополнительно проверены против API/БД.
  Получение поздней старой группы не отменяет новое dashboard confirmation.
- UI RED: отсутствующее поле Email на исходной placeholder page; затем поле
  Students не имело устойчивого accessible name. GREEN: Chromium registration →
  pending → admin approval → student login/read, teacher create/start/packet
  confirmation/end. API/Auth/DB настоящие, перехвата routes и mocks нет.
- MicroPython: все шесть исходников скомпилированы mpy-cross 1.29.0 из commit
  `0fd6c573ea815774668bbb16b8e197c8822368b2`, `-march=xtensawin`.

Required CI устанавливает Chromium и запускает тот же full suite через
`scripts/test_local.py`. Он берёт только local CLI status, без печати credentials.
Нет конфигурации — ошибка, без skips. Local-only guards проверяют host/hostaddr и
Auth origin. Local Auth sign-in limit повышен до 300 для независимых TEST fixtures;
это исключительно disposable config, не hosted Auth setting.

```bash
npm ci
npx --no-install supabase start >/dev/null
npx --no-install supabase db reset --local
npx --no-install supabase test db
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/test_local.py --junitxml=test-results/session-access.xml -q
npx --no-install supabase stop --no-backup
```

В этой рабочей среде использован отдельный rootless Docker socket; системный Docker
пользователю недоступен. Локальный reset относился только к созданному для задачи
disposable stack. Никаких remote операций или подключения физической платы.

## Проверенная локальная контрольная точка 08.10.2026

После local reset: 72 pgTAP assertions; полный Python 3.11 suite —
320 passed за 44.18 s, без failures/skips. Два Chromium сценария входят
в этот suite. Wheel проверен на наличие всех трёх dashboard assets; pip check
успешен. Все шесть ESP32 modules повторно скомпилированы MicroPython 1.29.0.
Снимки student/teacher UI визуально проверены локально в `var/`.
После форматирования и разделения test modules: 287 quick tests и 9 целевых
Auth/API/client/browser tests прошли; AST четырёх production modules совпадает
с проверенным wheel. Отдельный negative run без конфигурации получил 5 явных
ошибок, подтверждая отсутствие скрытых database/Auth skips.
Disposable Supabase и отдельный rootless Docker daemon остановлены.

Разрешение на локальный commit получено от пользователя 08.10.2026.
Новая feature branch пока не опубликована и PR не создан; разрешение на push
и draft PR ещё не получено. CI нового SHA до публикации не существует.
Удалённая конфигурация также запрошена, но не предоставлена.
Не считать локальные результаты CI или remote/hardware validation.
