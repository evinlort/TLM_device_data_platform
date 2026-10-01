# Локальная проверка, диагностика CI и подготовка branch protection

## Назначение и границы

Этот документ описывает, как локально воспроизвести два Pull Request job из
`.github/workflows/ci.yml`, измерить Python coverage, расширять существующие
проверки и разбирать сбои. Он также фиксирует подтверждённые имена checks для
будущей настройки защиты ветки `main`.

Документ не определяет Product requirements. Все значения с именами `TEST_*`,
fixture JSON schema, локальный HTTP route, HTTP status, временные файлы и
размер burst являются только test configuration. Coverage baseline также не
является обязательным порогом.

## Версии и предварительные условия

Проверенный локальный набор использует:

- Python `3.11`;
- Node.js `22.23.2` для полного совпадения с integration job;
- `package.json`, `package-lock.json` и exact `supabase@2.118.0`;
- Docker-compatible runtime только для локального Supabase;
- loopback TCP socket для двух HTTP/storage integration tests.

Физическое TLM-устройство, GitHub secrets, remote Supabase project, hosted
PostgreSQL и production services не нужны.

Создание и установка Python environment:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
.venv/bin/python -m pip check
```

Команда установки собирает и устанавливает wheel. Тесты используют
установленный package из `site-packages`, а не импортируют `src/` напрямую.

Установка local Supabase toolchain:

```bash
npm ci
npm ls --depth=0
npx --no-install supabase --version
```

Последняя команда должна вывести ровно `2.118.0`. `--no-install` запрещает
`npx` незаметно скачать другую версию.

## Job `CI / Python 3.11`

### Обычный локальный запуск

```bash
.venv/bin/python -m pip check
.venv/bin/python -m pytest
```

Полный suite включает package boundary, deterministic simulator, test-only
telemetry contract, offline/reconnect/ordering scenarios и настоящий loopback
HTTP/storage flow. Поэтому среда должна разрешать bind на `127.0.0.1` и
автоматически выбранный свободный порт.

### Воспроизведение result files

Из корня repository в Bash:

```bash
mkdir -p test-results
set +e
.venv/bin/python -m pytest --junitxml=test-results/pytest.xml 2>&1 \
  | tee test-results/pytest.log
pytest_exit_code=${PIPESTATUS[0]}
set -e
test -s test-results/pytest.xml
test -s test-results/pytest.log
exit "$pytest_exit_code"
```

`PIPESTATUS[0]` сохраняет status именно pytest; успешный `tee` не может скрыть
падение теста. В GitHub эти файлы публикуются как artifact
`pytest-results-python-3.11`:

```text
pytest.xml
pytest.log
```

`pytest.xml` предназначен для машинного разбора, `pytest.log` — для быстрой
человеческой диагностики. Срок хранения GitHub artifact берётся из repository
default и не является Product retention policy.

## Измерение Python coverage

`coverage==7.16.1` закреплён и в test extra `pyproject.toml`, и в
`requirements/test.txt`. Конфигурация в `pyproject.toml` измеряет statements и
branches для всего import package `tlm_device_data_platform` и показывает
пропущенные строки. `fail_under` намеренно отсутствует.

Воспроизводимый запуск:

```bash
.venv/bin/python -m coverage erase
.venv/bin/python -m coverage run -m pytest
.venv/bin/python -m coverage report
```

Baseline Step 11, измеренный 2026-10-01 на Python `3.11.9` полным suite из
`22` tests:

| Module | Statements | Missed | Branches | Partial | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| `local_integration.py` | 79 | 14 | 20 | 10 | 76% |
| `simulation.py` | 87 | 1 | 14 | 1 | 98% |
| `telemetry_fixture.py` | 87 | 7 | 22 | 4 | 90% |
| **TOTAL** | **253** | **22** | **56** | **15** | **88%** |

Файл `.coverage` является generated local state и исключён через `.gitignore`.
Число `88%` — измеренная точка отсчёта, а не требование. Порог не предложен и
не включён: сначала нужны согласованные quality policy и понимание, какие
error paths действительно должны стать required tests. Повышать coverage
следует содержательными сценариями, а не исключением неудобных строк.

## Детерминированный simulator и test fixtures

`src/tlm_device_data_platform/simulation.py` отделяет четыре внешние границы:

- `Sensor` возвращает reading без Product schema;
- `Clock` позволяет тесту полностью контролировать время;
- `Transport` передаёт opaque `bytes` и возвращает configured test outcome;
- `DurableQueue` хранит opaque `bytes` в FIFO order.

Управляемые реализации находятся в том же module:

- `SequenceSensor` выдаёт конечную последовательность;
- `ManualClock` меняется только после явного `advance()`;
- `ScriptedTransport` записывает attempts и выдаёт заданные результаты;
- `TemporaryFileQueue` доказывает FIFO persistence между Python instances;
- `flush_test_queue()` выполняет один явный deterministic flush и не является
  production retry worker.

`src/tlm_device_data_platform/telemetry_fixture.py` содержит только test-only
JSON contract. Его fields, schema version `1`, `message_id`, `stream_id`,
`sequence_no`, timestamps и payload не являются production telemetry schema.
`TelemetryFixtureProjection` моделирует history/current state только внутри
явно активированного test stream; device `recorded_at` не получает authority.

При расширении simulator tests:

1. называйте временные значения `TEST_*` или явно пишите `fixture`;
2. не добавляйте wall-clock sleeps, random input или физическое hardware;
3. держите transport и queue на opaque `bytes`;
4. добавляйте Product semantics только после подтверждённого решения;
5. для нового source module переустановите wheel перед pytest;
6. проверяйте scenario несколько раз, если он затрагивает filesystem,
   ordering, threads или sockets.

Текущая маршрутизация test responsibilities:

- `tests/test_simulation.py` — отдельные deterministic boundaries;
- `tests/test_telemetry_fixture.py` — serialization, parsing и controlled
  rejection test fixture contract;
- `tests/test_delivery_scenarios.py` — duplicate fixture acceptance,
  unavailable transport, reconnect и FIFO burst;
- `tests/test_ordering_scenarios.py` — out-of-order, stream restart, late data
  и clock skew;
- `tests/test_local_integration.py` — real loopback HTTP и filesystem storage;
- `tests/test_package.py` — installed-package boundary.

## Локальный HTTP и storage flow

`src/tlm_device_data_platform/local_integration.py` определяет локальную
границу. `OpaqueTelemetryAPI` принимает exact request body и передаёт его через
`StorageAdapter.store(message: bytes)`. API не импортирует fixture parser и не
знает Supabase schema. `TemporaryDirectoryStorage` пишет opaque messages в
временный каталог и открывается повторно для проверки настоящего filesystem
I/O.

Integration test поднимает standard-library WSGI server на `127.0.0.1:0`:

```text
TemporaryFileQueue
  -> test Transport
  -> real loopback HTTP POST
  -> OpaqueTelemetryAPI
  -> StorageAdapter
  -> TemporaryDirectoryStorage
  -> exact byte comparison after reopening storage
```

Если оба tests из `tests/test_local_integration.py` падают на
`PermissionError` при `socket.socket()`, сначала проверьте ограничения sandbox
или container profile. Это отличается от application failure: ошибка возникает
до bind и до вызова WSGI application. Не заменяйте real HTTP boundary mock-вызовом
только ради обхода такого ограничения.

Route `/test-fixture-telemetry`, response `204`, two-second client timeout и
file naming — test configuration. Они не определяют production API,
acknowledgement, authentication, durability или concurrency.

## Job `CI / Local Supabase integration`

### Database source of truth

- `supabase/config.toml` задаёт local test configuration и PostgreSQL major
  version `17`;
- `supabase/migrations/20260930233000_create_ingest_messages.sql` является
  текущим version-controlled schema source of truth;
- `supabase/tests/ingest_messages.test.sql` содержит transactional pgTAP test;
- seed выключен;
- remote link и generated `supabase/.temp/` не являются source.

Текущая migration создаёт только подтверждённый opaque ingress
`public.ingest_messages(id bigint identity primary key, body bytea not null)`.
RLS включён без policies; `anon` и `authenticated` не имеют доступа;
`service_role` имеет только необходимые для insert privileges. Это не разрешает
выводить будущую telemetry schema из test fixture JSON.

### Воспроизведение infrastructure flow

Сначала выполните Python и npm installation commands из раздела
«Версии и предварительные условия». Затем:

```bash
set -e
cleanup_local_supabase() {
  npx --no-install supabase stop --no-backup
}
trap cleanup_local_supabase EXIT

npx --no-install supabase start >/dev/null
npx --no-install supabase db reset --local
mkdir -p test-results/local-integration

set +e
npx --no-install supabase test db 2>&1 \
  | tee test-results/local-integration/database-tests.log
database_exit_code=${PIPESTATUS[0]}
set -e
test -s test-results/local-integration/database-tests.log
test "$database_exit_code" -eq 0

set +e
.venv/bin/python -m pytest \
  --junitxml=test-results/local-integration/pytest.xml 2>&1 \
  | tee test-results/local-integration/pytest.log
pytest_exit_code=${PIPESTATUS[0]}
set -e
test -s test-results/local-integration/pytest.xml
test -s test-results/local-integration/pytest.log
test "$pytest_exit_code" -eq 0

cleanup_local_supabase
trap - EXIT
```

`trap` гарантирует cleanup, если start, reset, pgTAP, pytest или проверка
result files завершится ошибкой. Если stack был запущен вручную без этого
блока, выполните cleanup отдельно:

```bash
npx --no-install supabase stop --no-backup
```

GitHub workflow гарантирует это отдельным step с `if: always()` до проверки и
upload результатов. Его artifact `local-integration-results` содержит ровно:

```text
database-tests.log
pytest.xml
pytest.log
```

Startup stdout подавлен, чтобы generated local URLs и keys не попадали в logs
или artifacts. Не публикуйте вывод local status/start, если он содержит такие
test credentials.

### Как расширять migration и pgTAP

1. Получите подтверждённое schema/authorization требование.
2. Создайте новую ordered migration; не переписывайте уже применённую history.
3. Не используйте `db push`, linked reset или production project для required
   CI.
4. Обновите pgTAP plan и добавьте assertions только для подтверждённого
   contract.
5. Выполните clean `db reset --local`, затем `supabase test db`.
6. Повторите reset/test, если изменение зависит от object creation order или
   migration history.
7. Запустите полный Python suite отдельно: database tests и provider-independent
   application tests доказывают разные границы.

## Диагностика CI failures

### Installation и dependency graph

- Failure `Install test environment`: повторите locked pip install, затем
  `pip check`. Не переходите на editable install и не добавляйте `PYTHONPATH`.
- Failure `Install local Supabase toolchain`: выполните clean `npm ci`, затем
  `npm ls --depth=0`.
- Failure `Verify Supabase CLI version`: ожидается exact `2.118.0`; не
  разрешайте `npx` автоматически скачать latest.

### Python tests

- Сначала откройте `pytest.log` для traceback и final summary.
- Затем проверьте `pytest.xml`: totals должны соответствовать тому же run.
- Если artifact отсутствует, смотрите `Validate test result files` и
  `Upload test results`; это отдельный failure artifact contract, а не
  доказательство падения pytest.
- Если collection не видит новый module/class, переустановите wheel locked
  command; это нормальное следствие `src/` layout.

### Local Supabase

- Failure `Start local Supabase`: проверьте Docker-compatible runtime и затем
  обязательно выполните `supabase stop --no-backup`.
- Failure `Rebuild local database`: проверяйте ordered migrations и local
  config; не заменяйте команду remote reset или push.
- Failure `Run database tests`: откройте `database-tests.log`, найдите номер
  failed pgTAP assertion и сопоставьте его с SQL test.
- Failure Python flow при зелёном pgTAP означает application/test boundary,
  а не автоматически database schema defect.
- Failure cleanup рассматривайте отдельно и не оставляйте local stack или
  volumes как предполагаемое состояние следующего запуска.

### Секреты и remote state

Required CI не должен получать project reference, access token, database
password, service-role key, hosted URL или remote connection string. Если
такое значение появилось в log/artifact, остановите публикацию и удалите
credential из workflow; локальные generated keys также не нужно сохранять.

## Открытые Product decisions

Текущие tests не принимают решений о:

- production telemetry envelope, fields, versions и rates;
- device provisioning, credentials и identity;
- participant/group/session roles и authorization;
- production API route, acknowledgement, retry и reconnect policy;
- offline retention, queue capacity, overflow и data-loss guarantees;
- production idempotency, ordering, reboot, late-data и timestamp trust;
- database tables beyond opaque ingress, read paths и RLS policies;
- retention, archive, partitioning, fleet scale, SLO и cost;
- remote commands и AI authority.

Появление подтверждённого решения требует отдельного source/migration/test
change. Нельзя молча повышать test fixture до Product contract.

## Подтверждённые checks и будущая branch protection

На commits `08b10d5eb0c450251fe23e3618a6d93ac7ac4aaa` (run #21) и
`5c11432939c3efe17f8189d09e64042e03d60822` (run #22) два GitHub Actions jobs
повторились с одинаковыми именами и conclusion `success`:

- check context `Python 3.11`, отображаемый в PR как
  `CI / Python 3.11`;
- check context `Local Supabase integration`, отображаемый в PR как
  `CI / Local Supabase integration`.

Оба check runs созданы GitHub Actions App с `app_id = 15368`. Third-party
`Sourcery review` не входит в required CI этого repository и не предлагается
как required check.

Read-only проверка 2026-10-01 показала: ветка `main` не защищена, repository
rulesets отсутствуют. Никакие settings не изменялись.

Минимальный предмет отдельного будущего approval — требовать перед merge оба
контекста выше и, где интерфейс позволяет, ограничить provider приложением
GitHub Actions `15368`. До применения пользователь должен отдельно решить:

- требуется ли branch быть up to date (`strict`);
- нужны ли approvals и сколько;
- применять ли правила к administrators;
- требовать ли conversation resolution, signed commits или linear history;
- разрешать ли force push, deletion и bypass.

Step 11 не выбирает эти repository governance settings, не включает branch
protection и не выполняет merge Pull Request.

## Проверенные внешние references

- Coverage.py branch measurement:
  <https://coverage.readthedocs.io/en/7.16.1/branch.html>;
- Coverage.py `7.16.1` release:
  <https://pypi.org/project/coverage/7.16.1/>;
- GitHub protected branches и required checks:
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>;
- GitHub REST branch-protection fields `strict`, `contexts`, `checks` и
  `app_id`:
  <https://docs.github.com/en/rest/branches/branch-protection>.
