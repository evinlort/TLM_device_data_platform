# Реализация приёма телеметрии — передача состояния

## Состояние Git и разрешённая работа

По прямому указанию пользователя PR #1 объединён в main merge commit
`20e2b7f1f845198556ba2ce73b86672de9a509ea`. Ветка
`ci/github-actions-foundation` затем fast-forward перемещена на тот же commit,
без force и без удаления. GitHub compare подтвердил identical, ahead=0,
behind=0. Устаревший Step 2 review thread предварительно проверен и закрыт
с объяснением, почему его handoff superseded завершёнными Steps 3–12.

После этой исторической записи PR #2 был объединён в `main` commit
`e0575205d4777c0c9e7a4838c3fa2179207192c4`, а ESP32 PR #3 — commit
`7baa7e908196762b6650a889c411403b919ee1fb`. Идентификаторы этапов ниже остаются
историческими контрольными точками, а не утверждениями о текущем HEAD checkout.

## Этап 1 — контракт и SQL

Добавлен отдельный `telemetry_v1.py`, а не переименован старый fixture.
Контракт валидирует UUID, последовательность, время и числовую карту показаний.
Тесты отклоняют boolean вместо числа, NaN/Infinity, переполненный float,
повторные JSON-ключи, неверные/лишние поля и превышение защитных лимитов.

Новая миграция создаёт devices, device_credentials и telemetry_messages в
схеме tlm. Исходная public.ingest_messages не изменена. Роль tlm_ingest
не имеет LOGIN/BYPASSRLS; runtime получает SELECT и INSERT только нужных
колонок, без подстановки received_at, изменения/удаления истории и credentials.
Это доверенный доступ backend, не будущая модель изоляции учеников.

Commit `948eb87b8113fb74c587bd17f058fe932bd28e96` прошёл оба job в CI run #27,
ID `36930195671`. Миграции применены в одноразовом локальном Supabase.
Исходные 18 и новые 16 pgTAP assertions образуют 34 SQL-проверки.

## Этап 2 — настоящий HTTP → PostgreSQL

FastAPI endpoint использует ограниченный body reader, проверяет протокол,
передаёт credential и envelope в PostgreSQL adapter. Адаптер определяет device_id
по хешу token, проверяет активность/отзыв/срок и принадлежность устройства.
Транзакция выполняется с READ COMMITTED; ACK возвращается только после COMMIT.
Новый пакет даёт 201/stored; идентичный повтор — 200/duplicate; подмена содержимого
или позиции потока — 409. Неуспех хранения никогда не подтверждается как доставка.

На первом сквозном запуске CI #34 обнаружил реальный race: PK-targeted
ON CONFLICT мог при конкурентном повторе получить violation второго unique
index и ошибочно вернуть 409. Проверка не ослаблена. Исправление использует
ON CONFLICT DO NOTHING для обоих индексов, затем отдельным SELECT сравнивает
неизменяемые поля по PK. Отсутствие совпадающего PK означает реальный конфликт
позиции потока. История не перезаписывается.

Исправление `d9ad8e3656ceca7dcda2528ad0d194529439c41f` прошло оба job CI #35,
ID `36931520332`, включая настоящий TCP HTTP, SQL и cleanup.
В следующем этапе конкурентный тест дополнительно повторяется пять раз с
барьером одновременного старта четырёх запросов.

## Этап 3 — агент и эксплуатационный запуск

Linux-агент читает выбранную функцию sensor adapter каждые 10 секунд.
Сбор и отправка независимы: медленная сеть не задерживает следующий сбор.
SQLite WAL с synchronous=FULL хранит исходные bytes и device binding.
После restart очередь открывается заново; новые показания получают новый stream,
а старые сообщения не переименовываются. Удаление происходит только после
совпадающего ACK. Повтор/timeout сохраняет очередь, постоянная ошибка пакета
переводит его в quarantine, ошибка credentials останавливает агент.
При заполнении лимита старые записи не вытесняются.

### Последующее исправление Linux HTTP timeout

Операторская сессия показала, что прежний default `5 s` мог завершить ожидание
раньше ACK: сохранённый пакет с диагностическим ожиданием получил `200 duplicate`
за `6.03 s`, а прямой `PostgresTelemetryRepository.accept()` вернул duplicate
за `5.74 s`. Это отдельные исторические замеры одного стенда, не SLA и не новая
проверка при обновлении документации. Timeout клиента не доказывает отсутствие
COMMIT на сервере.

Linux `HTTPSender` теперь использует именованный default `15.0 s` и допускает
обратно совместимый keyword-only `timeout_seconds` для управляемых тестов.
Ноль, отрицательные значения, NaN, infinity и `bool` отклоняются. Значения
PostgreSQL, SQL, SQLite, DNS/NTP, HC-SR04 и 10-секундный период сбора не менялись.

Default drain после завершения сбора увеличен с `10.0` до `16.0 s`: это HTTP
timeout `15.0 s` плюс `1.0 s` запаса на запуск и опрос worker. Bounded sender
join остаётся `6.0 s`. Shutdown координирует доступ к очереди: поздний
результат активного HTTP-запроса после сигнала остановки не подтверждает и не
карантинирует запись. Поэтому другой процесс не получает владение SQLite, пока
старый worker ещё способен её изменить. Pending-сообщения приводят к non-zero
завершению и сохраняют исходные bytes/ID для duplicate replay.

Реальный loopback regression test задерживает корректный ACK примерно на 6 секунд;
отдельные короткие тесты покрывают timeout/replay, точное сохранение двух записей,
duplicate ACK, `count=1` и остановку во время запроса. `urllib` timeout не является
строгим общим deadline, а `join(timeout=...)` не отменяет поток. Отдельный ESP32
`asyncio.wait_for(..., 10)` не менялся и требует аппаратной проверки.

Добавлены операторские provisioning-функции и CLI, создающие настоящий runtime
LOGIN и device credentials в выбранной БД. Требуется --apply; секреты попадают
только в новые owner-only JSON-файлы, а не в stdout или Git. При неопределённом
результате COMMIT файлы остаются для сверки и восстановления.
Серверный CLI по умолчанию слушает loopback; внешний listener требует TLS либо
отдельного явно небезопасного режима изолированной лаборатории.

Тесты проверяют постоянство очереди, capacity, ACK, ошибки HTTP, отсутствие
блокировки сбора сетью, permissions конфигурации, отказ перезаписи/симлинков.
Дополнительные database tests выполняют полный путь:

```text
provision runtime/device → private config → real API → restricted PostgreSQL login
reopened SQLite outbox → real HTTP sender → API → PostgreSQL row → queue deletion
```

Исторические результаты этапа 3 сохранены в merged PR #2. Точные результаты
последующего timeout-исправления нужно проверять в его отдельном PR → Checks на
опубликованном SHA; успех прежнего commit не подменяет результат нового.
Отсутствие `TLM_TEST_ADMIN_DSN` вызывает ошибку DB-тестов, а не скрытый skip.
Быстрый job явно исключает marker database; Supabase job запускает полный suite
с одноразовой локальной базой.

## Не выполнено и не заявлено

На этапе исходного PR #2 миграции не применялись к remote Supabase и сервис не
развёртывался. Позднее оператор отдельно проверил разрешённый development-проект
по [SUPABASE_BRINGUP_RU.md](SUPABASE_BRINGUP_RU.md); эта задача его не изменяет.
Физическая плата и реальные датчики не подключались. Программный demo_sensor явно
помечен тестовыми именами и не считается hardware test. Код Linux-агента не
является ESP32 firmware.

Перед аппаратным запуском использовать STAND_SETUP.md: выбрать dev-проект,
сверить migration history, применить проверенные migrations, зарегистрировать
runtime/device, запустить API и установить реальный sensor module.
Никакой remote reset или административные credentials на устройстве не нужны.

Не реализованы current_state, multi-school authorization, dashboard, команды
оборудованию, ротация token, retention, fleet-scale SLO и production deployment.
Это отдельные требования, не скрытые свойства лабораторной реализации.

**Последующая проверка 03.10.2026:** историческое утверждение выше об отсутствии
физической платы относится к исходному этапу. Позднее ESP32-D0WD-V3 с HC-SR04
передал реальные `distance_cm` через TLM API в Supabase. Подробности и границы:
[ESP32_REAL_HARDWARE_BRINGUP_RU.md](ESP32_REAL_HARDWARE_BRINGUP_RU.md).

## Руководство пользователя API — 09.10.2026

Руководство подготовлено отдельным локальным коммитом
`2606ee5a093a41a9a0c6491b00bf80a8cdce88a0`. Руководство и правила исключения
локальных secrets/device tooling отправлены в `feat/api-guide-and-local-ignores`
для объединения в `main` через PR #7. Эта запись описывает подготовку и отправку
изменений; фактическое слияние проверяется по Git refs и состоянию PR.
Исходный API проверен на `main` commit
`f6d9182be2a4790d6b5773998d7aa28d3b0ec251`; ветка
`feat/session-user-access` на commit `480d0cdf6f533c025f781193f3ce7b1ed4ea5099`
на момент проверки не объединена. Поэтому
[API_GUIDE_RU.md](API_GUIDE_RU.md) полностью описывает действующий контракт
`main`, а Auth/session/v2 дополнение обозначает отдельно как разработку.
В README добавлена ссылка на руководство.

Структура опирается на прочитанные web-источники Diátaxis, GitHub REST API
getting started и OpenAPI paths/security: назначение, первый запрос,
справочник, инструкции, объяснение ACK/retry, диагностика. Ссылки на источники
сохранены в самом руководстве. Фактические routes, headers, JSON validation,
credentials, duplicate/conflict, SQL storage и client policies сверены
с исходниками. Отдельно объяснено ограничение generated OpenAPI: он не описывает
полный ручной telemetry contract и не заменяет справочник пользователя.

При чтении GitHub check-runs для точного исходного `main` SHA и SHA дополнения
получено `total_count=0`. Это не результат новых CI-проверок и не перенос
исторического успеха PR на эти commits. В этой задаче изменяется только
документация; remote Supabase, hardware и deployment не проверяются.

Локальная проверка документации: 46 relative links/anchors, 32 fenced blocks,
15 Bash fragments (`bash -n`), два Python fragments (`compile`), пять JSON
examples (`json.loads`), telemetry example через настоящий `TelemetryV1.parse`.
Проверены все шесть route definitions, GET/HEAD страниц документации,
health response, отсутствие корневого dashboard в `main` и фактические
ограничения OpenAPI. Эти HTTP-проверки не подключаются к БД.

Команда `.venv/bin/python -m pytest -q -o pythonpath=src
-o faulthandler_timeout=20 tests/test_telemetry_v1.py tests/test_ingestion_api.py`
завершилась: **30 passed**. В sandbox FastAPI TestClient зависал; первоначальные
запуски остановлены, те же проверки успешно выполнены вне sandbox.
`git diff --check` проходит. Это targeted contract/documentation verification,
не новый полный database/CI/hardware результат; assertions и DB-тесты
не менялись. Изменены только руководство, README и эта запись handoff.

## Tutorials пользовательской аутентификации и Dashboard — 09.10.2026

Пользователь явно запросил подготовить оба tutorial в `main`, создать коммит
после завершения и выполнить push. Исходная локальная/remote main при проверке
равна `3864893dc5d76a9a5f011e1a3a60a115953413d6`; PR #7 объединён.
Session-user-access code остаётся отдельным snapshot
`480d0cdf6f533c025f781193f3ce7b1ed4ea5099`. Оба новых документа указывают эту
область применимости, не объявляют дополнение внедрённым в main или удалённо.
У обоих точных исходных SHA GitHub check-runs вернул `total_count=0`.
Исторические test results не перенесены на новое состояние.

[AUTHENTICATION_TUTORIAL_RU.md](AUTHENTICATION_TUTORIAL_RU.md) описывает
browser registration/login, pending approval, роли/школу/блокировку,
cookie/CSRF rotation, refresh/logout, все шесть Auth endpoints,
приватный curl workflow и user runtime/bootstrap-admin.
[DASHBOARD_TUTORIAL_RU.md](DASHBOARD_TUTORIAL_RU.md) описывает все экраны,
role-specific controls, admin preparation, draft/active/ended lifecycle,
roster immutability, paging и v2 delivery evidence после позднего replay.
Оба tutorial связаны с README и API guide. При сверке исправлен ошибочный
navigation path device context в API guide: фактически дополнение использует
`GET /v2/devices/{device_id}/context`.

Факты сверены с branch snapshot user_api.py, user_access.py, serve_api.py,
provision.py, HTML/JavaScript Dashboard, SQL migration и существующими
Auth/browser test scenarios. UI Refresh не вызывает history reload и
не является auto-polling; это явно объяснено. Registration helper запускается
отдельным Python-файлом, чтобы interactive input не конфликтовал с heredoc stdin.
Provider/session/logout пояснения проверены по официальным Supabase docs;
полный TLM contract определяется исходниками, не общей документацией provider.

Проверка документов: 81 local link/anchor и 15 ссылок на файлы/anchors точного
snapshot проверены через local Git objects; 25 Bash fragments проходят `bash -n`,
четыре Python fragments компилируются, десять JSON examples разбираются.
Три новых request examples проверены настоящими Pydantic models дополнения,
37 названий UI — HTML/JavaScript; route references сверены с declarations.
CSRF helper выполнен с отдельным TEST cookie jar, включая HttpOnly entry;
он формирует ожидаемый header без вывода session secrets.
`git diff --check` проходит. Это document/static verification без обращения
к Auth, БД или hardware; исходники и существующие tests не изменены.

Перед публикацией прочитана фактическая classic protection main:
required PR, `enforce_admins=true`, required contexts `Python 3.11` и
`Local Supabase integration`, strict status checks. Ruleset API вернул пустой
список, что не отменяет classic protection. Эта задача не меняет защиту ветки.
Результат нового push/CI нужно проверять по фактическому опубликованному SHA;
статические проверки документации не подменяют required integration CI.

## Проверка следующей сессии

Прочитать AGENTS.md и ingestion documents. Проверить фактические refs, текущий
PR, точный head SHA и соответствующий CI run. Не создавать ещё один
self-referential handoff commit только ради записи текущего HEAD. Не merge PR,
не удалять ветки и не менять remote Supabase без соответствующего указания.
