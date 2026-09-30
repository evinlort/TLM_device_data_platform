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

После локальной валидации Step 4 имеет статус `READY_FOR_COMMIT`. Для
завершения всё ещё нужны явное разрешение пользователя на commit/push и
успешный `CI / Python 3.11` для отправленного HEAD. Step 4.5 нельзя начинать в
этой сессии.
