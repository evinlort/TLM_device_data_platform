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

### Удалённая проверка и завершение шага

После явного разрешения пользователя реализация, tests и подготовленный handoff
были зафиксированы commit
`dac48925b2f5f0d09627a9f02b2783d332c31595`
(`test: add deterministic ordering scenarios`) и отправлены в
`ci/github-actions-foundation`.

Push запустил GitHub Actions workflow `CI`, run ID `36730767093`, run number
`13`. Job `Python 3.11` завершился с conclusion `success`. Повторная проверка
job details подтвердила, что checkout, Python setup, locked install,
`pip check`, pytest, result-file validation и artifact upload имеют статус
`completed` и conclusion `success`.

Первый ответ GitHub jobs API после завершения run был внутренне
несогласованным: весь job уже имел `completed/success`, но
`Check dependency consistency` ещё отображался как `in_progress`, а несколько
steps временно отсутствовали. Этот snapshot не был принят как окончательное
доказательство. После завершения eventual-consistency обновления повторный
запрос вернул полный согласованный список всех successful steps.

GitHub также показал информационное предупреждение, что label `ubuntu-latest`
начнёт миграцию на Ubuntu 26 с 19 октября 2026 года. Оно не повлияло на текущий
run и не требует изменения Step 6. Будущую смену runner image следует
оценивать по фактическим результатам CI, а не превращать её в незапрошенное
изменение этого шага.

Run опубликовал artifact `pytest-results-python-3.11`, ID `11105275969`,
размером `1393` archive bytes. Artifact был скачан во временный каталог.
SHA-256 скачанного ZIP
`3bf8dd9be495b94d0266244438d373cc94f78fde8332a9ceb022221ff6c9ab37`
точно совпал с GitHub digest. `unzip -t` подтвердил целостность архива.

Внутри находились ровно два ожидаемых непустых файла:

- `pytest.xml` — `3218` bytes, `20` tests, `0` failures, `0` errors,
  `0` skipped;
- `pytest.log` — `881` bytes и итог `20 passed`.

Удалённая проверка доказывает, что Step 6 проходит на чистом
GitHub-hosted runner с locked environment и что существующий artifact flow
публикует результаты всех новых ordering scenarios. После successful run и
artifact inspection `CI_PLAN.md` и `CI_STATE.md` переведены в `DONE`.

Следующим остаётся Step 7 — local API/storage integration boundary. Его
реализация в этой сессии не начиналась и должна стартовать только в новой
сессии через `docs/ci/BOOTSTRAP_PROMPT.md`.

---

## Step 7 — Локальная граница API и Storage Adapter

### Короткий итог

Step 7 добавил минимальную provider-independent границу между приёмом opaque
device message и его сохранением. Новый протокол `StorageAdapter` знает только
об операции `store(message: bytes)`. Новый `OpaqueTelemetryAPI` получает body
реального HTTP request и передаёт эти же bytes adapter без JSON parsing,
проверки fixture fields или обращения к Supabase.

Для required CI добавлена локальная реализация
`TemporaryDirectoryStorage`. Она пишет сообщения в отдельные файлы временного
каталога и позволяет повторно открыть storage другим instance. Это test
implementation для доказательства настоящей filesystem boundary, а не
production database или обещание durability.

Интеграционный тест поднимает WSGI server на случайном свободном порту
`127.0.0.1`, отправляет fixture через существующие `TemporaryFileQueue` и
`flush_test_queue()`, проходит через test `Transport`, HTTP, API и storage,
после чего повторно открывает каталог и сравнивает точные bytes. Второй тест
посылает не-JSON binary message и доказывает, что boundary остаётся opaque.

### Почему этот шаг был нужен

К концу Step 6 CI подробно проверял client-side и fixture behavior: sensor и
clock boundaries, opaque transport, durable test queue, deterministic envelope,
duplicate/offline/reconnect, ordering, смену test stream, late data и clock
skew. Однако успешный `Transport.send(bytes)` всё ещё моделировался только
`ScriptedTransport`: фактического HTTP request, server-side application seam
и отдельной storage boundary не существовало.

Нельзя было сразу подключить Supabase. В репозитории нет schema, migration,
подтверждённых table names, credentials, authorization или RLS semantics.
Прямая зависимость device code от Supabase URL или table API преждевременно
закрепила бы provider и продуктовые решения, которые остаются открытыми.

Поэтому Step 7 решает более узкую архитектурную задачу:

1. сохранить существующий device-facing контракт `Transport.send(bytes)`;
2. доказать передачу через настоящий локальный HTTP socket;
3. отделить API от способа хранения посредством `StorageAdapter`;
4. проверить реальный local filesystem I/O;
5. не интерпретировать временную telemetry fixture как production contract.

Такой seam позволяет следующему storage provider реализовать тот же минимальный
adapter, не меняя queue или device transport. При этом Step 7 не утверждает,
что production adapter обязательно будет принимать ровно один opaque blob:
это минимальная точка интеграции до появления подтверждённой schema.

### Проверка состояния перед изменениями

Перед реализацией были проверены branch, `HEAD`, remote и clean working tree.
Ветка `ci/github-actions-foundation` и её remote указывали на handoff commit
`5a1d90c61ef7f52bf3ff35650139ddaf9cf039cf`. Pull Request #1 оставался открыт
на `main`.

`CI_STATE.md` фиксировал successful implementation run #13 для Step 6. На
фактическом PR head уже существовал более новый run #14, ID `36731923102`.
Его job `Python 3.11` и все steps, включая locked install, `pip check`,
pytest, result validation и artifact upload, завершились с `success`.

Artifact run #14 `pytest-results-python-3.11`, ID `11104568500`, был скачан
и проверен. SHA-256 ZIP
`89b5f057df85ce601018842e4ecba87a77e09e29d1f3392903c18f5275bd49db`
совпал с GitHub digest. `unzip -t` подтвердил целостность, а archive содержал
ровно непустые `pytest.xml` и `pytest.log`; log завершался `20 passed`.
Следовательно, activation condition Step 7 была выполнена для актуального
handoff commit, а не только для предыдущего implementation commit.

### Provider-independent Storage Adapter

В `src/tlm_device_data_platform/local_integration.py` определён structural
protocol:

```python
class StorageAdapter(Protocol):
    def store(self, message: bytes) -> None:
        ...
```

Контракт не содержит Supabase client, SQL, table name, identifier,
`message_id`, timestamp, transaction result или acknowledgement. Он также не
возвращает product status. Успешное завершение test call означает только, что
выбранная local implementation не сообщила ошибку.

Такой узкий контракт сохраняет separation of concerns:

```text
device-side queue and Transport
  -> HTTP byte stream
  -> provider-independent API
  -> StorageAdapter
  -> replaceable local test implementation
```

Fixture parser находится за пределами этого потока. API и storage не импортируют
`telemetry_fixture.py` и не знают о `schema_version`, `message_id`,
`stream_id`, `sequence_no`, `recorded_at` или `payload`.

### Локальная filesystem implementation

`TemporaryDirectoryStorage` получает путь, предоставленный test harness, и
при каждом `store()` создаёт следующий файл вида
`test-message-00000001.bin`. Запись сначала выполняется во временный файл,
после чего `Path.replace()` перемещает его на окончательное имя. Метод
`read_all()` читает только ожидаемые record names и возвращает bytes в
детерминированном порядке.

Повторное создание `TemporaryDirectoryStorage` для того же каталога
демонстрирует, что результат пересекает настоящую filesystem boundary и не
остаётся только в памяти первого Python object.

Имена файлов, восемь цифр, последовательная numbering и использование
`Path.replace()` — local test configuration. Они не являются database
primary key, production transaction protocol, concurrency solution, retention
policy, capacity guarantee или crash-durability claim.

### Минимальный HTTP API

`OpaqueTelemetryAPI` реализован как WSGI callable стандартной библиотеки.
Конструктор получает `StorageAdapter` и явно заданный `test_ingest_path`.
Для configured `POST` request он:

1. проверяет, что `Content-Length` является неотрицательным целым;
2. читает ровно указанное число bytes из `wsgi.input`;
3. передаёт bytes в `StorageAdapter.store()`;
4. возвращает пустой test response `204 No Content`.

Неверный test route/method получает `404`, некорректная длина — `400`.
Этот минимальный request handling нужен, чтобы boundary можно было честно
вызвать через real HTTP server. Он не определяет production API error model.

Маршрут `/test-fixture-telemetry`, response `204` и mapping этого status на
`Transport.send() == True` прямо помечены как test integration choices.
Product API URL, authentication headers, acknowledgement body, retryable
statuses и error contract остаются открытыми.

### Интеграционные сценарии

Новый `tests/test_local_integration.py` использует только Python standard
library: `wsgiref.simple_server` для server и `urllib.request` для client.
Новая dependency в `pyproject.toml` или `requirements/test.txt` не
потребовалась.

#### Полный queued fixture flow

`test_fixture_crosses_real_local_http_and_storage_boundaries` выполняет
следующую цепочку:

```text
serialize TEST FIXTURE envelope to bytes
  -> enqueue bytes in TemporaryFileQueue
  -> start WSGI server on 127.0.0.1 and an OS-assigned port
  -> flush_test_queue calls the test HTTP Transport
  -> urllib sends a real POST request
  -> OpaqueTelemetryAPI reads the exact request body
  -> StorageAdapter.store writes a local binary record
  -> configured 204 maps to successful test delivery
  -> queue removes the delivered fixture
  -> server stops
  -> a new storage instance reopens the directory
  -> exact stored bytes equal the serialized message
  -> fixture parser is used only by the test after storage
```

Проверка parser в последнем пункте подтверждает, что сохранённый blob не был
изменён. Она не переносит parsing внутрь API или Storage Adapter.

Server bind использует только `127.0.0.1` и port `0`, поэтому операционная
система выбирает свободный local port. Нет фиксированного порта, sleep,
external DNS или внешнего service. Teardown всегда вызывает
`shutdown()`, `server_close()` и `Thread.join()`.

#### Непрозрачный binary message

`test_local_api_and_storage_keep_non_fixture_bytes_opaque` отправляет bytes с
`NUL`, обычным текстом, который намеренно не является telemetry JSON, и
`0xff`. Повторно открытый storage возвращает точное исходное значение.

Этот тест важен архитектурно: первый сценарий использует fixture envelope, и
без отдельного binary case можно было бы случайно связать API с JSON parser.
Binary case доказывает, что реальная boundary реализована на `bytes`, а
fixture interpretation остаётся отдельным test layer.

### Что происходило во время реализации и как решались проблемы

#### Первый locked reinstall не имел network access

Запуск canonical install внутри restricted Codex sandbox не смог разрешить
PyPI host и завершился при попытке получить закреплённый
`setuptools==84.0.0`. Это не было dependency conflict или дефектом lock.
Команда была повторена с явно разрешённым network access, после чего wheel
успешно собрался и переустановился, а `pip check` сообщил
`No broken requirements found`.

Не добавлялись editable install, `PYTHONPATH` или обход build isolation.
Таким образом, tests продолжили работать против установленного wheel.

#### Restricted sandbox запретил loopback socket

Targeted suite, запущенный с разрешённой local socket capability, сразу прошёл.
Первый workflow-equivalent full run внутри sandbox собрал все 22 tests, но два
новых tests получили `PermissionError: [Errno 1] Operation not permitted` в
`socket.socket()`; остальные 20 tests прошли.

Это было точно локализовано как security restriction среды Codex: bind не
успевал обратиться к application code, а endpoint был `127.0.0.1`. Та же
полная команда была повторена вне socket restriction и завершилась
`22 passed`. Затем integration suite прошёл пять раз подряд. Код не был
ослаблен mock HTTP вызовом, потому что цель Step 7 прямо требует real local
HTTP boundary where practical.

GitHub-hosted runner обычно разрешает loopback sockets; окончательное remote
доказательство будет получено только после approved commit/push. До этого
Step 7 имеет статус `READY_FOR_COMMIT`, а не `DONE`.

#### Нужно было не превратить local API в production contract

Добавление даже маленького HTTP endpoint создаёт риск, что его URL, status и
payload начнут восприниматься как продуктовые требования. Поэтому module
docstring, class docstrings, test identifiers и durable решение
`CI-DEC-011` явно отделяют test configuration от production semantics.

Также не был добавлен `HttpTransport` в production package. Test-local
`_LoopbackHTTPTransport` только адаптирует configured `204` к существующему
boolean test contract. Будущая production transport/acknowledgement policy
требует отдельного решения.

### Проверка и что она доказывает

Локально на Python 3.11.9 выполнены locked reinstall, dependency check,
workflow-equivalent pytest, повторные integration runs и дополнительные
static/artifact checks.

Результаты:

- locked wheel build и reinstall: PASS;
- dependency consistency: PASS (`No broken requirements found`);
- targeted Step 7 suite: PASS (`2 passed`);
- полный suite: PASS (`22 passed`);
- pytest exit status: `0`;
- JUnit XML: `22` tests, `0` failures, `0` errors, `0` skipped;
- `pytest.xml` и `pytest.log`: созданы и непусты;
- Step 7 suite пять раз подряд: PASS (`2 passed` каждый раз);
- installed-package import из `/tmp`: PASS;
- forbidden provider/credential/hardware/random/uncontrolled-time scan: PASS;
- workflow по-прежнему создаёт, проверяет и загружает оба result files с
  `always()` и `if-no-files-found: error`;
- никаких новых dependencies: подтверждено неизменностью `pyproject.toml` и
  `requirements/test.txt`.

Импорт из `/tmp` разрешил `local_integration.py` из
`.venv/lib/python3.11/site-packages`, что подтверждает installed-package
boundary. Пять повторов real HTTP tests проверяют отсутствие зависимости от
фиксированного порта, test order или оставшегося server state. Они не являются
performance или load test.

Full suite подтверждает, что новый layer не сломал существующие package,
simulation, fixture, delivery и ordering contracts. Binary test доказывает
opaque behavior; reopened storage доказывает фактический filesystem I/O;
loopback request доказывает настоящий HTTP boundary.

### Что сознательно осталось вне Step 7

Step 7 не определял и не реализовывал:

- production API URL, framework, versioning или response schema;
- TLS, credentials, device identity, roles, authorization или RLS;
- production telemetry envelope или server-side validation;
- production acknowledgement, retryable status или error semantics;
- Supabase client, table, PostgreSQL schema, migration или CLI configuration;
- database transaction, unique constraint, idempotency или conflict resolution;
- production ordering, current-state materialization, late-data или retention;
- concurrency, locking, crash recovery, capacity, throughput или durability
  guarantee для local files;
- Docker, external service, production secret или remote database access;
- новые dependencies, caching, lint, type checking или coverage threshold;
- deployment, branch protection, Pull Request merge или Hardware-in-the-Loop;
- Step 8 Supabase schema bootstrap strategy.

Все route/status/file layout значения являются test configuration. Все
перечисленные product semantics остаются открытыми.

### Состояние перед commit approval

Implementation, tests, local validation и persistent handoff подготовлены.
`CI_PLAN.md` и `CI_STATE.md` имеют статус `READY_FOR_COMMIT`.
`NEXT_SESSION.md` описывает Step 8, но запрещает начинать его до approved
commit/push Step 7, successful Pull Request workflow и inspection нового
artifact.

Удалённая проверка Step 7 пока намеренно не заявлена. После явного разрешения
нужно зафиксировать и отправить изменения, дождаться required workflow,
скачать его artifact, сверить digest, JUnit и log, затем завершить handoff. До
этого Step 7 не получает статус `DONE`, а Step 8 не начинается.

### Удалённая проверка и завершение шага

После явного разрешения пользователя реализация, tests и подготовленный handoff
были зафиксированы commit
`922ea764909e60ce9de828d557298d66a32e09b6`
(`test: add local API storage integration boundary`) и отправлены в
`ci/github-actions-foundation`.

Push запустил GitHub Actions workflow `CI`, run ID `36746384665`, run number
`15`. Job `Python 3.11` завершился с conclusion `success`. Все его steps —
checkout, Python setup, locked install, `pip check`, pytest, result-file
validation и artifact upload — получили согласованные статусы
`completed/success`.

GitHub показал информационное предупреждение о будущей миграции label
`ubuntu-latest` на Ubuntu 26 с 19 октября 2026 года. Оно не повлияло на run #15
и не меняет scope Step 7. Изменение runner image следует оценивать отдельно по
фактическим CI результатам.

Run опубликовал artifact `pytest-results-python-3.11`, ID `11111973801`,
размером `1487` archive bytes. Artifact был скачан во временный каталог.
SHA-256 скачанного ZIP
`b15231921bf2d820d9965715ca678c283f370d565563d0afc8cc0e34ad696d70`
точно совпал с GitHub digest. `unzip -t` подтвердил целостность архива.

Внутри находились ровно два ожидаемых непустых файла:

- `pytest.xml` — `3481` bytes, `22` tests, `0` failures, `0` errors,
  `0` skipped;
- `pytest.log` — `961` bytes и итог `22 passed`.

Удалённая проверка особенно важна для Step 7: в restricted локальном sandbox
loopback socket требовал отдельного разрешения, а clean GitHub-hosted runner
выполнил real HTTP tests без специальной настройки. Это подтверждает, что
required CI действительно может поднять локальный WSGI server, пройти через
queue, HTTP, API и filesystem storage и завершиться детерминированно без
внешнего service, Docker, secret, Supabase или production dependency.

После successful run и artifact inspection `CI_PLAN.md` и `CI_STATE.md`
переведены в `DONE`. Следующим остаётся Step 8 — Supabase schema bootstrap
strategy. Его реализация в этой сессии не начиналась и должна стартовать только
в новой сессии через `docs/ci/BOOTSTRAP_PROMPT.md`.

---

## Step 8 — Стратегия bootstrap Supabase/PostgreSQL schema

### Короткий итог

Step 8 определил безопасный путь от отсутствующей database schema к
воспроизводимой локальной Supabase/PostgreSQL database, не создавая выдуманных
таблиц и не обращаясь к production. Репозиторий получил project-scoped
Supabase CLI `2.118.0`, закреплённый точной npm-версией и lock-файлом, а также
отдельный документ `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md`.

Version-controlled source of truth после появления авторизованного источника
будет состоять из ordered SQL migrations в `supabase/migrations/`. Для уже
существующего remote проекта baseline разрешено получать только после явного
подтверждения точного target и schema scope. Для greenfield database первая
migration может содержать только подтверждённые Product/architecture
requirements.

На этом шаге намеренно не появились `supabase/config.toml`, migration, seed,
таблицы, роли или RLS. Это не незавершённая реализация: в репозитории нет
schema source, а пользователь не разрешал remote schema access. Создание
placeholder schema нарушило бы запрет на выдумывание Product semantics.

### Почему этот шаг был нужен

Step 7 доказал provider-independent поток от device queue через реальный local
HTTP к `StorageAdapter`, но storage implementation оставался временным
filesystem adapter. Следующие milestones должны заменить эту test boundary
локальной database и затем включить её в CI.

Нельзя было сразу перейти к `supabase start` и `db reset`. Эти команды имеют
содержательный смысл только тогда, когда Git уже содержит проверенную
конфигурацию и реальные migrations. До Step 8 отсутствовали:

- `supabase/config.toml`;
- `supabase/migrations/`;
- declarative schema files;
- seed data;
- database tests;
- Supabase CLI dependency;
- подтверждённый remote project или greenfield schema;
- решения о tables, columns, roles, RLS, retention и conflict handling.

Главной задачей было определить не SQL, а безопасный способ получить SQL,
сделать его reviewable и затем воспроизводить database только из Git.

### Сверка исходного состояния

Перед изменениями были проверены локальные branch, HEAD, remote, clean working
tree и remote Pull Request. Локальный и remote PR head совпали на
`11a96b308aa26a067cd2aeb995662f06f9c35471`; PR #1 оставался открытым и
mergeable.

`CI_STATE.md` подробно фиксировал Step 7 implementation run #15. Дополнительно
был найден более новый run #16, ID `36747992035`, относящийся к финальному
handoff commit Step 7. Его `Python 3.11` job и все steps завершились с
`success`.

Artifact run #16 `pytest-results-python-3.11`, ID `11112439370`, был повторно
скачан через GitHub connector. Его SHA-256
`92a56afc6382c97df635277829ba29234d32c844dce03f84f71d7a4d9344b69c`
совпал с GitHub digest. ZIP прошёл integrity check и содержал ровно
`pytest.xml` размером `3481` bytes и `pytest.log` размером `961` bytes. Log
сообщил `22 passed`, а JUnit — `22` tests без failures, errors и skipped.
Поэтому Step 8 начался с фактически проверенного final Step 7 head.

### Исследование repository schema sources

Полный список файлов и поиск по Supabase/PostgreSQL/schema/database terms
подтвердили отсутствие database implementation. Единственные упоминания schema
находились в test-only telemetry fixture и CI-документации. Они не являются SQL
schema source.

`TemporaryDirectoryStorage` принимает opaque `bytes` и пишет локальные binary
files. В нём нет table name, SQL, Supabase client или данных, из которых можно
однозначно вывести production database model. Поэтому он не использовался как
schema prototype.

Remote Supabase project также не был исследован. Пользователь не указал project
reference, environment или разрешённый schema scope и не давал явного
разрешения на remote access. Step 8 сохранил эту границу.

### Проверенная официальная модель Supabase CLI

Актуальные официальные материалы Supabase были проверены 2026-09-30. Они
подтвердили следующие технические факты:

- CLI можно хранить как project dev dependency и следует закреплять одной
  версией для команды;
- npm/npx-вариант требует Node.js 20 или новее;
- `supabase init` создаёт каталог `supabase/` и `config.toml`;
- local stack требует Docker-compatible runtime;
- migrations хранятся в `supabase/migrations/`;
- `supabase db reset` пересоздаёт local database и применяет migrations и seed;
- `supabase db pull` создаёт migration из remote schema, требует link или
  явный database URL и запускает local shadow Postgres container;
- текущий `db pull` может предложить обновить remote migration history;
- после bootstrap обычные schema changes должны идти через migrations, а не
  через прямое редактирование shared remote database.

Официальный GitHub latest-stable endpoint сообщил `v2.118.0`, опубликованный
2026-09-25 и не помеченный prerelease. Поэтому выбрана exact version
`2.118.0`, а не mutable `latest`, range или beta build.

### Почему добавлен npm toolchain

`package.json` имеет только техническое назначение:

```json
{
  "private": true,
  "engines": { "node": ">=20" },
  "devDependencies": { "supabase": "2.118.0" }
}
```

`private: true` защищает вспомогательный tooling package от случайной
публикации. Exact version устраняет плавающее обновление CLI. `package-lock.json`
фиксирует разрешённые npm packages и integrity hashes, а `npm ci` даёт clean
installation path. `node_modules/` добавлен в `.gitignore` как generated local
state.

Node не стал runtime dependency Python package. `pyproject.toml` и
`requirements/test.txt` не изменились. CLI пока не включён в required workflow:
Step 8 проверяет стратегию и tool bootstrap, а Docker/database job относится к
Step 9/10 после появления реальной schema.

### Почему не был committed `supabase/config.toml`

Перед принятием решения `npx supabase@2.118.0 init` был запущен только во
временном `/tmp` directory. Команда успешно создала текущий generated
`config.toml`, но файл содержал не только local project ID. В нём присутствовали
PostgreSQL major version и многочисленные API, Auth, Storage, Realtime, Studio,
SMTP и другие defaults.

Документация самого config указывает, что PostgreSQL major version должен
соответствовать remote database. Remote version неизвестна. Остальные defaults
являются лишь возможной local test configuration и могут быть ошибочно приняты
за подтверждённые product settings.

Поэтому generated config не копировался в repository и не сокращался вручную.
Он будет создан locked CLI только тогда, когда remote facts или approved
greenfield requirements позволят review каждого сохранённого значения. Такой
подход меньше по scope и точнее, чем commit большого файла с непроверенными
параметрами.

### Source of truth и два bootstrap-пути

Durable решение `CI-DEC-012` фиксирует ordered SQL migrations как будущий
database source of truth.

Для существующего remote project поток выглядит так:

```text
user authorizes exact project/environment and schema scope
  -> verify remote PostgreSQL major version and allowed commands
  -> npm ci installs Supabase CLI 2.118.0
  -> locked CLI creates local config
  -> generated config is reviewed against verified facts
  -> authenticate and link without committing credentials or .temp state
  -> db pull captures the approved schema scope
  -> do not accept migration-history mutation without separate approval
  -> review generated SQL, grants, policies, functions, triggers and omissions
  -> remove remote credentials from the working flow
  -> rebuild a disposable local database from Git
  -> run only confirmed database tests
  -> commit after user approval
```

Для greenfield project поток другой:

```text
Product/architecture approves schema requirements
  -> initialize local project with locked CLI
  -> create a named migration
  -> author only approved SQL
  -> label seed values as test data
  -> rebuild a disposable local database
  -> test only confirmed requirements
  -> commit after user approval
```

Оба пути сходятся в одной точке: clean local rebuild должен работать только из
version-controlled files и не требовать production secret.

### Граница remote safety

`db pull` рассматривается не как безусловно read-only операция. Текущая
официальная reference показывает интерактивный шаг, который может repair/update
remote migration history. Поэтому перед pull требуется разрешение не только на
доступ, но и на точный target; любое предложение изменить remote history
останавливает поток до отдельного подтверждения.

`db push`, `migration repair` и accepted remote-history update являются
remote mutations и не входят в discovery. `db reset --linked` отдельно
запрещён для production и никогда не будет автоматизирован. Credentials,
passwords, connection strings и generated `.temp` state не должны попадать в
Git или test artifacts.

### Что происходило во время реализации

#### Локальный `gh` по-прежнему не запускался

Snap/AppArmor снова отклонил запуск GitHub CLI. Дополнительно sandbox не имел
DNS для обычного `git ls-remote`. Это не было расхождением repository state.
Публичные PR/run/artifact metadata были проверены read-only GitHub API, а
authenticated artifact download выполнен через GitHub connector.

#### Первый artifact download без credentials получил `401`

Metadata публичного artifact доступна без authentication, но ZIP download
потребовал авторизацию. Попытка без credentials была остановлена ответом `401`;
никакое состояние GitHub не изменилось. Connector вернул временную download
reference, после чего ZIP был скачан в `/tmp` и полностью проверен.

#### Первая sandboxed `npm ci` оставила неполный `node_modules`

Команда в restricted environment завершилась без установленной `.bin/supabase`,
и последующая проверка честно получила `supabase: not found`. Это не было
обойдено использованием глобальной CLI. Та же clean command была повторена с
разрешённым network access. Она установила locked graph, после чего
`npx supabase --version` вернул `2.118.0`.

#### Generated test results появились как untracked files

Workflow-equivalent локальный pytest создал `test-results/pytest.xml` и
`test-results/pytest.log`. Эти файлы являются generated validation output и в
GitHub публикуются как artifact, а не source. `test-results/` добавлен в
`.gitignore`, чтобы локальный результат не попал в commit случайно. Artifact
contract workflow при этом не изменился.

### Проверка и что она доказывает

Toolchain validation использовала Node `v22.23.2` и npm `10.9.8`:

- clean `npm ci`: PASS;
- npm audit во время install: `0 vulnerabilities`;
- `npx supabase --version`: `2.118.0`;
- `npm ls --depth=0`: единственная direct dependency
  `supabase@2.118.0`;
- JSON assertions: package private, Node baseline `>=20`, manifest и lock
  фиксируют одинаковую exact CLI version.

Python regression validation на Python `3.11.9`:

- locked wheel rebuild/reinstall: PASS;
- `pip check`: PASS (`No broken requirements found`);
- полный workflow-equivalent suite через real loopback HTTP: PASS
  (`22 passed`);
- JUnit: `22` tests, `0` failures, `0` errors, `0` skipped;
- pytest XML и readable log непусты;
- import из `/tmp`: PASS, `local_integration.py` загружен из установленного
  `site-packages`.

Static validation подтвердила:

- `supabase/` directory отсутствует;
- в изменениях нет remote project URL, database password, service-role key,
  connection string или secret reference;
- required workflow по-прежнему не использует `pull_request_target`, Docker,
  production service или secret;
- workflow сохраняет always-run validation/upload двух pytest result files;
- `AGENTS.md` по-прежнему указывает на `BOOTSTRAP_PROMPT.md`;
- `git diff --check` и отдельная проверка untracked files проходят.

Эти проверки доказывают воспроизводимость CLI tool version и отсутствие
регрессии текущих 22 tests. Они не доказывают database rebuild: schema и
configuration намеренно ещё не существуют.

### Что сознательно осталось вне Step 8

Step 8 не выполнял и не определял:

- Supabase login или link;
- remote schema inspection или pull;
- `supabase/config.toml`;
- migration, declarative schema или seed;
- PostgreSQL major version проекта;
- table, column, primary/foreign key или unique constraint;
- roles, grants, RLS или authorization split;
- retention, idempotency, ordering или conflict resolution;
- Docker/local Supabase startup;
- local database reset или database tests;
- `db push`, `migration repair` или production operation;
- Step 10 integration CI job;
- deployment, branch protection или Pull Request merge.

Для Step 9 требуется новый вход: явно разрешённый существующий schema source
либо подтверждённые greenfield schema requirements. Если его нет, новая сессия
должна остановиться и запросить решение, а не создавать placeholder production
model.

### Состояние перед commit approval

Стратегия, locked CLI toolchain, validation и persistent handoff подготовлены
локально. `CI_PLAN.md` и `CI_STATE.md` имеют статус `READY_FOR_COMMIT`.
`NEXT_SESSION.md` описывает только Step 9 и запрещает начинать его до approved
commit/push Step 8, successful Pull Request workflow, artifact inspection и
появления авторизованного schema source.

Удалённая проверка Step 8 пока намеренно не заявлена: она возможна только после
явного разрешения пользователя на commit и push. До этого Step 8 не получает
статус `DONE`.

### Удалённая проверка и завершение шага

После явного разрешения пользователя стратегия, locked CLI toolchain и
подготовленный handoff были зафиксированы commit
`ef051ddeb7264ddbc392ba80c894d0d8027a46ae`
(`ci: define Supabase schema bootstrap strategy`) и отправлены в
`ci/github-actions-foundation`.

Push запустил Pull Request workflow `CI`, run ID `36760536805`, run number
`17`. Job `Python 3.11` завершился с conclusion `success`. Отдельная проверка
job details подтвердила согласованные `completed/success` для checkout, Python
setup, locked installation, `pip check`, pytest, result-file validation,
artifact upload и post steps.

Run опубликовал artifact `pytest-results-python-3.11`, ID `11118133887`,
размером `1494` archive bytes. Artifact был скачан через GitHub connector во
временный каталог. SHA-256 скачанного ZIP
`44b67a55d353dcb32250aabc9ff15bd59edcf3665ed5b5ae92578d0fb03364ee`
точно совпал с GitHub digest. `unzip -t` подтвердил целостность архива.

Внутри находились ровно два ожидаемых непустых файла:

- `pytest.xml` — `3481` bytes, `22` tests, `0` failures, `0` errors,
  `0` skipped;
- `pytest.log` — `961` bytes и итог `22 passed in 0.19s`.

Удалённая проверка доказывает, что Step 8 не нарушил существующий required
Python CI и artifact contract на clean GitHub-hosted runner. Supabase CLI
toolchain был проверен локально через clean `npm ci`; workflow намеренно не
запускает CLI и database services до появления реальной schema и задач Step
9/10. В required CI по-прежнему нет production Supabase, secret, credential,
Docker или physical hardware dependency.

После successful run и artifact inspection `CI_PLAN.md` и `CI_STATE.md`
переведены в `DONE`. Следующим остаётся Step 9, но его implementation требует
отдельного авторизованного schema source или подтверждённых greenfield schema
requirements и должна выполняться только в новой сессии через
`docs/ci/BOOTSTRAP_PROMPT.md`.

## Step 9 — Воспроизводимая локальная база и подтверждённые database tests

### Зачем был нужен этот шаг

После Step 8 repository уже фиксировал exact Supabase CLI version и безопасную
bootstrap strategy, но ещё не содержал самой базы: отсутствовали
`supabase/config.toml`, migrations и database tests. Поэтому Git не мог
воспроизвести PostgreSQL schema, а CI не мог доказать ни её форму, ни access
boundary.

Step 9 должен был превратить только подтверждённое требование в минимальный
database source of truth. Здесь особенно важно было не скопировать в production
model test-only telemetry fixture из Python tests и не придумать message ID,
device fields, timestamps, ordering, deduplication, retention или пользовательские
read policies. Всё это остаётся отдельными Product decisions.

### Подтверждённый источник и границы разрешений

Пользователь указал точный Supabase project, классифицировал его как
`development`, подтвердил `Production: no`, ограничил schema scope значением
`public` и отдельно разрешил read-only MCP inspection и определение PostgreSQL
major version. Project reference использовался только для авторизованной
операции и не был записан в version-controlled files.

Discovery показал PostgreSQL `17.6`. В проекте не было Auth users, Storage
buckets/objects, Vault secrets, Edge Functions или development branches; по
словам пользователя, Supabase URL не использовался приложением, сайтом или
устройством. В `public` первоначально оставались старые database functions и
migration-history entries, поэтому такой remote state нельзя было объявить
чистым greenfield baseline.

Пользователь вручную удалил семь functions. Последняя
`rls_auto_enable()` сначала не удалялась, потому что от неё зависел event
trigger `ensure_rls`; пользователь затем удалил и trigger, и function. Отдельно
были явно разрешены `supabase link`, scoped `db pull`, а позже очистка remote
migration history при запрете остальных remote mutations. Для трёх устаревших
history entries locked CLI выполнил только `migration repair --status reverted`.
Никакой schema deployment, `db push`, remote data write или settings change не
выполнялись.

Итоговая read-only проверка показала ноль `public` relations, functions,
policies, custom types и migration-history entries. Шесть оставшихся event
triggers принадлежат Supabase platform: owner `supabase_admin`, trigger
functions находятся в `extensions`. Они не являются application objects и
были намеренно сохранены. Таким образом remote project был приведён к пустому
development state, но migration этого шага туда не разворачивалась.

После discovery пользователь явно утвердил `PROPOSAL v1`:

- `public.ingest_messages`;
- `id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY`;
- `body bytea NOT NULL`;
- backend-only access, RLS enabled, no policies;
- duplicate и empty `bytea` разрешены;
- все более богатые Product semantics отложены.

Это подтверждение стало единственным источником schema requirements. Durable
граница записана как `CI-DEC-013`.

### Что изменилось

Locked CLI `2.118.0` создал `supabase/config.toml`. Generated файл сохранён,
потому что после discovery его ключевой database fact уже можно было проверить:
`db.major_version = 17`. Верхний комментарий явно говорит, что остальные
значения являются local test configuration и не определяют production Auth,
API, Storage, Realtime, SMTP или telemetry requirements.

Дополнительно review изменил только значения, необходимые для безопасного
локального baseline:

- `project_id = "tlm-device-data-platform-local"` отделяет local stack от
  remote project;
- `api.auto_expose_new_tables = false` запрещает implicit grants новым
  `public` objects;
- migrations включены;
- seed выключен и seed paths пусты;
- PostgreSQL major version равен подтверждённому `17`.

Первый source-of-truth migration находится в
`supabase/migrations/20260930233000_create_ingest_messages.sql`. Он создаёт
ровно одну утверждённую таблицу и две утверждённые колонки. Comments в SQL
фиксируют важные non-decisions: `id` является только internal surrogate key и
не задаёт Product ordering; `body` остаётся opaque bytes и не определяет
production telemetry contract.

Migration включает RLS, но не создаёт ни одной policy. Он сначала отзывает
table privileges у `PUBLIC`, `anon`, `authenticated` и `service_role`, затем
выдаёт `service_role` только `INSERT`. Для identity sequence тому же backend
role выдан только `USAGE`. Поэтому browser/device roles не получают database
access, а backend role не получает `SELECT`, `UPDATE` или `DELETE` через эту
migration. Никакие privileged credentials в repository не добавлены.

Database test `supabase/tests/ingest_messages.test.sql` выполняется внутри
transaction и завершает её `ROLLBACK`. Его 18 pgTAP assertions проверяют:

- наличие единственной ожидаемой table shape;
- типы, `NOT NULL`, identity mode и primary key;
- включённый RLS и отсутствие policies;
- отсутствие `SELECT`/`INSERT` у `anon` и `authenticated`;
- наличие backend `INSERT` privilege у `service_role`;
- точный round-trip bytes `00ff`;
- разрешённый zero-length `bytea`;
- разрешённые duplicate bodies.

Test не утверждает, что bytes являются JSON, telemetry envelope или уникальным
message. Он также не превращает identity order в business order.

Root `.gitignore` теперь исключает `supabase/.temp/`, а
`supabase/.gitignore` сохраняет generated `.branches`, `.temp` и local dotenv
state вне Git. Seed file не создавался, потому что approved baseline разрешает
empty database и не требует test data при reset.

### Как теперь работает локальный поток

После clean `npm ci` repository получает exact CLI `2.118.0` из lock file.
Локальный database flow имеет следующий вид:

```text
npx supabase start
  -> disposable local Supabase/PostgreSQL 17 starts
  -> version-controlled migration is applied
npx supabase db reset --local
  -> local database is recreated from migrations only
  -> no seed or remote project is used
npx supabase test db
  -> transactional pgTAP contract runs
  -> approved shape, RLS, grants and byte behavior are checked
npx supabase stop --no-backup
  -> disposable services are removed
```

Этот flow решает задачу Step 9: база восстанавливается из Git, tests опираются
только на подтверждённые requirements, а required path не зависит от remote
development или production Supabase.

### Что происходило во время реализации и как решались проблемы

#### Remote schema не был принят за source of truth автоматически

Read-only inspection обнаружил старые objects и history. Вместо создания
baseline из сомнительного состояния работа остановилась на discovery, а
пользователь отдельно подтвердил очистку. Functions и dependent trigger были
удалены пользователем. Remote history была изменена только после отдельного
явного разрешения на конкретную mutation. После этого повторная inspection
доказала пустой application scope.

#### Обычный system Docker socket был недоступен

`/var/run/docker.sock` нельзя было использовать в текущей среде. До запуска
официального local stack migration была независимо проверена на disposable
native PostgreSQL `17.9`: SQL применился, catalog shape и privileges совпали с
ожиданием, а opaque, empty и duplicate bytes сохранились корректно. Это дало
раннюю SQL-проверку, но не заменило required Supabase CLI validation.

В системе оказался установлен `dockerd-rootless.sh`. Для Step 9 был запущен
эпhemeral rootless Docker daemon, полностью размещённый в уникальном `/tmp`
directory и доступный только через его local Unix socket. Host Docker config,
system daemon и repository files не менялись. Locked CLI скачал необходимые
local images и успешно поднял Supabase stack.

#### Проверка повторяемости выполнялась дважды

После первого `supabase db reset --local` migration применилась, а
`supabase test db` сообщил один test file и все `18` успешных assertions. Live
catalog отдельно подтвердил PostgreSQL `17.6`, RLS, ноль policies и точный
privilege boundary. Затем reset и database test были повторены с тем же
результатом `18/18`. Второй цикл доказывает, что успешный результат не зависел
от одноразового состояния первого startup.

#### Cleanup rootless storage потребовал UID-aware удаления

`supabase stop --no-backup` успешно остановил local services, после чего список
containers был пуст. Сам rootless daemon корректно завершился. Его примерно
`3.4G` временного storage нельзя было полностью удалить обычным host-side
`rm`, потому что часть файлов имела UID mapping user namespace. Cleanup был
выполнен через временный `rootlesskit` namespace с тем же mapping. После этого
и data directory, и cleanup state отсутствовали. Это был только cleanup в
`/tmp`; пользовательские и repository files не удалялись.

#### Последний Step 8 artifact был перепроверен

Перед изменением handoff был подтверждён final-handoff workflow `CI`, run
`36761100821`, на starting HEAD Step 9. Job `Python 3.11` и все его steps имеют
`success`. Artifact `pytest-results-python-3.11` был скачан и распакован:
`pytest.log` показывает `22 passed`, а `pytest.xml` содержит `22` tests, ноль
failures, errors и skipped. Поэтому Step 9 действительно начался с полностью
проверенного Step 8, а не только с artifact metadata.

### Проверка и что она доказывает

Tool and configuration validation:

- clean `npm ci`: PASS, `9` packages, `0 vulnerabilities`;
- `npx supabase --version`: `2.118.0`;
- `npm ls --depth=0`: единственная direct dependency
  `supabase@2.118.0`;
- TOML parse и assertions для project ID, PostgreSQL `17`, migrations, seed и
  explicit-grant mode: PASS;
- scan не нашёл remote project reference, URL, connection string, token,
  password или credential в source changes.

Official database validation:

- Supabase local startup: PASS;
- clean reset cycle 1: PASS;
- pgTAP cycle 1: `18/18` PASS;
- live catalog и role privileges: PASS;
- clean reset cycle 2: PASS;
- pgTAP cycle 2: `18/18` PASS;
- stop without backup: PASS;
- containers и временный daemon/storage после cleanup отсутствуют.

Python regression validation:

- locked reinstall: PASS;
- `pip check`: PASS;
- полный workflow-equivalent pytest: `22 passed`;
- JUnit: `22` tests, `0` failures, `0` errors, `0` skipped;
- installed-package import из `/tmp`: PASS.

Таким образом доказаны clean rebuild, repeatability, approved database
contract и отсутствие regression в существующем provider-independent Python
flow. Required GitHub Actions workflow намеренно пока не изменён: перенос
Supabase lifecycle на clean GitHub-hosted runner является отдельным Step 10.

### Что сознательно осталось вне Step 9

Step 9 не добавлял и не определял:

- deployment migration в remote development project;
- production или staging access;
- remote dependency required CI;
- device/browser database credentials;
- API route или acknowledgement semantics;
- JSON/telemetry parsing в database;
- Product message ID, device ID, system type или timestamp columns;
- uniqueness, deduplication, ordering, late-data или current-state policy;
- retention, archive, partitioning или capacity policy;
- read, update или delete access;
- production Auth/RLS model;
- seed data;
- Step 10 GitHub Actions database/integration job;
- deployment, branch protection или Pull Request merge.

### Состояние перед commit approval

Implementation, два official local rebuild/test cycles, Python regression
checks, cleanup и persistent handoff подготовлены локально. `CI_PLAN.md` и
`CI_STATE.md` имеют статус `READY_FOR_COMMIT`. `NEXT_SESSION.md` описывает
только Step 10 и запрещает remote Supabase dependency или mutation.

Step 9 ещё не считается `DONE`: commit и push требуют явного разрешения
пользователя. После push нужно дождаться updated Pull Request workflow,
проверить каждый required job и скачать его test-results artifact. Только после
этого handoff можно финализировать как удалённо подтверждённый Step 9. В этой
сессии Step 10 не начинается.

### Удалённая проверка и завершение шага

После явного разрешения пользователя весь reviewed Step 9 был зафиксирован
commit `2e46cd6baf5dc013a64b3c0fdde54e34acb11f01`
(`ci: add reproducible local database baseline`) и отправлен в branch
`ci/github-actions-foundation`. Local HEAD, remote-tracking branch и Pull
Request head совпали. Pull Request #1 остался open, non-draft и mergeable.

Push запустил workflow `CI`, run ID `36777217649`, run number `19`, точно на
этом commit. Job `Python 3.11`, ID `110098037814`, завершился с conclusion
`success`. Отдельная проверка job metadata подтвердила successful checkout,
Python setup, locked install, `pip check`, pytest, result-file validation,
artifact upload и post steps.

Run опубликовал неистёкший artifact `pytest-results-python-3.11`, ID
`11125259470`, размером `1489` archive bytes. GitHub сообщил digest
`sha256:6d67301a53cd2005040400c5268eb28049d442ee3a6d9d8d9bef9c0b7e36793b`.
Artifact был скачан и проверен после завершения run. В нём находятся ровно два
ожидаемых непустых файла:

- `pytest.xml` — `3481` bytes, `22` tests, `0` failures, `0` errors,
  `0` skipped;
- `pytest.log` — `961` bytes и итог `22 passed in 0.22s`.

Эта remote проверка доказывает, что Step 9 commit не нарушил существующий
required Python CI и artifact contract на clean GitHub-hosted runner. Workflow
намеренно пока не поднимает Supabase: database-specific evidence этого шага —
два уже выполненных official local reset/test cycles по `18/18`. Перенос того
же lifecycle в GitHub Actions является ровно задачей Step 10.

После successful remote run и artifact inspection Step 9 переведён в `DONE`.
Текущий documentation-only handoff готов к отдельному approved commit/push.
Он не начинает Step 10, не меняет workflow, schema или remote Supabase state и
только сохраняет проверенные commit/run/artifact facts для следующей сессии.

## Step 10 — Отдельный CI job для локальной интеграции

### Короткий итог

Step 10 добавил в Pull Request workflow второй job —
`Local Supabase integration`. Он на чистом GitHub-hosted runner должен поднять
только disposable local Supabase, заново собрать database из committed
migrations, выполнить все `18` pgTAP assertions, запустить полный Python suite
из `22` tests и в любом исходе удалить local stack.

Существующий job `Python 3.11` не изменён. Новый job не использует GitHub
secrets, remote project, production service или physical device и публикует
отдельный artifact только с database-test и pytest results.

### Почему этот шаг был нужен

После Step 9 schema уже была воспроизводимой локально, но required Pull Request
workflow всё ещё проверял только Python. Database-specific доказательство
существовало в виде двух локальных Supabase cycles, а не автоматической проверки
каждого PR.

Это оставляло реальный разрыв: migration или pgTAP test можно было изменить в
Pull Request, не запустив их на clean runner. Кроме того, Step 7 уже имел
настоящий local HTTP/storage integration flow, но его совместное прохождение с
локальной infrastructure не было отдельным видимым check.

Step 10 закрывает этот разрыв, не меняя Product model. CI теперь описывает
конкретный disposable lifecycle, который воспроизводит database source of truth
из Git и одновременно выполняет существующий provider-independent flow.

### Проверка исходного состояния

Сессия началась с commit
`581d389c9b5072f80cb5eb2409b32a3716e09627` в ветке
`ci/github-actions-foundation`. Local branch, `origin` tracking branch и Pull
Request head совпадали, working tree был clean.

Pull Request #1 был open, non-draft и mergeable. Последний исходный workflow
`CI`, run `36777531943` (`#20`), завершился успешно на том же commit. Его job
`Python 3.11` и все steps имели conclusion `success`.

Artifact `pytest-results-python-3.11`, ID `11126805181`, был заново скачан и
проверен. Он содержал ровно два непустых файла: `pytest.xml` размером `3481`
bytes и `pytest.log` размером `961` bytes. JUnit сообщил `22` tests, ноль
failures, errors и skipped; log завершался результатом `22 passed in 0.61s`.
Так было доказано, что Step 10 активирован от полностью проверенного Step 9, а
не только от локального состояния.

### Проверенная актуальная toolchain model

Перед изменением workflow были повторно проверены официальные источники
Supabase и GitHub.

Supabase по-прежнему требует Docker-compatible runtime для local development,
Node.js 20 или новее для npm/npx installation, рекомендует project-scoped CLI с
закреплённой версией и использует committed migrations плюс clean `db reset`
как путь воспроизводимости. `package.json` и `package-lock.json` уже выполняли
эти требования через exact `supabase@2.118.0`.

GitHub runner-images указывает, что `ubuntu-24.04` является текущей
`ubuntu-latest` image и содержит Docker. Job использует явный
`ubuntu-24.04`, чтобы его OS base не менялся во время постепенного переноса
alias `ubuntu-latest`.

Для точной установки Node.js добавлен официальный `actions/setup-node` release
v7.0.0. Его tag разрешается в commit
`820762786026740c76f36085b0efc47a31fe5020`; GitHub API подтвердил valid
signature verification. Workflow использует полный SHA, как и остальные
actions.

### Что изменилось в workflow

В `.github/workflows/ci.yml` добавлен отдельный job с устойчивым display name:

```text
CI / Local Supabase integration
```

Job использует:

- `ubuntu-24.04`;
- explicit timeout `30` minutes;
- Node.js `22.23.2` через full-SHA `actions/setup-node`;
- Python `3.11` через уже проверенный full-SHA `actions/setup-python`;
- exact project dependency `supabase@2.118.0` через clean `npm ci`;
- существующий locked Python install contract.

`package-manager-cache: false` оставляет cache вне этого шага: caching не нужен
для correctness и не должен добавлять ещё одну изменяемую границу. После
`npm ci` отдельная команда сравнивает фактический вывод CLI ровно с `2.118.0`,
поэтому случайная подмена tool version станет явной ошибкой.

Все CLI calls используют `npx --no-install`: если locked binary отсутствует,
job падает вместо загрузки другой версии. Always-run cleanup сначала проверяет
наличие `node_modules/.bin/supabase`, поэтому failure самого `npm ci` не запускает
неуправляемую fallback installation.

Существующий job `Python 3.11` сохранён без изменения имени, runner,
timeout, commands и artifact. Это удерживает его прежний check и failure signal
стабильными. Более тяжёлый database lifecycle не скрывает обычную Python
regression и может диагностироваться отдельно.

### Полный поток нового job

Job выполняет следующий процесс:

```text
checkout without persisted credentials
  -> setup exact Node.js
  -> npm ci from package-lock.json
  -> assert Supabase CLI == 2.118.0
  -> setup Python 3.11
  -> install package and pinned test environment
  -> pip check
  -> start disposable local Supabase
  -> reset local database from committed migrations
  -> run all transactional pgTAP tests
  -> run the complete Python suite
  -> always stop Supabase without backup
  -> always validate expected result files
  -> always attempt result-artifact upload
```

`supabase start` stdout перенаправлен в `/dev/null`. CLI при успешном startup
обычно печатает local URLs и generated local keys; они не являются production
secrets, но сохранять credentials и connection data в CI logs или artifacts
нет необходимости. Ошибки остаются видимыми через stderr.

`db reset --local` явно выбирает local database и заново применяет migration
из `supabase/migrations/`. Никакой `link`, access token, project reference,
database password или remote command job не получает.

Database-test output пишется одновременно в console и
`test-results/local-integration/database-tests.log` с сохранением реального
exit status через `PIPESTATUS`. Полный pytest аналогично создаёт JUnit XML и
human-readable log. Каталог уже покрыт существующим `test-results/` ignore и
не создаёт нового generated-state правила.

Cleanup расположен до result validation и имеет `if: always()`. Поэтому он
выполняется после success или failure предыдущего step. Validation и artifact
upload также имеют `always()`: отсутствующий или пустой ожидаемый result file
становится отдельной понятной ошибкой, а существующие результаты остаются
доступны для диагностики.

Artifact `local-integration-results` содержит только:

- `database-tests.log`;
- `pytest.xml`;
- `pytest.log`.

Startup output, `.temp` state, database volume, local keys, URLs и connection
strings в artifact не входят. Его retention не определяет Product retention.

### Почему не добавлен новый database adapter

Step 10 разрешал соединить `StorageAdapter` с `public.ingest_messages`, только
если минимальный adapter мог сохранить opaque bytes без новых Product решений.
Технически это потребовало бы выбрать как минимум один пока не подтверждённый
контракт:

- PostgREST endpoint и способ передачи `service_role` key; либо
- PostgreSQL driver, connection lifecycle и transaction behavior.

Оба пути закрепили бы credential и backend connection implementation, которые
остаются открытыми. Read-back проверка также конфликтовала бы с намеренно узким
Step 9 grant: `service_role` имеет `INSERT`, но не `SELECT`.

Поэтому Step 10 не выдаёт дополнительных privileges и не создаёт
provider-specific Python code. Вместо этого один clean job проверяет две уже
утверждённые границы:

1. migration и pgTAP доказывают database shape, grants и exact opaque-byte
   behavior;
2. полный Python suite запускает queue, simulator orchestration, настоящий
   loopback HTTP server и `StorageAdapter` filesystem implementation.

Это покрывает acceptance criteria шага, не превращая CI wiring в случайный
production architecture decision. Решение сохранено как `CI-DEC-014`.

### Что происходило во время реализации и как решались проблемы

#### Sandbox запрещал системный Docker и запись CLI telemetry

Local environment не имел доступа к `/var/run/docker.sock`, а CLI пытался
обновить telemetry state в read-only home. Это ограничение текущего sandbox, а
не GitHub runner или repository workflow.

Как на Step 9, был поднят отдельный rootless Docker daemon. Все runtime, image и
volume data находились в уникальном `/tmp/tlm-step10-docker.*`; host Docker
configuration не менялась. CLI запускался с exact local binary после `npm ci`.

При последнем повторе pytest в обычном restricted sandbox два loopback tests
получили `PermissionError` на создание TCP socket. Suite был немедленно
повторён в разрешённом local-loopback context и дал `22 passed`; ранее тот же
suite уже прошёл внутри полного Supabase cycle. Это подтвердило, что failure
вызван sandbox permission, а не test или workflow regression.

#### Первый local daemon был запущен с несовместимым network option

Первая попытка использовала `--bridge=none`. Images скачались, но database
container не смог стартовать с ошибкой `unable to derive the IP value for
host-gateway`. Эта попытка не была засчитана как database validation.

Дополнительно orchestration shell той попытки не включал fail-fast, поэтому
после неуспешного reset он дошёл до Python tests. Хотя Python tests прошли, этот
результат также не считался успешным combined cycle.

Daemon был полностью остановлен и перезапущен со стандартным rootless bridge
networking. Повторный workflow-equivalent command использовал
`set -euo pipefail`, поэтому любое отклонение немедленно завершало бы validation.
После исправления Supabase startup, reset, pgTAP и pytest прошли последовательно.

#### Registry однажды вернул timeout при первом image pull

При clean download PostgreSQL image registry один раз вернул timeout ожидания
headers. Docker автоматически повторил pull, digest был получен, и image
скачался успешно. Изменять versions или обходить registry не потребовалось.

#### Cleanup был проверен не только на успешном пути

После зелёного полного цикла local stack был поднят ещё раз, затем shell
получил намеренный non-zero result, после чего был выполнен тот же
`supabase stop --no-backup`. Проверка обнаружила ноль оставшихся Supabase
containers. Это подтверждает фактическую cleanup command, а workflow-level
`always()` гарантирует её запуск после failed prior step.

После остановки daemon обычный host-side `rm` не мог удалить часть UID-mapped
image layers. Остаток был удалён внутри краткого rootless user namespace с тем
же mapping. Затем были подтверждены отсутствие daemon processes, runtime
directory и cleanup state.

### Проверка и что она доказывает

Статическая и supply-chain проверка:

- YAML parse: PASS;
- новый job и expected structure: PASS;
- все семь action uses закреплены полными 40-character SHA: PASS;
- `actions/setup-node` v7.0.0 SHA и signature: PASS;
- `git diff --check`: PASS до persistent handoff update.

Dependency и Python regression:

- clean `npm ci`: PASS, установлено `9` packages;
- `npm ls --depth=0`: только `supabase@2.118.0`;
- Supabase CLI: exact `2.118.0`;
- locked Python reinstall: PASS;
- `pip check`: `No broken requirements found`;
- full pytest: `22 passed`;
- JUnit: `22` tests, `0` failures, `0` errors, `0` skipped;
- import из `/tmp` разрешился в `.venv/lib/python3.11/site-packages`.

Official local infrastructure validation:

- disposable local Supabase startup: PASS;
- `db reset --local`: PASS, migration применена из Git;
- `supabase test db`: `1` file, `18` tests, `Result: PASS`;
- full Python suite при работающем local stack: PASS;
- три ожидаемых local integration result files существуют и непусты;
- success-path cleanup: PASS;
- simulated failure-path cleanup: PASS;
- после cleanup нет containers, daemon processes или временного storage.

Эти проверки доказывают, что команды нового job согласованы с существующим
locked project и проходят в clean disposable environment. Они ещё не заменяют
обязательную remote проверку на настоящем GitHub-hosted runner: она возможна
только после approved commit и push.

### Что сознательно осталось вне Step 10

Step 10 не добавляет и не определяет:

- remote Supabase link, pull, push, SQL или deployment;
- GitHub secret, project reference или production credential;
- физическое устройство или Hardware-in-the-Loop;
- новый table, column, grant, RLS policy, seed или migration;
- PostgREST/PostgreSQL Python adapter;
- production API route, acknowledgement или transaction semantics;
- telemetry parsing или перенос test fixture fields в database;
- identity, ordering, duplicate, retention или read-access policy;
- cache, coverage threshold, lint, typing, SLO или performance target;
- branch protection или Pull Request merge;
- Step 11 documentation и coverage work.

### Состояние перед commit approval

Workflow, local validation, cleanup, `CI-DEC-014` и persistent handoff
подготовлены. `CI_PLAN.md` и `CI_STATE.md` имеют статус `READY_FOR_COMMIT`.
`NEXT_SESSION.md` описывает только Step 11 и запрещает его активацию до approved
Step 10 commit/push, успешного прохождения обоих PR jobs и проверки обоих
artifacts.

Step 10 ещё не считается `DONE`: сначала требуется явное разрешение пользователя
на commit и push. После push необходимо проверить exact Pull Request head, оба
jobs и каждый их step, скачать `pytest-results-python-3.11` и
`local-integration-results`, сверить digests и содержимое и только затем
финализировать remote handoff. Step 11 в этой сессии не начинается.
