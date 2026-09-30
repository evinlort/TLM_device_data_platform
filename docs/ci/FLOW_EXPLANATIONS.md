# Подробные объяснения CI-шагов

## Назначение документа

Этот файл объясняет не только результат каждого CI-шага, но и полный ход
рассуждений и выполнения: зачем шаг понадобился, от какого состояния мы
отталкивались, какие файлы и механизмы появились, как данные и команды проходят
через систему, какие сложности возникли, как они были устранены и что именно
доказывают проверки.

Это дополнение к компактным координационным файлам:

- `CI_PLAN.md` отвечает на вопрос «каков общий план и статус этапов?»;
- `CI_STATE.md` отвечает на вопрос «какое состояние сейчас проверено?»;
- `NEXT_SESSION.md` отвечает на вопрос «что делать в следующей сессии?»;
- `DECISIONS.md` хранит долговечные решения;
- этот файл отвечает на вопрос «почему всё устроено именно так и как оно
  работает целиком?».

Документ ведётся последовательно. После каждого завершённого и проверенного
шага, до запроса разрешения на commit, в конец добавляется новый раздел. Старые
разделы не переписываются без необходимости исправить подтверждённую
фактическую ошибку.

---

## Step 1 — Базовая Python-валидация

### Короткий итог

На Step 1 пустой репозиторий был превращён в минимальный, но реально
устанавливаемый Python-проект. Появились воспроизводимая сборка, закреплённое
тестовое окружение и первый тест, который проверяет важную границу: пакет
действительно устанавливается и импортируется как установленный пакет, а не
случайно находится прямо в рабочем каталоге.

Основной commit шага: `c780555` (`test: establish Python validation baseline`).

### Почему этот шаг был нужен

До Step 1 в репозитории не было Python-пакета, зависимостей, тестовой
конфигурации или команды, которую можно было бы честно назвать обязательной
проверкой. В такой ситуации сразу добавлять GitHub Actions было рано: workflow
не имел бы устойчивого локального контракта и мог бы запускать произвольный
набор команд, который невозможно одинаково воспроизвести на машине разработчика
и на GitHub runner.

Поэтому сначала требовалось ответить на четыре вопроса:

1. Какая версия Python является минимальной базой?
2. Как проект собирается и устанавливается?
3. Как фиксируется тестовое окружение?
4. Какая самая маленькая проверка уже имеет технический смысл, не выдумывая
   ещё не определённое продуктовое поведение TLM?

Step 1 создал именно этот локальный контракт. Step 2 затем смог перенести его в
GitHub Actions без изменения смысла проверок.

### Исходное состояние

В начале шага отсутствовали:

- `pyproject.toml`;
- import package;
- `requirements/test.txt`;
- pytest-конфигурация;
- каталог `tests/`;
- установочный или тестовый процесс;
- продуктовые модели, API, симулятор и база данных.

Физического устройства также не было. Продуктовые решения о telemetry,
credentials, roles, retention и command authority оставались открытыми. Поэтому
тестировать продуктовые сообщения или поведение устройства на этом шаге было
бы выдумыванием требований.

### Принятый подход

Была выбрана Python 3.11 как минимальная версия начальной базы. Это не означает,
что проект навсегда ограничен только этой версией. Решение фиксирует минимальную
проверенную точку, от которой можно расширять матрицу в будущем отдельным
осознанным изменением.

Проект получил стандартную структуру `src/`:

```text
pyproject.toml
requirements/test.txt
src/
  tlm_device_data_platform/
    __init__.py
tests/
  test_package.py
```

Ключевой смысл `src/` layout состоит в том, что Python не должен находить
пакет просто потому, что текущий каталог совпал с корнем репозитория. Тесты
должны работать с установленным distribution, то есть с тем же типом артефакта,
который будет использоваться вне исходного дерева.

### Что было добавлено

#### `pyproject.toml`

Файл определяет сборку и минимальные метаданные проекта:

- `setuptools==84.0.0` закреплён как build backend dependency;
- `setuptools.build_meta` используется как стандартный PEP 517 backend;
- distribution называется `tlm-device-data-platform`;
- import package называется `tlm_device_data_platform`;
- `requires-python = ">=3.11"` фиксирует минимальную версию;
- runtime dependencies пока пусты, потому что приложение ещё не реализовано;
- test extra содержит `pytest==9.1.1`;
- поиск пакетов направлен в `src`;
- pytest запускается в strict mode, использует `tests/` и
  `--import-mode=importlib`.

Версия `0.0.0` — технический bootstrap placeholder. Это не продуктовая версия
и не решение о будущей release/versioning policy.

#### `requirements/test.txt`

Файл закрепляет разрешённое Python 3.11 test environment:

- `pytest==9.1.1`;
- `iniconfig==2.3.0`;
- `packaging==26.3`;
- `pluggy==1.6.0`;
- `pygments==2.21.0`.

Команда установки передаёт этот файл как constraint:

```bash
python -m pip install --constraint requirements/test.txt '.[test]'
```

`.[test]` сообщает pip, что нужно установить сам локальный проект и его test
extra. Constraint-файл не является отдельным списком произвольных пакетов: он
ограничивает версии прямых и транзитивных test dependencies. Благодаря этому
локальная машина и чистый runner получают один и тот же проверенный набор
версий.

#### `src/tlm_device_data_platform/__init__.py`

Это минимальная граница import package. В ней ещё нет продуктовой логики. Её
задача — сделать distribution реально собираемым и дать тестам стабильную
точку импорта.

#### `tests/test_package.py`

Первый тест выполняет:

```python
import tlm_device_data_platform
```

и проверяет имя импортированного модуля. Ценность теста не в проверке одной
строки. Он доказывает всю цепочку:

- build backend увидел package в `src/`;
- wheel был собран;
- wheel был установлен;
- Python может разрешить import установленного package;
- pytest работает с установленным package boundary.

Продуктового поведения ещё нет, поэтому такой тест является минимальной
содержательной проверкой без выдумывания telemetry contract.

#### `.gitignore`

Исключены локальные и генерируемые артефакты:

- `.venv/`;
- `__pycache__/`;
- `.pytest_cache/`;
- `*.egg-info/`;
- `build/`;
- `dist/`.

Это предотвращает попадание локального окружения и результатов сборки в Git.

### Полный поток Step 1

```text
developer or CI
  -> creates an isolated Python 3.11 virtual environment
  -> pip reads pyproject.toml
  -> pip installs the pinned build backend
  -> build backend finds tlm_device_data_platform under src/
  -> pip builds a wheel
  -> pip installs the wheel plus the test extra
  -> requirements/test.txt constrains test dependency versions
  -> pip check validates installed dependency metadata
  -> pytest loads tests in importlib mode
  -> test imports tlm_device_data_platform from site-packages
  -> successful result proves the install/test boundary
```

Канонические команды:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest
```

### Как это решает задачу

До шага фраза «тесты проходят» не имела общего технического значения: не было
ни установочной модели, ни закреплённых зависимостей, ни обязательной команды.
После шага она означает конкретный воспроизводимый процесс.

Отдельные части закрывают разные риски:

- `pyproject.toml` устраняет неопределённость сборки;
- pinned build backend устраняет незаметное изменение инструмента сборки;
- `requirements/test.txt` устраняет плавающие версии test dependencies;
- `src/` layout уменьшает риск ложноположительного импорта из repository root;
- установка `.[test]` проверяет настоящий distribution;
- `pip check` обнаруживает несовместимое установленное dependency graph;
- pytest strict/importlib configuration делает ошибки конфигурации и импорта
  более явными;
- тест не зависит от устройства, сети, Supabase, secrets или времени.

### Что происходило во время реализации и как были устранены риски

#### Репозиторий был практически пустым

Нельзя было опереться на существующий framework, package manager или test
convention. Вместо преждевременного создания архитектуры приложения был выбран
наименьший стандартный Python foundation.

#### Не было подтверждённого продуктового поведения для тестирования

Вместо выдуманного telemetry payload или device behavior был проверен
установочный boundary. Это технически значимая проверка и одновременно не
создаёт ложных продуктовых требований.

#### Обычный import из repository root мог дать ложный успех

Если package лежит непосредственно в корне или Python добавляет исходный
каталог в import path, тест может пройти даже при сломанной упаковке. Риск был
снят сочетанием `src/` layout, установки wheel и дополнительной проверки из
каталога вне repository root. Фактический путь модуля указывал на
`site-packages`.

#### Нужно было различать project dependency declaration и locked test set

`pyproject.toml` объявляет, что проекту для тестирования нужен pytest.
`requirements/test.txt` закрепляет проверенные версии всего разрешённого test
environment. Установка использует оба источника одновременно через
`.[test]` и `--constraint`.

#### Нельзя было незаметно добавить лишние quality gates

Lint, formatter, type checker и coverage threshold не были добавлены, потому
что для них ещё не было подтверждённого project convention или измеренной
базы. Их отсутствие — сознательное ограничение scope, а не забытая работа.

### Проверка и что она доказывает

Проверка выполнялась в новом изолированном окружении на Python 3.11.9:

- wheel успешно собран и установлен;
- `pip check` сообщил `No broken requirements found`;
- pytest сообщил `1 passed`;
- импорт из каталога вне репозитория разрешился в `site-packages`;
- `git diff --check` не обнаружил whitespace errors.

После загрузки dependencies обязательные проверки не требовали сети, Docker,
Supabase, secrets или физического устройства.

### Что сознательно осталось вне Step 1

Step 1 не определял:

- telemetry fields или message envelope;
- device simulator;
- API;
- database schema;
- credentials или authorization;
- retry, duplicate, offline или ordering semantics;
- lint, type checking или coverage policy;
- GitHub Actions workflow.

Последний пункт стал задачей Step 2.

---

## Step 2 — Базовый Pull Request workflow в GitHub Actions

### Короткий итог

Step 2 перенёс локальный контракт Step 1 в один минимальный Pull Request
workflow. Теперь каждый PR может на чистом GitHub-hosted runner повторить
установку package, `pip check` и pytest без физического оборудования,
production Supabase или secrets.

Основные commits:

- `7238050` — workflow и подготовительный handoff;
- `95ba5de` — финальный handoff после успешного удалённого запуска.

Pull Request:
[#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1).

### Почему этот шаг был нужен

Локальные команды Step 1 доказывали, что baseline работает на одной машине.
Однако Pull Request можно безопасно оценивать только тогда, когда те же
обязательные проверки автоматически запускаются в чистой среде для изменений,
которые предполагается объединить.

Целью не было создать «большую CI-платформу». Требовалось добавить ровно один
надёжный job, который повторяет уже проверенный локальный контракт. Такой
порядок предотвращает расхождение: локально запускается один набор команд, а CI
проверяет другой.

### Исходное состояние

В начале Step 2 уже существовали:

- устанавливаемый Python 3.11 project;
- pinned test environment;
- канонические install/check/test commands;
- один deterministic package-boundary test.

Но в `.github/workflows/` не было workflow. Pull Request не имел
автоматической обязательной Python-проверки.

### Что было добавлено

Файл `.github/workflows/ci.yml` содержит один workflow `CI` и один job
`Python 3.11`.

#### Trigger

```yaml
on:
  pull_request:
```

Workflow реагирует на безопасный `pull_request` context. Не используется
`pull_request_target`, потому что тот выполняется в контексте base repository
и требует особенно осторожного обращения с недоверенным PR code, permissions и
secrets. Для сборки и тестирования кода PR нужен обычный `pull_request`.

Дополнительные deployment, schedule или production triggers не добавлялись.

#### Минимальные permissions

```yaml
permissions:
  contents: read
```

Workflow получает только чтение contents. Ему не нужны права на изменение
веток, PR, issues, packages, deployments или repository settings.

#### Отмена устаревших запусков

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

Все запуски одного workflow для одного PR попадают в одну concurrency group.
Если в PR быстро отправлено несколько commits, старый незавершённый запуск
отменяется, а проверяется новый HEAD. Разные PR при этом не блокируют друг
друга.

#### Ограничение времени

```yaml
timeout-minutes: 10
```

Если install или test зависнет, job не будет занимать runner шесть часов по
умолчанию. Десять минут — защитный CI timeout для текущего маленького набора
проверок, а не продуктовый SLO.

#### Закреплённые Actions

Используются полные commit SHA:

- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`
  с комментарием `v7.0.1`;
- `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97`
  с комментарием `v7.0.0`.

Release tags были разрешены напрямую против официальных upstream Git
repositories. Workflow хранит полный SHA, потому что SHA неизменяем, а tag
может быть перемещён. Комментарий с release version сохраняет читаемость для
человека.

Для checkout дополнительно задано:

```yaml
persist-credentials: false
```

После checkout token не остаётся настроенным для последующих Git-команд. Job
только читает и тестирует код, поэтому push credentials ему не нужны.

#### Повторение локального контракта

Job выполняет те же команды, которые были установлены на Step 1:

```bash
python -m pip install --constraint requirements/test.txt '.[test]'
python -m pip check
python -m pytest
```

В CI используется `python`, потому что `actions/setup-python` уже добавляет
выбранный Python 3.11 в `PATH`.

### Полный поток Step 2

```text
developer pushes a commit to the Pull Request
  -> GitHub emits pull_request opened/synchronize/reopened
  -> GitHub loads .github/workflows/ci.yml from the PR merge context
  -> concurrency identifies this workflow and PR number
  -> an older in-progress run for the same PR is cancelled if necessary
  -> GitHub starts a clean ubuntu-latest runner
  -> the 10-minute job timeout starts
  -> checkout reads the repository at a full-SHA-pinned action version
  -> checkout does not persist write credentials
  -> setup-python installs/selects Python 3.11 using a full-SHA-pinned action
  -> pip builds and installs the project with the locked test constraints
  -> pip check validates installed dependencies
  -> pytest runs the installed-package test
  -> GitHub publishes CI / Python 3.11 as the PR check result
```

### Как Step 2 решает задачу

Step 1 определил локальный source of truth. Step 2 не создал параллельную
систему, а автоматизировал тот же поток на чистом runner.

Это даёт следующие свойства:

- воспроизводимость: CI начинает с чистой среды;
- одинаковый смысл локальной и удалённой проверки;
- раннее обнаружение сломанной упаковки или dependencies;
- отсутствие зависимости от локально установленных глобальных пакетов;
- least privilege для `GITHUB_TOKEN`;
- supply-chain защита через full-SHA action pins;
- ограниченное время выполнения;
- экономия runner time через cancellation;
- отсутствие production credentials и внешних production systems.

### Что происходило во время реализации

#### Проверка актуальных release versions и SHA

Перед написанием workflow были проверены официальные GitHub Actions guidance и
release pages. Mutable tags не переносились в итоговый `uses:`. Команды
`git ls-remote` против официальных repositories подтвердили полные SHA
release tags.

#### Локальная проверка workflow

До отправки workflow были выполнены:

- чистая установка в новом `.venv`;
- `pip check`;
- pytest;
- проверка import path из каталога вне repository root;
- YAML parsing;
- явные assertions для trigger, `contents: read`, concurrency cancellation,
  timeout, двух full-SHA pins и обязательных команд;
- проверка отсутствия `pull_request_target` и secret references;
- `git diff --check`.

Это отделило ошибки самого YAML/контракта от возможных проблем удалённого
GitHub запуска.

#### Локальный `gh` не запустился

Установленный GitHub CLI был поставлен через Snap и отказался запускаться из-за
локальной ошибки Snap/AppArmor. Это не было ошибкой repository или workflow.

Проблема была обойдена без изменения project scope: commit и push выполнялись
обычным Git, а Pull Request и чтение GitHub Actions state — через подключённый
GitHub API. Таким образом, не понадобилось менять workflow или просить
пользователя вручную создавать PR.

#### Первый запрос Actions API ещё не видел run

Сразу после открытия PR API кратковременно возвращал пустой список workflow
runs. Вместо вывода о поломке были проверены несколько независимых фактов:

- Pull Request существует и mergeable;
- repository Actions включены;
- разрешены GitHub Actions;
- локальный merge tree не содержит конфликтов;
- у commit появился GitHub Actions check suite.

Причиной оказалась задержка регистрации запуска, а не ошибка workflow. После
короткого ожидания run появился и завершился успешно.

#### Проверены implementation и final-handoff commits

Первый фактический запуск:

- workflow: `CI`;
- run ID: `36674668467`;
- run number: `1`;
- commit: `72380506cbae287db8858a55e041fd4186054f1a`;
- job: `Python 3.11`;
- conclusion: `success`.

После обновления финального handoff был отправлен commit
`95ba5dec3d8d53a941e1917f888980cf2793322a`. Он вызвал второй PR run:

- run ID: `36675487866`;
- run number: `2`;
- job: `Python 3.11`;
- conclusion: `success`.

Во втором запуске успешно завершились checkout, Python setup, locked
installation, dependency consistency check и pytest. Поэтому зелёным оказался
не только implementation commit, но и фактический финальный HEAD Step 2.

### Проверка и что она доказывает

Локальная проверка доказала:

- workflow синтаксически читаем;
- его security/semantics соответствуют плану;
- Step 1 commands по-прежнему проходят;
- package импортируется из установленного `site-packages`;
- нет whitespace errors.

Удалённая проверка доказала:

- GitHub принимает workflow;
- `pull_request` trigger действительно создаёт run;
- выбранные full-SHA Actions исполняются на GitHub-hosted runner;
- Python 3.11 доступен;
- clean runner собирает и устанавливает project;
- locked dependencies согласованы;
- pytest проходит;
- результат публикуется как `CI / Python 3.11`.

### Что сознательно осталось вне Step 2

Не добавлялись:

- simulator tests;
- API или database integration;
- Supabase/PostgreSQL/Docker;
- dependency caching;
- test matrix или splitting;
- coverage threshold;
- lint или type checking;
- secrets;
- deployment;
- branch protection или required-status-check settings;
- автоматическое merge PR.

Pull Request #1 оставлен открытым и mergeable. Решение о merge не входило в
разрешение на Step 2.

### Связь Step 1 и Step 2

Step 1 отвечает за содержание проверки:

```text
buildable package + locked environment + pip check + pytest
```

Step 2 отвечает за автоматический запуск этого содержания:

```text
pull_request event + isolated runner + least privilege + pinned actions
```

Вместе они образуют первую полноценную CI-цепочку проекта:

```text
source change
  -> Pull Request
  -> clean Python 3.11 environment
  -> reproducible package installation
  -> dependency validation
  -> deterministic test
  -> visible PR check
```

Следующий Step 3 может добавлять deterministic simulator boundaries уже поверх
работающей цепочки. Новые unit tests автоматически попадут в существующий
`python -m pytest` и будут проверяться тем же PR workflow.

---

## Step 3 — Детерминированные границы симулятора

### Короткий итог

Step 3 добавил четыре минимальные provider-independent границы: `Sensor`,
`Clock`, `Transport` и `DurableQueue`. Для них появились управляемые тестами
реализации `SequenceSensor`, `ManualClock`, `ScriptedTransport` и
`TemporaryFileQueue`. Четыре новых unit tests доказывают повторяемость readings,
времени, результатов delivery и FIFO-состояния временной файловой очереди.

Шаг не определяет telemetry envelope и не моделирует retry, reconnect или
replay. На этой стадии сообщение остаётся непрозрачным `bytes`, а reading —
generic Python-значением. Благодаря этому CI получает необходимые точки
подмены, не превращая временные fixture-значения в продуктовые требования.

### Почему этот шаг был нужен

После Step 2 проект уже умел воспроизводимо устанавливаться и автоматически
запускать pytest в Pull Request. Однако единственный тест проверял только
package boundary. Для будущих device scenarios нельзя обращаться напрямую к
реальному датчику, системным часам, сети или production storage: такие тесты
были бы недетерминированными и не могли бы надёжно выполняться на чистом
GitHub-hosted runner.

При этом сразу создавать полноценный device simulator также было рано.
Product Management ещё не подтвердил поля telemetry, sampling rate, transport,
credentials, buffer capacity, retention, retry или authorization semantics.
Поэтому Step 3 отделяет изменчивые внешние зависимости от будущей логики, но не
решает за продукт, какие данные и политики должны существовать.

### Исходное состояние

В начале шага существовали:

- устанавливаемый Python 3.11 package;
- pinned pytest environment;
- один installed-package test;
- Pull Request workflow `CI / Python 3.11` с успешным запуском;
- решения о hardware-independent CI и provider-independent device boundary.

Не существовали sensor, clock, transport, queue или simulator abstractions.
Физического устройства, API, базы данных, Docker и Supabase для обязательных
проверок не требовалось и не было.

Перед изменениями реальное состояние было сверено с handoff: ветка
`ci/github-actions-foundation`, HEAD `67ddea7`, чистое рабочее дерево, `origin`,
открытый mergeable PR #1 и успешный `CI / Python 3.11` совпадали с
`CI_STATE.md`.

### Что было добавлено

#### Структурные границы

В `src/tlm_device_data_platform/simulation.py` определены четыре `Protocol`:

- `Sensor[ReadingT_co].read()` возвращает одно generic reading;
- `Clock.now()` возвращает контролируемый `datetime`;
- `Transport.send(message: bytes)` выполняет delivery attempt и возвращает
  только его результат `bool`;
- `DurableQueue` предоставляет `enqueue`, `peek`, `dequeue` и длину FIFO.

`Protocol` задаёт требуемую форму dependency без наследования от конкретного
provider class. Будущая production или integration реализация сможет
соответствовать границе структурно. `Sensor` не называет ни одного telemetry
field, а transport и queue видят только уже сериализованные bytes.

`bool` у `Transport` означает лишь test delivery outcome. Он не определяет HTTP
status mapping, acknowledgement protocol, retry policy или продуктовый смысл
успеха.

#### Управляемые test implementations

`SequenceSensor` получает `test_readings` и возвращает их строго по очереди.
После исчерпания fixture он выбрасывает `FixtureExhaustedError`, поэтому
случайный дополнительный read не маскируется повтором последнего значения.

`ManualClock` начинается с явно переданного `test_start`. Повторный `now()` не
двигает время. Изменение возможно только через `advance(test_delta)`, поэтому
тест не зависит от скорости runner или wall clock.

`ScriptedTransport` получает последовательность `test_results`. Каждый
`send()` записывает opaque message в `attempts` и возвращает следующий заранее
заданный результат. После исчерпания configuration также возникает
`FixtureExhaustedError`. Никакого network call реализация не делает.

`TemporaryFileQueue` сохраняет список сообщений в одном JSON-файле. Bytes
кодируются base64, поэтому queue не интерпретирует payload. При изменении новый
JSON сначала записывается во временный соседний файл, затем заменяет основной.
Новый экземпляр с тем же `test_path` загружает прежнее состояние, что позволяет
проверить минимальное значение слова durable для этого шага — состояние не
зависит от жизни одного Python object.

Это именно временная test implementation. Она не обещает production
crash-safety, multi-process locking, retention, capacity или performance.

#### Явные test fixtures

В `tests/test_simulation.py` значения названы `TEST_READING_FIXTURES`,
`TEST_START_TIME`, `TEST_TIME_ADVANCE`, `TEST_DELIVERY_RESULTS` и
`TEST_MESSAGES`. Значения вроде `2042-01-02`, семи секунд и строк
`test-message-a`/`test-message-b` существуют только для проверки механики. Они
не являются telemetry schema, reporting interval или product default.

### Полный поток Step 3

Sensor flow:

```text
test configures finite readings
  -> consumer calls Sensor.read()
  -> SequenceSensor returns the next configured value
  -> an unconfigured extra call fails explicitly
```

Clock flow:

```text
test supplies an exact datetime
  -> repeated Clock.now() calls return the same value
  -> test calls ManualClock.advance(delta)
  -> Clock.now() returns exactly start + delta
```

Transport flow:

```text
test configures failure then success
  -> send(opaque bytes) records the first attempt and returns False
  -> send(opaque bytes) records the second attempt and returns True
  -> no network or provider is contacted
```

Queue flow:

```text
first queue instance enqueues opaque messages into tmp_path
  -> file stores base64 representations in FIFO order
  -> second instance reads the same file and sees the oldest message
  -> peek leaves it in place
  -> dequeue persists its removal
  -> third instance sees only the remaining message
```

Эти потоки пока намеренно не соединены в end-to-end retry loop. Их задача —
доказать независимые границы, на которых следующие шаги смогут строить свои
сценарии без обращения к hardware или production services.

### Как это решает задачу

Каждый источник недетерминизма теперь имеет маленькую заменяемую точку:

- hardware reading заменяется конечной fixture sequence;
- wall clock заменяется manual clock;
- сеть заменяется scripted outcome sequence;
- долговечность между объектами проверяется во временной filesystem queue.

Результат одинаков на каждом запуске, потому что тест полностью задаёт входы и
не ждёт реального времени. Opaque payload одновременно сохраняет правильное
направление архитектуры: device boundary не знает Supabase URL, table names,
PostgREST, Edge Functions или service-role credentials.

### Что происходило во время реализации и как решались проблемы

#### Нужно было не опередить Step 4

Для sensor можно было сразу создать telemetry dataclass, а для transport —
JSON envelope. Это было бы удобнее для конкретного сценария, но незаметно
зафиксировало бы неподтверждённые поля и версии. Поэтому reading оставлен
generic, а message — opaque bytes. Envelope и validation остаются отдельной
задачей Step 4.

#### Queue могла навязать будущую retry-модель

Методы вроде `ack`, `retry`, `replay` или automatic reconnect не добавлялись.
Минимальный FIFO содержит только enqueue, non-destructive peek и dequeue. Это
достаточно для проверки границы хранения, но не утверждает, когда продукт
обязан удалять сообщение или повторять delivery.

#### Первая переустановка package не получила build dependency

Первый запуск locked install выполнялся в restricted sandbox. PEP 517 build
environment попытался получить закреплённый `setuptools==84.0.0`, но DNS/network
access был запрещён. Ошибка произошла до сборки project и не указывала на
дефект кода.

После явного разрешения сетевого доступа была повторена та же команда без
изменения dependencies или constraints. Wheel успешно собрался и установился.
Таким образом, проблема была устранена как ограничение среды, а не обходом
reproducibility contract.

### Проверка и что она доказывает

Использовался Python 3.11.9. Выполнены:

```bash
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

Результаты:

- locked wheel build и install: PASS;
- dependency consistency: PASS (`No broken requirements found`);
- полный suite пять раз подряд: PASS (`5 passed` в каждом запуске);
- import из `/tmp`: PASS, `simulation.py` загружен из установленного
  `site-packages`, а не из source tree;
- поиск запрещённых external dependencies: PASS;
- `git diff --check`: PASS до handoff edits и повторяется на финальном diff.

Четыре simulator tests отдельно доказывают:

- readings возвращаются в точной fixture-последовательности;
- время остаётся неподвижным без явного `advance`;
- transport возвращает точно заданные failure/success и сохраняет attempts;
- queue сохраняет FIFO-порядок и удаления между новыми instances.

Повтор пяти запусков важен не как статистическая гарантия, а как простая
проверка отсутствия зависимости от порядка, реального времени или случайности.
Проверка import path подтверждает, что новые module/tests проходят через тот же
installed-package boundary, который был установлен на Step 1.

### Что сознательно осталось вне Step 3

Не добавлялись:

- product telemetry envelope, поля или schema version;
- normal message contract scenarios Step 4;
- duplicate, idempotency, retry, reconnect, replay или buffered burst Step 5;
- out-of-order, stream restart, late-data или clock-skew semantics Step 6;
- API, HTTP, Storage Adapter, Supabase, PostgreSQL или Docker;
- credentials, roles, authorization или remote commands;
- retention guarantee, queue capacity или overflow policy;
- sampling/reporting rates;
- Hardware-in-the-Loop;
- новые dependencies, lint, type checking, caching или coverage threshold.

Следующий Step 4 может использовать opaque transport/queue boundary и добавить
явно test-only contract fixtures. Начинать его в этой сессии нельзя. Сначала
Step 3 должен получить одобренный commit/push и успешный Pull Request workflow.

### Удалённая проверка и завершение шага

После явного разрешения пользователя реализация и подготовленный handoff были
зафиксированы commit `ef46e3d` (`test: add deterministic simulator boundaries`)
и отправлены в `ci/github-actions-foundation`.

Push запустил GitHub Actions workflow `CI`, run ID `36699527689`, run number
`4`. Job `Python 3.11` завершился с conclusion `success`. На чистом
GitHub-hosted runner успешно прошли checkout, Python setup, locked installation,
`pip check` и полный pytest suite. Это подтверждает, что Step 3 работает не
только в сохранённом локальном `.venv`, но и в изолированной среде Pull Request
без hardware, secrets и production services.

После этого `CI_PLAN.md` и `CI_STATE.md` переведены из промежуточного
`READY_FOR_COMMIT` в окончательный `DONE`. Step 4 остаётся задачей новой сессии;
никакой его implementation в рамках Step 3 не выполнялся.

---

## Step 4 — Нормальная telemetry и contract-сценарии

### Короткий итог

Step 4 добавил минимальный versioned telemetry contract исключительно для CI
fixtures. Три нормальных сообщения с `sequence_no` 1, 2 и 3 детерминированно
сериализуются в JSON `bytes`, проходят через существующий
`ScriptedTransport`, затем разбираются обратно в исходные fixture envelopes.
Malformed input и неподдерживаемая fixture schema version отклоняются
контролируемыми и различимыми exception types.

Ни имя поля, ни его значение, ни fixture schema version `1` не считаются
подтверждённым продуктовым требованием. Модуль называется
`telemetry_fixture.py`, API использует слово `Fixture`, а module/class
docstrings прямо фиксируют временный test-only статус этого контракта.

### Почему этот шаг был нужен

Step 3 создал управляемые границы sensor, clock, transport и queue, но
намеренно оставил сообщения непрозрачными `bytes`. Этого было достаточно для
проверки независимых механизмов, однако нельзя было проверить нормальную
последовательность telemetry или контролируемую реакцию на неверный contract:
не существовало даже тестового формата, который можно принять или отклонить.

Одновременно product telemetry schema всё ещё не подтверждена. Если бы Step 4
назвал временный JSON production envelope, CI начал бы закреплять решения о
полях, версиях и правилах приёма без Product Manager. Поэтому задача решена
через отдельный fixture contract: он стабилен для тестов и достаточно строг,
чтобы доказывать contract behavior, но явно не претендует на продуктовый API.

### Исходное состояние

Перед изменениями были сверены локальное и удалённое состояния:

- ветка `ci/github-actions-foundation` и HEAD `959d08e`;
- чистое рабочее дерево;
- `origin` указывает на ожидаемый private GitHub repository;
- PR #1 открыт, mergeable и указывает на тот же HEAD;
- `CI / Python 3.11` для фактического remote HEAD завершён успешно;
- Step 3 implementation commit и его успешный run присутствуют в истории.

Более новый commit `959d08e` только добавлял в план будущий Step 4.5 для test
artifacts и не изменял завершённое состояние Step 3. Поэтому он не создавал
конфликта с activation condition Step 4.

До Step 4 transport принимал только opaque `bytes`, а проект не содержал
telemetry serializer, parser, schema version или contract errors. Поля
production telemetry, rates, credentials, authorization, retention и storage
semantics оставались открытыми решениями.

### Что было добавлено

#### Отдельный fixture module

`src/tlm_device_data_platform/telemetry_fixture.py` содержит fixture schema
version `1` и `TelemetryFixtureEnvelope` с полями:

- `schema_version`;
- `message_id`;
- `stream_id`;
- `sequence_no`;
- `recorded_at`;
- `payload`.

Этот список выбран только как test configuration, достаточная для текущего и
запланированных deterministic scenarios. Он не утверждает, что production
device обязан отправлять эти поля, использовать JSON или версию `1`.

`serialize_fixture_telemetry()` сначала проверяет exact fixture shape, затем
создаёт UTF-8 JSON `bytes`. `sort_keys=True` и compact separators дают один и
тот же byte sequence для одинакового envelope. `allow_nan=False` не позволяет
незаметно породить нестандартные JSON values `NaN` или `Infinity`.

`parse_fixture_telemetry()` принимает тот же opaque `bytes` boundary,
декодирует только UTF-8 JSON, требует object с точным набором fixture fields и
проверяет минимальные типы. Parser не интерпретирует timestamp, payload value
или product meaning полей.

#### Контролируемые ошибки

Ошибки разделены на две категории:

- `MalformedTelemetryFixtureError` означает, что input не является допустимым
  fixture envelope: это может быть неверный JSON, не-object, отсутствующий или
  лишний field либо неверный fixture field type;
- `UnsupportedFixtureSchemaVersionError` означает, что shape и тип version
  распознаны, но test fixture version не поддерживается.

Обе ошибки наследуют `TelemetryFixtureError`, поэтому consumer при
необходимости может обработать общий fixture failure. Раздельные subclasses
позволяют тесту доказать, что unsupported version не маскируется под случайную
ошибку JSON parser.

#### Normal ordered scenario

`tests/test_telemetry_fixture.py` объявляет значения через `TEST_*` constants
и создаёт три envelopes. Их `message_id`, `stream_id`, `recorded_at`, payload и
числовые readings — только test fixtures.

Тест сериализует envelopes, передаёт каждый message через уже существующий
`ScriptedTransport` с тремя заранее настроенными успешными результатами и
разбирает записанные `attempts`. Он проверяет одновременно:

- все три configured delivery attempts успешны;
- после round trip envelopes не изменились;
- наблюдаемый порядок `sequence_no` равен `(1, 2, 3)`.

`Transport.send(message: bytes) -> bool` не расширялся и не узнал ничего о
JSON. Таким образом, Step 4 использует Step 3 boundary, не связывая transport с
fixture или будущей production schema.

Дополнительные tests доказывают стабильность повторной сериализации,
round-trip parsing, controlled rejection неверного JSON, не-object input,
неполного envelope, неверного типа `sequence_no` и отдельно unsupported
fixture version.

### Полный поток Step 4

Normal flow:

```text
test creates three TelemetryFixtureEnvelope values
  -> serialize_fixture_telemetry validates fixture-only shape
  -> deterministic JSON encoder produces opaque bytes
  -> ScriptedTransport records bytes and returns configured True
  -> parse_fixture_telemetry validates recorded bytes
  -> test observes sequence_no 1, 2, 3 in original order
```

Malformed flow:

```text
test supplies invalid JSON, wrong top-level type, incomplete shape,
or invalid field type
  -> parse_fixture_telemetry rejects the fixture input
  -> MalformedTelemetryFixtureError identifies a controlled contract failure
```

Unsupported-version flow:

```text
test supplies an otherwise shaped fixture with schema_version 999
  -> parser recognizes the integer version
  -> version differs from fixture version 1
  -> UnsupportedFixtureSchemaVersionError reports the exact test version
```

Ни один поток не обращается к hardware, wall clock, network, API, database,
Supabase, Docker, secret или production service.

### Как это решает задачу

Теперь CI может отличить три принципиально разных результата: normal fixture
message принят parser, malformed fixture отклонён как malformed, а корректно
представленная, но неизвестная fixture version отклонена как unsupported.
Порядок 1, 2, 3 подтверждается на реальном serialized `bytes` boundary, а не
только на списке Python objects.

При этом архитектурная граница Step 3 сохранена. Contract logic находится
перед transport и после него, а сам transport остаётся provider-independent.
Такой composition позволяет позже строить новые deterministic scenarios, не
добавляя Supabase details в device boundary.

Явная fixture terminology решает второй риск: читатель и следующая Codex
сессия видят, что текущая схема существует ради CI. Для превращения любого её
элемента в production contract по-прежнему понадобится отдельное
подтверждённое продуктовое решение.

### Что происходило во время реализации и как решались проблемы

#### Первый pytest увидел прежний установленный wheel

Проект использует `src/` layout и pytest `importlib` mode, поэтому tests
импортируют установленный distribution. Сразу после создания нового module
`.venv` всё ещё содержал wheel Step 3. Collection остановился с
`ModuleNotFoundError` для `telemetry_fixture`.

Это было ожидаемым доказательством installed-package boundary, а не поводом
добавлять source tree в `PYTHONPATH`. Текущий project был переустановлен
канонической locked command, после чего import стал разрешаться из
`site-packages`.

#### Restricted sandbox не мог скачать build dependency

Первая locked reinstall попытка дошла до isolated PEP 517 build environment,
но sandbox не разрешал DNS/network access для получения закреплённого
`setuptools==84.0.0`. Команда была повторена после явного разрешения сетевого
доступа, без изменения dependency versions или installation flow. Wheel был
успешно собран и установлен.

#### Нужно было не превратить validation в product policy

Parser проверяет только техническую форму fixture: exact fields, базовые
типы, supported test version и стандартный finite-value JSON. Он намеренно не
проверяет business ranges, timestamp freshness, identity, authorization,
storage acceptance, duplicate policy или ordering across streams. Эти правила
не подтверждены либо относятся к будущим шагам.

### Проверка и что она доказывает

На Python 3.11.9 выполнены:

```bash
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

Результаты:

- locked wheel build и reinstall: PASS;
- dependency consistency: PASS (`No broken requirements found`);
- полный suite пять раз подряд: PASS (`12 passed` в каждом запуске);
- import из `/tmp`: PASS, `telemetry_fixture.py` загружен из установленного
  `site-packages`;
- controlled malformed/version errors: PASS через dedicated tests;
- forbidden external-dependency scan по `src` и `tests`: PASS;
- `git diff --check`: PASS до handoff update и повторяется для final diff.

Пять одинаковых прогонов подтверждают, что новые scenarios не зависят от test
order, wall clock или случайности. Installed import доказывает, что новый
module попал в собираемый distribution. Отдельные exception assertions
доказывают не просто факт отказа, а ожидаемый и контролируемый вид отказа.

### Что сознательно осталось вне Step 4

Step 4 не добавлял:

- production telemetry schema или подтверждение fixture fields;
- duplicate/idempotency behavior;
- unavailable transport, queue retention, retry, reconnect или replay;
- buffered burst;
- out-of-order current state, stream restart, late data или clock skew;
- API, HTTP, Storage Adapter, Supabase, PostgreSQL или Docker;
- credentials, identity, roles, authorization или remote commands;
- retention, capacity, overflow, sampling rate или reporting rate;
- JUnit/log artifacts, которые выделены в следующий Step 4.5;
- новые dependencies, caching, lint, type checking или coverage threshold;
- Hardware-in-the-Loop, deployment, branch protection или merge PR.

### Удалённая проверка и завершение шага

После явного разрешения пользователя реализация и подготовленный handoff были
зафиксированы commit `d0edec4` (`test: add telemetry fixture contract
scenarios`) и отправлены в `ci/github-actions-foundation`.

Push запустил GitHub Actions workflow `CI`, run ID `36705219771`, run number
`7`. Job `Python 3.11` завершился с conclusion `success`. На чистом
GitHub-hosted runner успешно прошли checkout, Python setup, locked
installation, `pip check` и полный pytest suite. Тем самым test-only contract,
ordered scenario и controlled rejection проверены не только в локальном
`.venv`, но и в изолированной Pull Request среде без hardware, secrets и
production services.

После успешного run `CI_PLAN.md` и `CI_STATE.md` переведены из
`READY_FOR_COMMIT` в `DONE`. Следующим шагом остаётся Step 4.5; никакая его
реализация в этой сессии не выполнялась.

---

## Step 4.5 — Публикация результатов тестов

### Короткий итог

Step 4.5 расширил единственный Pull Request job двумя сохраняемыми
представлениями результата pytest: machine-readable JUnit XML
`test-results/pytest.xml` и human-readable log
`test-results/pytest.log`. Оба файла загружаются в artifact
`pytest-results-python-3.11` даже после падения тестов. При этом код возврата
pytest не заменяется кодом `tee`, а отсутствие или пустота любого ожидаемого
файла превращается в явную ошибку workflow.

Для upload используется официальный `actions/upload-artifact@v7.0.1`,
закреплённый по полному upstream commit SHA
`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`. `retention-days` намеренно не
задан: применяется repository-default artifact retention, которая не имеет
отношения к ещё открытому продуктовому решению о сроке хранения telemetry.

### Почему этот шаг был нужен

До Step 4.5 результат `python -m pytest` был виден только в live/job log
GitHub Actions. Этого достаточно для простого ответа «job зелёный или
красный», но недостаточно для устойчивой диагностики и последующей
автоматической обработки:

- инструменты не получали стандартный JUnit XML с отдельными testcase;
- человеку приходилось искать pytest output среди всех install/check steps;
- после завершения run не существовало одного скачиваемого пакета результатов;
- failure path не доказывал, что диагностические данные сохраняются, когда они
  нужны больше всего.

Одновременно нельзя было ослабить основной quality gate. Наивный pipeline
`python -m pytest | tee pytest.log` обычно возвращает status последней команды,
то есть успешного `tee`, и способен показать зелёный test step при упавшем
pytest. Поэтому публикация отчетов должна была быть добавлена вместе с явным
сохранением статуса первого process в pipeline.

### Исходное состояние

Перед изменениями были сверены локальное и удалённое состояния:

- ветка `ci/github-actions-foundation` и HEAD
  `1ee0e45eafab56315f40aa266b1b627994388074`;
- чистое рабочее дерево и совпадающий `origin` branch;
- PR #1 открыт, mergeable и указывает на тот же HEAD;
- run `CI #8`, ID `36705516577`, для этого HEAD завершён успешно;
- workflow устанавливает locked Python 3.11 environment, выполняет
  `pip check` и обычный `python -m pytest`;
- test-result files и artifact upload отсутствуют.

Локальный `gh` по-прежнему не запускался: Snap launcher отказался работать
из-за состояния AppArmor. Это уже известное ограничение локального CLI, а не
repository defect. PR head и успешный run были проверены через
аутентифицированный GitHub connector, поэтому изменять workflow или просить
ручную проверку пользователя не потребовалось.

### Проверка официального upload action

Перед редактированием workflow была проверена официальная страница releases
`actions/upload-artifact`. Актуальным release оказался `v7.0.1`. Ссылка
release на commit была раскрыта до полного SHA
`043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`, и именно этот immutable reference
помещён в `uses:`. Комментарий `# v7.0.1` оставляет конфигурацию читаемой, но не
участвует в разрешении action.

Это сохраняет уже установленный на Step 2 supply-chain подход: workflow не
исполняет mutable major tag или branch. Все три внешних action references —
`checkout`, `setup-python` и теперь `upload-artifact` — имеют полные 40-значные
SHA.

### Что изменилось в workflow

#### Создание JUnit XML и readable log

Test step теперь выполняет логически следующий shell flow:

```text
create test-results directory
  -> disable immediate shell exit for the pytest pipeline
  -> run pytest with --junitxml=test-results/pytest.xml
  -> merge stderr into stdout
  -> tee the same readable stream into test-results/pytest.log
  -> capture PIPESTATUS[0], which belongs to pytest
  -> restore immediate shell exit
  -> exit with the captured pytest status
```

`tee` одновременно сохраняет output в файл и оставляет его видимым в обычном
job log. JUnit XML создаётся самим pytest, поэтому report соответствует тому же
запуску, а не собирается отдельным post-processing tool.

`set +e` нужен из-за GitHub Actions bash behavior: test command исполняется с
fail-fast semantics. Без временного отключения immediate exit non-zero
pipeline завершил бы shell до чтения `PIPESTATUS`. После pipeline значение
`${PIPESTATUS[0]}` немедленно копируется в `pytest_exit_code`, затем `set -e`
возвращается и step завершается через `exit "$pytest_exit_code"`.

Индекс `0` принципиален: это status команды `python -m pytest`. Status `tee`
находится в следующем элементе массива и не может выдать падение pytest за
успех.

#### Отдельная проверка обоих файлов

Следующий step `Validate test result files` имеет `if: ${{ always() }}`.
Следовательно, обычное падение test step не мешает проверке reports. Step
проходит по двум точным путям и требует, чтобы каждый файл существовал и был
непустым через `[[ -s ... ]]`.

Для каждого отсутствующего файла workflow печатает annotation формата:

```text
::error file=<path>::Expected test result file is missing or empty
```

Проверка накапливает failure flag, поэтому если отсутствуют оба результата,
job покажет две конкретные ошибки, а не остановится после первой.

Изначально предполагалось полагаться только на
`if-no-files-found: error`. Во время реализации был замечен важный edge case:
этот input защищает от ситуации, когда upload action не нашёл вообще ни одного
файла, но не является строгой гарантией наличия каждого элемента multi-path
набора. Поэтому добавлен отдельный validation step. Это делает требование
«оба ожидаемых файла» проверяемым буквально.

#### Always-run upload

`Upload test results` также использует `if: ${{ always() }}`. Он запускается:

- после успешного pytest;
- после failed pytest;
- даже если validation step сообщил missing result.

Последний случай сохраняет принцип «попытаться загрузить доступную
диагностику», одновременно оставляя job красным из-за точной validation
ошибки. В нормальном success/failure test flow оба файла передаются одному
artifact `pytest-results-python-3.11`.

`if-no-files-found: error` сохранён как второй уровень защиты самого upload
step. `retention-days` отсутствует, поэтому срок жизни artifact управляется
настройкой repository. Это CI operational setting. Оно не подтверждает и не
изменяет retention product data, offline queue guarantee или telemetry
storage policy.

### Полный поток Step 4.5

Success flow:

```text
pytest runs all tests
  -> pytest writes JUnit XML
  -> tee writes readable log and mirrors output to the job log
  -> pytest status 0 is preserved
  -> validation confirms both files are non-empty
  -> upload-artifact publishes both files
  -> Python 3.11 job succeeds
```

Test-failure flow:

```text
pytest reports a failure and writes result files
  -> tee preserves readable diagnostics
  -> test step exits with pytest's non-zero status
  -> always() validation still checks both files
  -> always() upload still publishes both files
  -> job remains failed because the pytest status was not masked
```

Missing-result flow:

```text
an expected report is absent or empty
  -> always() validation emits a path-specific GitHub error
  -> validation exits non-zero
  -> always() upload is still attempted for available diagnostics
  -> if nothing exists, upload action also fails via if-no-files-found: error
```

### Как это решает задачу

Machine consumers получают стандартный JUnit XML с числом tests, failures и
errors. Разработчик получает компактный pytest log без install noise. Оба
представления относятся к одному test invocation и находятся в одном artifact.

Failure observability больше не противоречит correctness gate: reports
публикуются после non-zero pytest, но итоговый status остаётся non-zero.
Явная file validation отделяет два вида отказа: падение самих тестов и поломку
механизма формирования diagnostics.

Step не требует hardware, network call из tests, production Supabase, secret,
database или Docker. Единственное внешнее действие — стандартная публикация CI
artifact средствами GitHub Actions после test execution.

### Что происходило во время реализации и как решались проблемы

#### Нужно было сохранить именно status pytest

Простого `set -o pipefail` было бы достаточно в обычном случае, когда `tee`
успешен, но явное чтение `${PIPESTATUS[0]}` точнее выражает контракт: job
возвращает status конкретно pytest, а не вычисленный status всего pipeline.
Отдельная локальная симуляция с non-zero process status `23` сначала доказала
механику capture, затем настоящий pytest failure path подтвердил status `4`.

#### `if-no-files-found` не доказывал наличие каждого файла

После первого варианта workflow был рассмотрен partial-artifact случай. Один
существующий файл позволил бы upload action начать upload, даже если второй
ожидаемый report отсутствует. Отдельный `Validate test result files` закрыл
этот пробел и формирует понятную annotation для каждого точного пути.

#### Нельзя было смешивать два вида retention

В плане остается открытым Product decision о хранении telemetry. Artifact
нужен только для диагностики Pull Request CI. Поэтому ни число дней, ни новая
durable decision запись не добавлялись: GitHub использует repository default,
а `DECISIONS.md` не меняется.

#### Локальный GitHub CLI оставался недоступен

Ошибка Snap/AppArmor повторилась при удалённой сверке. Она не повлияла на
implementation: исходный PR/run state прочитан через GitHub connector, а
актуальный public action release и полный upstream commit проверены в
официальном `actions/upload-artifact` repository.

### Проверка и что она доказывает

На Python 3.11.9 выполнены locked reinstall и проверки текущего project:

```bash
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest --junitxml=test-results/pytest.xml
```

Результаты:

- locked wheel build и reinstall: PASS;
- dependency consistency: PASS (`No broken requirements found`);
- полный suite: PASS (`12 passed`);
- pytest exit status: `0`;
- оба result files существуют и непусты;
- JUnit XML разбирается стандартным XML parser и сообщает `12` tests,
  `0` failures, `0` errors;
- readable log содержит путь generated XML и итог `12 passed`.

Отдельная failure-path проверка направила pytest на отсутствующий test path.
Pytest вернул status `4`, pipeline создал непустые XML/log files, и сохранённый
`pytest_exit_code` остался равен `4`. Это доказывает, что `tee` не маскирует
реальный pytest outcome.

Отдельная missing-results проверка была выполнена в пустом временном каталоге.
Она напечатала две annotations — для XML и log — и завершилась status `1`.

Workflow contract validation дополнительно доказала:

- YAML синтаксически разбирается;
- все три `uses:` закреплены полными SHA;
- validation и upload имеют `always()`;
- перечислены оба точных result path;
- задан `if-no-files-found: error`;
- `retention-days`, secret references и `pull_request_target` отсутствуют;
- Product/runtime tests и dependencies не менялись.

### Что сознательно осталось вне Step 4.5

Step 4.5 не добавлял:

- Product telemetry retention или CI-specific retention duration;
- новые test semantics или fixtures;
- duplicate/idempotency, offline queue, reconnect, replay или buffered burst
  Step 5;
- out-of-order, stream restart, late-data или clock-skew Step 6;
- API, HTTP, Storage Adapter, Supabase, PostgreSQL или Docker;
- credentials, identity, roles, authorization или remote commands;
- caching, lint, type checking, coverage threshold или test splitting;
- deployment, branch protection, PR merge или Hardware-in-the-Loop.

### Удалённая проверка и завершение шага

После явного разрешения пользователя реализация и подготовленный handoff были
зафиксированы commit `a4604c7` (`ci: publish pytest result artifacts`) и
отправлены в `ci/github-actions-foundation`.

Push запустил GitHub Actions workflow `CI`, run ID `36708553100`, run number
`9`. Job `Python 3.11` завершился с conclusion `success`. Все значимые steps —
locked installation, `pip check`, pytest, `Validate test result files` и
`Upload test results` — завершились успешно.

Run опубликовал artifact `pytest-results-python-3.11`, ID `11093152151`,
размером `1113` archive bytes. Artifact был скачан во временный каталог через
GitHub Actions API. SHA-256 скачанного ZIP
`f2aa0cf4a9aaabe41d6f4308f9b2fe28fc9c308e8010b744ee3838bbf087639e`
точно совпал с digest, который сообщил GitHub. ZIP integrity check не нашёл
ошибок.

Внутри находились ровно два ожидаемых непустых файла:

- `pytest.xml` — `2117` bytes, `12` tests, `0` failures, `0` errors,
  `0` skipped;
- `pytest.log` — `721` bytes, содержит runner path созданного XML и итог
  `12 passed in 0.03s`.

Таким образом, remote проверка доказала всю цепочку на чистом GitHub-hosted
runner: reports не только создаются локально, но проходят always-run
validation, загружаются официальным action, появляются в API, скачиваются как
целостный artifact и содержат ожидаемые machine-readable и human-readable
результаты.

После успешного run и inspection `CI_PLAN.md` и `CI_STATE.md` переведены из
`READY_FOR_COMMIT` в `DONE`. Следующим шагом остаётся Step 5; никакая его
реализация в рамках Step 4.5 не выполнялась.

---

## Step 5 — Duplicate, offline и reconnect-сценарии

### Короткий итог

Step 5 соединил уже существующие opaque transport и temporary durable queue в
минимальный детерминированный test flow. Новая функция `flush_test_queue()`
пытается передать FIFO-head, удаляет его только после настроенного результата
`True` и останавливается на первом `False`, оставляя неотправленное сообщение в
очереди. Reconnect моделируется не скрытой автоматикой, а новым
`ScriptedTransport` и отдельным явным вызовом функции.

Четыре новых сценария доказывают:

- две попытки с одним fixture `message_id` дают одну логическую test
  acceptance;
- недоступный transport не удаляет сообщения из test queue;
- после reconnect сохранённые сообщения воспроизводятся в порядке FIFO;
- тот же порядок сохраняется для correctness burst из `64` fixture messages.

Число `64`, поля envelope, правило принятия по `message_id` и результат
transport остаются test configuration. Шаг не определяет production retry,
acknowledgement, storage, retention, capacity, overflow или SLO.

### Почему этот шаг был нужен

После Step 4 существовал test-only telemetry envelope, а после Step 3 —
отдельные детерминированные transport и queue boundaries. Однако независимые
тесты границ ещё не доказывали составное поведение при повторной попытке,
недоступности transport или восстановлении связи.

Без Step 5 оставались непроверенными важные технические свойства будущего CI
потока:

1. повтор одного логического fixture message не должен создавать два
   логических принятия внутри тестового сценария;
2. `False` от configured transport не должен приводить к удалению queue head;
3. новый явный replay после reconnect должен сохранить FIFO order;
4. механизм должен работать не только для трёх сообщений, но и для более
   заметной deterministic sequence без заявления о production scale.

Реализовывать настоящий retry loop или storage adapter на этом шаге было бы
преждевременно. Product Management ещё не подтвердил timeout, backoff,
acknowledgement, offline guarantee, retention duration, maximum buffer size,
overflow policy или production idempotency key. Поэтому Step 5 проверяет
только явно названную fixture-механику.

### Проверка состояния перед изменениями

До редактирования были проверены:

- ветка `ci/github-actions-foundation`;
- локальный HEAD
  `33b61371869a15bdf8480638e6d7eb8895784964`;
- тот же SHA у `origin/ci/github-actions-foundation`;
- remote URL
  `https://github.com/evinlort/TLM_device_data_platform.git`;
- открытый Pull Request #1;
- успешный `CI` run #10, ID `36709494100`, для фактического starting HEAD;
- успешный Step 4.5 run #9, ID `36708553100`;
- наличие обоих artifacts в run listings;
- повторно скачанный Step 4.5 artifact.

SHA-256 повторно скачанного Step 4.5 ZIP равен
`f2aa0cf4a9aaabe41d6f4308f9b2fe28fc9c308e8010b744ee3838bbf087639e`
и совпадает с GitHub digest. `unzip -t` подтвердил целостность. Архив содержит
ровно ожидаемые `pytest.xml` размером `2117` bytes и `pytest.log` размером
`721` bytes. Log сообщает `12 passed`, а XML — `12` tests, `0` failures,
`0` errors и `0` skipped.

Во время сверки обнаружилось одно расхождение: `CI_STATE.md` называл repository
private, а GitHub API сообщал `public`. Согласно bootstrap-инструкции работа
была остановлена до расследования. Пользователь подтвердил, что публичность
установлена намеренно. После этого актуальная visibility была записана в новый
handoff, и Step 5 продолжился.

### Минимальная orchestration boundary

В `src/tlm_device_data_platform/simulation.py` добавлена одна функция:

```python
flush_test_queue(
    test_queue: DurableQueue,
    test_transport: Transport,
) -> tuple[bytes, ...]
```

Она не знает `TelemetryFixtureEnvelope`, JSON, `message_id`, `stream_id` или
`sequence_no`. Вход и выход остаются opaque `bytes`, поэтому существующая
provider-independent boundary не изменилась.

Один вызов выполняет только следующий детерминированный алгоритм:

```text
peek FIFO head
  -> if queue is empty: stop
  -> call configured Transport.send(head)
  -> if result is False: stop without dequeue
  -> if result is True: dequeue the same head
  -> record this successful test attempt
  -> continue with the next head
```

После successful result функция дополнительно проверяет, что `dequeue()`
вернул именно ранее увиденный head. Если test queue неожиданно изменилась между
`peek` и `dequeue`, deterministic flow завершается явной ошибкой вместо тихого
удаления другого message.

Название аргументов, docstring и поведение подчёркивают ограничение: это
test-only orchestration. Функция не запускает background worker, не ждёт
время, не повторяет `send()`, не создаёт transport, не обнаруживает reconnect и
не рассчитывает backoff. Таким образом, одна короткая composition boundary
достаточна для сценариев, но не притворяется production client.

### Как определена логическая acceptance duplicate

`Transport.send() -> bool` остаётся только configured delivery outcome. Step 5
не переопределяет `True` как database commit или подтверждение production
server. Поэтому logical acceptance определена локально внутри
`tests/test_delivery_scenarios.py` функцией `_logical_fixture_acceptance()`.

Для этого теста правило выглядит так:

```text
parse delivered fixture bytes
  -> inspect fixture message_id
  -> keep the first envelope for each message_id
  -> ignore later occurrences of that same fixture message_id
```

Это правило существует только для доказательства требуемой логической
idempotency. Оно не утверждает, что production обязан использовать это поле
как database unique key, какой payload следует сохранить при конфликте или
какой ответ должен получить device.

### Добавленные test fixtures и scenarios

Новый файл `tests/test_delivery_scenarios.py` использует только существующие
test boundaries и новый explicit flush.

`_test_envelope()` строит fixture envelopes с именами
`test-step-5-message-*`, stream `test-step-5-stream` и test timestamp
`2042-01-02T03:04:05Z`. Эти значения не являются production defaults.

`_enqueue()` явно помещает переданные serialized bytes во временную файловую
очередь. Каждый тест использует отдельный `tmp_path`, поэтому состояние не
разделяется между test cases и не зависит от filesystem предыдущего запуска.

#### Duplicate fixture retry

`test_duplicate_message_id_retry_is_logically_accepted_once` дважды помещает
в очередь одинаковые serialized bytes с `message_id` равным
`test-duplicate-message`. `ScriptedTransport((True, True))` доказывает, что
обе попытки действительно произошли. Затем fixture acceptance оставляет один
envelope.

Проверяются одновременно два разных факта:

- transport attempts содержат duplicate дважды;
- logical accepted result содержит его один раз.

Queue после двух настроенных successful attempts пуста. Дедупликация не
встроена в queue или transport и потому не меняет их общие contracts.

#### Unavailable transport

`test_unavailable_transport_retains_messages_in_test_queue` помещает два
fixture messages и использует `ScriptedTransport((False,))`.

Функция пытается передать только первый head, получает `False` и возвращает
пустой набор successful attempts. Новый instance `TemporaryFileQueue` видит
оба прежних messages и извлекает их в исходном FIFO order. Это доказывает
удержание через границу Python object lifetime, не обещая production
crash-safety или retention duration.

#### Reconnect replay

`test_reconnect_replays_persisted_messages_in_fifo_order` создаёт messages с
fixture `sequence_no` 1, 2 и 3. Первый explicit flush получает `False` и
ничего не удаляет. Затем test создаёт новый `ScriptedTransport` с тремя
результатами `True` и новый queue instance для того же temporary path.

Replay attempts в точности совпадают с исходными serialized bytes, parser
наблюдает sequence `(1, 2, 3)`, а queue после успешного replay пуста. Новый
transport и второй вызов явно обозначают reconnect; product reconnect detector
не имитируется и не предполагается.

#### Correctness-scale buffered burst

`test_reconnect_replays_correctness_scale_buffered_burst` повторяет offline и
reconnect flow для `TEST_CORRECTNESS_BURST_SIZE = 64`.

После первого `False` новый queue instance содержит все `64` messages. После
второго explicit flush:

- replayed bytes полностью равны исходному tuple;
- parsed `sequence_no` равны `1..64` без пропусков и перестановок;
- temporary queue пуста.

Размер `64` выбран как test fixture, достаточно большой для проверки цикла и
FIFO порядка вне тривиальных трёх элементов. Тест не измеряет duration,
throughput, memory или disk usage и поэтому не устанавливает capacity,
performance target или SLO.

### Полные потоки Step 5

Duplicate flow:

```text
serialize one fixture envelope
  -> enqueue identical bytes twice
  -> explicit flush makes two configured successful attempts
  -> test-only acceptance groups by fixture message_id
  -> one logical fixture envelope remains
```

Offline flow:

```text
enqueue opaque fixture bytes
  -> explicit flush peeks oldest message
  -> configured transport returns False
  -> flush stops without dequeue
  -> new queue instance loads all original messages
```

Reconnect flow:

```text
offline flush leaves queue intact
  -> test constructs a new configured successful transport
  -> second explicit flush reads the same temporary queue
  -> each successful head is removed in FIFO order
  -> parsed fixture sequence remains ordered
  -> queue becomes empty
```

Burst flow:

```text
serialize and enqueue fixture sequence 1..64
  -> unavailable attempt preserves all 64 messages
  -> explicit reconnect replays all opaque bytes
  -> byte equality and parsed sequence equality both pass
  -> no performance or capacity conclusion is drawn
```

Ни один поток не использует hardware, sleep, wall clock, random input, API,
HTTP, production network, database, Supabase, PostgreSQL, Docker, secret или
credential.

### Что происходило во время реализации и как решались проблемы

#### Repository visibility не совпала с handoff

Bootstrap запрещал менять файлы при расхождении actual state и `CI_STATE.md`.
GitHub connector дважды подтвердил public visibility, тогда как handoff
говорил private. Работа была остановлена, evidence сообщён пользователю, и
только после подтверждения намеренной публичности implementation продолжился.
Это не потребовало изменения GitHub settings; исправлена только factual запись
в handoff.

#### Нельзя было превратить `False` и `True` в product protocol

Самый удобный API мог называться retry/ack worker и автоматически ждать
reconnect. Такой API незаметно определил бы product policy. Вместо него выбран
один synchronous explicit flush. Его docstring прямо говорит, что configured
success и removal имеют смысл только внутри deterministic test scenario.

#### Duplicate acceptance могла стать ложной storage specification

Дедупликация не добавлялась в `TemporaryFileQueue`, `ScriptedTransport` или
общий source module. Она находится в private test helper и использует
fixture-only `message_id`. Поэтому тест доказывает требуемый логический
результат, но не навязывает будущему Storage Adapter database schema.

#### Первый locked reinstall не получил build dependency

Первый запуск команды

```bash
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
```

в restricted sandbox не смог разрешить DNS для получения закреплённого
`setuptools==84.0.0` в isolated PEP 517 environment. Ошибка возникла до build
и не относилась к Step 5 code.

Та же команда была повторена после явного разрешения network access. Никакие
dependency versions, constraints или build settings не менялись. Wheel
собрался и установился успешно.

#### Installed-package boundary требовал reinstall

Проект по-прежнему использует `src/` layout и pytest `importlib` mode. Поэтому
финальная проверка выполнялась после rebuild/reinstall wheel, а не через
добавление source directory в `PYTHONPATH`. Дополнительный import из `/tmp`
показал путь `.venv/lib/python3.11/site-packages/.../simulation.py`.

#### Existing artifact flow не потребовал изменения

Новые test cases автоматически попали в прежнюю `python -m pytest` command.
Workflow уже создаёт JUnit XML и readable log, проверяет оба файла и загружает
artifact. Поэтому `.github/workflows/ci.yml` не редактировался: Step 5 не
обнаружил дефекта в завершённом Step 4.5 flow.

### Проверка и что она доказывает

После финального reinstall на Python 3.11.9 выполнены:

```bash
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest --junitxml=test-results/pytest.xml
```

Результаты:

- locked wheel build и reinstall: PASS;
- dependency consistency: PASS (`No broken requirements found`);
- полный suite: PASS (`16 passed`);
- pytest exit status: `0`;
- JUnit XML: `16` tests, `0` failures, `0` errors, `0` skipped;
- `pytest.xml` и `pytest.log`: существуют и непусты;
- Step 5 scenario suite пять раз подряд: PASS (`4 passed` каждый раз);
- installed-package import из `/tmp`: PASS;
- forbidden hardware/production dependency scan: PASS;
- workflow по-прежнему содержит оба result paths, два `always()` conditions и
  `if-no-files-found: error`;
- `git diff --check`: PASS.

Пять повторных прогонов не являются статистическим performance test. Они
проверяют отсутствие случайной зависимости от test order, реального времени
или остаточного temporary queue state.

Полный suite подтверждает, что четыре новых сценария не сломали package,
simulator boundary или telemetry fixture contract. XML/log проверка
подтверждает, что существующий artifact contract автоматически включает новый
suite.

### Что сознательно осталось вне Step 5

Step 5 не определял и не реализовывал:

- production retry timing, attempt limits или backoff;
- acknowledgement protocol или mapping transport result;
- production idempotency key, database unique constraint или conflict result;
- offline retention duration или durability guarantee;
- queue capacity, overflow или data-loss policy;
- performance, throughput, fleet scale или SLO;
- Step 6 out-of-order current-state, stream restart, late-data или clock-skew
  semantics;
- API, HTTP, Storage Adapter, Supabase, PostgreSQL или Docker;
- credentials, identity, roles, authorization или remote commands;
- новые dependencies, caching, lint, type checking или coverage threshold;
- deployment, branch protection, Pull Request merge или Hardware-in-the-Loop.

### Состояние перед commit approval

Implementation, tests и handoff подготовлены локально. `CI_PLAN.md` и
`CI_STATE.md` имеют статус `READY_FOR_COMMIT`. `NEXT_SESSION.md` описывает
только Step 6 и не разрешает начинать его, пока Step 5 не получит approved
commit/push, successful Pull Request run и inspection опубликованного
artifact.

Удалённая проверка Step 5 пока намеренно не заявлена: она возможна только после
явного разрешения пользователя на commit и push. До этого момента Step 5 не
имеет статус `DONE`.

### Удалённая проверка и завершение шага

После явного разрешения пользователя реализация и подготовленный handoff были
зафиксированы commit `f893661` (`test: add deterministic delivery scenarios`)
и отправлены в `ci/github-actions-foundation`.

Push запустил GitHub Actions workflow `CI`, run ID `36721698288`, run number
`11`, для полного commit SHA
`f89366151dc7b913feb6d77bef776b960a575a88`. Job `Python 3.11` завершился с
conclusion `success`. Через GitHub connector отдельно подтверждено, что каждый
step, включая checkout, Python setup, locked installation, `pip check`, pytest,
result-file validation и artifact upload, имеет conclusion `success`.

Первый ответ прямого jobs API уже показывал завершённый successful job, но два
вложенных step summary временно оставались в состоянии `in_progress`. Это было
расценено как несогласованное промежуточное представление API, а не как
доказательство завершения. Повторная проверка через GitHub connector вернула
полный список, где все steps были `completed/success`; только после этого
remote job validation была принята.

Run опубликовал artifact `pytest-results-python-3.11`, ID `11098952143`,
размером `1254` archive bytes. Artifact был скачан через подключённый GitHub
доступ во временный каталог. SHA-256 скачанного ZIP
`f5eb6b10322b29f799f64eb94cf6eb64cc759f7cae3684533b56325e671f738c`
точно совпал с digest GitHub. `unzip -t` подтвердил целостность архива.

Внутри находились ровно два ожидаемых непустых файла:

- `pytest.xml` — `2642` bytes, `16` tests, `0` failures, `0` errors,
  `0` skipped;
- `pytest.log` — `801` bytes и итог `16 passed`.

Удалённая проверка доказывает, что Step 5 проходит на чистом GitHub-hosted
runner с тем же locked environment и что существующий Step 4.5 artifact flow
без изменений публикует результаты расширенного suite. После успешного run и
inspection `CI_PLAN.md` и `CI_STATE.md` переведены в `DONE`.

Следующим остаётся Step 6. Его реализация в этой сессии не начиналась и должна
стартовать только в новой сессии через `docs/ci/BOOTSTRAP_PROMPT.md`.

---

## Step 6 — Ordering, stream и late-data сценарии

### Короткий итог

Step 6 добавил минимальную test-only модель истории и текущего состояния для
telemetry fixtures. Каждое поступление теперь можно записать в историю вместе с
контролируемыми тестом `observation_no` и `observed_at`. Текущее состояние
обновляется только сообщением с большим `sequence_no` внутри stream, который
явно выбран test harness. Поэтому out-of-order сообщение сохраняется, но не
откатывает более новое состояние; новый fixture `stream_id` может явно начать
последовательность заново; позднее сообщение старого stream остаётся в истории,
но не вытесняет состояние нового stream.

Поле `recorded_at` намеренно не интерпретируется как доказательство порядка,
доверия или полномочий. Clock-skew сценарий использует далёкие прошлые и
будущие значения device time и подтверждает, что они не выбирают
`current_state` и не активируют stream.

Вся модель остаётся частью явно обозначенного fixture contract. Она не является
production хранилищем, Storage Adapter, reboot protocol, authorization policy
или окончательным алгоритмом разрешения конфликтов.

### Почему этот шаг был нужен

После Step 5 CI уже умел детерминированно проверять duplicate, offline queue и
reconnect replay. Однако FIFO replay отвечает только на вопрос, в каком порядке
клиент попытался повторно передать bytes. Он не доказывает, как принимающая
сторона должна вести историю и текущую проекцию, если сообщения фактически
наблюдаются не по `sequence_no`, если устройство начинает новую сессию после
условной перезагрузки или если старое сообщение приходит после более нового.

Отдельным риском было поле `recorded_at`. Оно находится внутри test envelope и
имитирует время, сообщённое устройством. Если использовать его для выбора
текущего состояния или автоматического принятия нового stream, тест незаметно
закрепил бы недоказанное предположение: часы устройства точны и заслуживают
доверия. В реальной системе clock может отставать, спешить, быть сброшен или
контролироваться недоверенным источником. Product Management пока не определил
ни trusted clock, ни reboot identity, ни authorization semantics.

Поэтому Step 6 должен был разделить три понятия:

1. содержимое fixture envelope, включая недоверенное `recorded_at`;
2. факт и порядок наблюдения сообщения тестовой системой;
3. явно выбранный test stream, внутри которого допустимо сравнивать
   `sequence_no`.

Такое разделение позволяет проверить требуемые свойства и не выдавать
временную test configuration за production requirement.

### Проверка состояния перед изменениями

До редактирования были сверены branch, `HEAD`, remote, clean working tree,
Pull Request и GitHub Actions. Ветка
`ci/github-actions-foundation` и remote branch указывали на
`4fc720d2db00c5f852e800b06b2d4a8615be0f97`. Pull Request #1 оставался открыт
на `main`.

Handoff фиксировал successful Step 5 implementation run #11. Кроме него на
текущем documentation `HEAD` уже существовал более новый successful CI run
#12, ID `36723266684`. Все steps job `Python 3.11`, включая locked install,
`pip check`, pytest, result validation и artifact upload, завершились с
`success`.

Artifact актуального `HEAD`, `pytest-results-python-3.11` с ID `11101041556`,
был скачан и проверен отдельно. Его SHA-256
`ab5529354c9de7eca236a3d091a351610219994a178c6f739f1814bcf5c08231`
совпал с GitHub digest. ZIP прошёл `unzip -t` и содержал ровно непустые
`pytest.xml` и `pytest.log`; log завершался результатом `16 passed`.
Следовательно, activation condition Step 6 была выполнена для фактического
PR head, а не только для implementation commit предыдущего шага.

### Минимальная fixture projection

В `src/tlm_device_data_platform/telemetry_fixture.py` добавлены два test-only
типа.

`ObservedTelemetryFixture` — immutable dataclass с тремя полями:

- `observation_no` — последовательный номер поступления внутри одного fixture
  projection;
- `observed_at` — время наблюдения, которое тест передаёт явно;
- `envelope` — уже проверенный `TelemetryFixtureEnvelope`.

`TelemetryFixtureProjection` хранит список таких наблюдений, идентификатор
явно активного stream и необязательный `current_state`. Его контракт намеренно
узкий:

```text
observe opaque serialized fixture bytes at controlled observed_at
  -> parse with the existing fixture parser
  -> append every valid observation to history
  -> if stream is inactive: stop without changing current_state
  -> if active stream has no current state: select the observation
  -> if sequence_no is greater: replace current_state
  -> otherwise: keep the observation only in history
```

История наружу возвращается как tuple. Это не делает backing store durable, но
не позволяет вызывающему коду случайно изменить внутренний list через
property. Номер наблюдения вычисляется из детерминированного порядка вызовов и
не зависит от wall clock.

Метод `activate_test_stream()` представляет явное событие test harness. Он
выбирает новый fixture stream и очищает только текущую проекцию. Накопленная
история сохраняется. После этого первое сообщение нового stream может иметь
`sequence_no = 1`, даже если предыдущий stream дошёл до значительно большего
номера.

Важно, что `activate_test_stream()` не вызывается автоматически по значению
`stream_id`, `recorded_at` или любому полю входящего сообщения. Таким образом,
само сообщение не получает право объявить себя новым доверенным stream. В
production вопрос о том, кто и как подтверждает reboot или смену stream,
остаётся открытым.

### Почему модель размещена в `telemetry_fixture.py`

Существующие `Transport` и `DurableQueue` в `simulation.py` продолжают работать
с opaque `bytes`. Добавление parsing или sequence logic туда связало бы
provider-independent delivery boundary с временной JSON fixture schema.

Projection размещена рядом с уже явно test-only envelope и использует
существующий `parse_fixture_telemetry()`. Поэтому interpretation начинается
только после generic delivery boundary. `Transport.send()`,
`TemporaryFileQueue` и `flush_test_queue()` не изменены и по-прежнему ничего не
знают о `message_id`, `stream_id`, `sequence_no` или timestamps.

### Добавленные deterministic scenarios

Новый файл `tests/test_ordering_scenarios.py` содержит четыре сценария. Все
значения с префиксом `TEST_` и строки `test-step-6-*` являются test fixtures,
а не product defaults.

#### Out-of-order history

`test_out_of_order_history_does_not_roll_back_fixture_current_state`
наблюдает в одном активном stream последовательность `1, 3, 2`.

Проверяется, что history сохраняет именно arrival order `(1, 3, 2)` и получает
`observation_no` `(1, 2, 3)`. После sequence `3` позднее наблюдение sequence `2`
не откатывает `current_state`: текущим остаётся envelope с sequence `3`.

#### Новый stream после test reboot

`test_new_fixture_stream_permits_sequence_restart_after_test_reboot` сначала
наблюдает sequence `41` в stream до reboot. Затем test harness явно вызывает
`activate_test_stream()` для другого fixture `stream_id` и наблюдает sequence
`1`.

История содержит оба envelope, но current state относится к новому stream и
имеет sequence `1`. Это доказывает scoped comparison: число `1` не сравнивается
глобально с `41` из другой fixture sequence.

#### Late data старого stream

`test_late_fixture_telemetry_stays_in_history_without_replacing_new_stream`
после явной активации post-reboot stream принимает ещё один envelope старого
stream с sequence `42`.

Поздний envelope добавляется третьей записью истории. Несмотря на большое
значение `42`, он относится к inactive stream и не заменяет post-reboot
`current_state` с sequence `1`. Шаг тем самым не смешивает независимые
sequence spaces.

#### Контролируемый clock skew

`test_device_clock_skew_cannot_choose_or_authorize_fixture_current_state`
использует `ManualClock` для observation time и намеренно противоречивые
device timestamps:

- sequence `1` сообщает `recorded_at` в конце 2099 года;
- sequence `2` сообщает `recorded_at` в начале 2001 года;
- inactive stream сообщает sequence `999` и `recorded_at` в 2999 году.

`observed_at` при этом возрастает ровно на одну test second между вызовами.
История сохраняет и controlled observation times, и исходные device timestamps.
Current state становится sequence `2`, потому что сравнение происходит внутри
активного stream по fixture sequence, а far-future сообщение inactive stream
не активирует себя. Это не утверждает, что production обязан доверять
`sequence_no`; тест лишь доказывает, что текущая fixture orchestration не
использует device clock как authority.

### Полный поток Step 6

```text
test constructs a fixture envelope
  -> existing serializer validates and creates deterministic UTF-8 bytes
  -> ManualClock supplies controlled observation time
  -> TelemetryFixtureProjection parses the fixture bytes
  -> observation is always appended to test history
  -> explicit active stream gates current-state consideration
  -> greater sequence within that stream advances fixture current_state
  -> lower sequence or inactive-stream data remains history-only
```

Test reboot flow:

```text
old stream has fixture current_state
  -> test harness explicitly activates a new stream
  -> fixture current_state resets, history remains
  -> sequence 1 in the new stream becomes current
  -> later old-stream observations remain history-only
```

Ни в одном потоке нет background task, sleep, настоящего времени, случайного
input, физического устройства, API, HTTP, database, Supabase, PostgreSQL,
Docker, secret или credential.

### Что происходило во время реализации и как решались проблемы

#### Первый test run не увидел новый класс

Сразу после изменения source targeted pytest завершился collection error:
`TelemetryFixtureProjection` отсутствовал в импортированном module. Traceback
показал путь `.venv/lib/python3.11/site-packages/...`, то есть тест корректно
использовал ранее установленный Step 5 wheel, а не подменял package исходниками
из repository root.

Проблема была устранена канонической locked-командой:

```bash
.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'
```

Wheel был пересобран и переустановлен. После этого targeted suite прошёл. Не
добавлялись `PYTHONPATH`, editable install или иные обходы, которые ослабили бы
installed-package boundary.

#### Нужно было не превратить fixture projection в production policy

Автоматический выбор нового stream по первому неизвестному `stream_id` был бы
удобен, но дал бы входящему сообщению неявную власть сменить current state.
Сравнение timestamps также закрепило бы недоказанную модель доверенных device
часов. Вместо этого смена stream стала явным действием test harness, а
`recorded_at` сохраняется без влияния на projection.

Docstrings прямо перечисляют ограничения: класс не определяет production
persistence, ordering, reboot, trust или authorization. Durable решение
`CI-DEC-010` фиксирует этот scope между сессиями.

#### Existing delivery и artifact flows не потребовали изменений

Step 6 добавил parsing только в fixture layer. Generic queue/transport code и
workflow остались корректными. Новые tests автоматически попали в прежнюю
`python -m pytest` command и существующие JUnit/log artifacts, поэтому
`.github/workflows/ci.yml`, `pyproject.toml` и `requirements/test.txt` менять не
потребовалось.

### Проверка и что она доказывает

Локально на Python 3.11.9 выполнены locked reinstall, `pip check` и полный
workflow-equivalent pytest с JUnit XML и readable log.

Результаты:

- locked wheel build и reinstall: PASS;
- dependency consistency: PASS (`No broken requirements found`);
- полный suite: PASS (`20 passed`);
- pytest exit status: `0`;
- JUnit XML: `20` tests, `0` failures, `0` errors, `0` skipped;
- `pytest.xml`: `3213` bytes, непустой;
- `pytest.log`: `822` bytes, непустой;
- Step 6 suite пять раз подряд: PASS (`4 passed` каждый раз);
- installed-package import из `/tmp`: PASS;
- forbidden hardware/production dependency и uncontrolled-time scan: PASS;
- workflow по-прежнему создаёт, проверяет и загружает оба result files с
  `always()` и `if-no-files-found: error`;
- `git diff --check`: PASS.

Повторные прогоны проверяют отсутствие случайной зависимости от wall clock,
test order или общего mutable state. Они не являются performance или
statistical test. Импорт из `/tmp` подтвердил, что
`TelemetryFixtureProjection` загружается из установленного wheel в
`.venv/lib/python3.11/site-packages`.

Полный suite показывает, что новая projection не сломала package boundary,
симулятор, fixture parser или Step 5 delivery scenarios. XML/log проверка
показывает, что artifact contract без изменений охватывает уже `20` tests.

### Что сознательно осталось вне Step 6

Step 6 не определял и не реализовывал:

- production history store или current-state materialization;
- database transaction, unique constraint или conflict resolution;
- production смысл `stream_id`, способ обнаружения reboot или право сменить
  active stream;
- доверенный server time, синхронизацию часов или timestamp validation;
- production ordering, late-data window, retention или reconciliation policy;
- API, HTTP, Storage Adapter, Supabase, PostgreSQL, schema или Docker;
- credentials, identity, roles, RLS, authorization или remote commands;
- retry, acknowledgement, buffer capacity, overflow или data-loss guarantees;
- performance, throughput, fleet scale или SLO;
- новые dependencies, caching, lint, type checking или coverage threshold;
- deployment, branch protection, Pull Request merge или Hardware-in-the-Loop;
- Step 7 API/storage integration implementation.

Все перечисленные product semantics остаются открытыми. Имена полей и
алгоритм projection используются только для детерминированного Step 6 fixture.

### Состояние перед commit approval

Implementation, tests, validation и handoff подготовлены локально.
`CI_PLAN.md` и `CI_STATE.md` имеют статус `READY_FOR_COMMIT`.
`NEXT_SESSION.md` описывает Step 7, но запрещает начинать его до approved
commit/push Step 6, successful Pull Request workflow и inspection нового
artifact.

Удалённая проверка Step 6 пока намеренно не заявлена: она возможна только после
явного разрешения пользователя на commit и push. До этого Step 6 не получает
статус `DONE`.
