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
