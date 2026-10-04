# ESP32 / HC-SR04 — реализация и передача состояния

## Ветка и разрешённая область

По указанию пользователя создана `feat/esp32-ultrasonic-micropython` от точного
HEAD `3eb5ce365e8db4ac2ab024f5bbd23ba7c2e91b67` ветки `feat/device-ingestion-v1`.
Это необходимо: backend из PR #2 ещё не находится в main. PR #3 направлен в
эту родительскую ветку; main и PR #2 не объединяются и не изменяются автоматически.
Новая задача — MicroPython-клиент реального устройства, не изменение Product SQL.

Выбран классический ESP32 DevKit/WROOM, предполагаемый датчик HC-SR04, GPIO26
(TRIG) и GPIO27 (ECHO через делитель). Точная маркировка платы/датчика проверяется
оператором до подключения. Подробности: [firmware README](../../firmware/esp32_micropython/README.md).

## Реальный порядок TDD

Тесты записывались и выполнялись до появления соответствующего source module.
Первые RED-запуски ожидаемо падали из-за отсутствующего файла; после реализации
выполнялся GREEN-запуск. Это подтверждает порядок разработки, но не является
утверждением об аппаратной проверке.

| Граница | RED commit | Реализация | Host результат после реализации |
| --- | --- | --- | --- |
| Протокол, UUID, flash queue, ACK, cadence | `199a526` | `ff57b39` | 39 passed |
| HC-SR04 и bounded HTTP/TLS | `087d69d` | `09ce1de`, `113a954` | 22 новых; всего 61 passed |
| Sampling/delivery orchestration | `8357329` | `e93dce8` | 12 новых; всего 73 passed |
| Безопасная boot-конфигурация | `5bb24b2` | `df000cb` | 13 новых; всего 86 passed |

Локальный host: CPython 3.13.5. До реализации source отсутствовал, поэтому RED
означал FileNotFoundError при загрузке файла, а не скрытое пропускание сценария.
Логи RED/GREEN анализировались в рабочем окружении. Дополнительный настоящий
локальный TLS test проверил доверенный сертификат, отказ неверному hostname и
отказ недоверенному CA: после него 87 host tests прошли. Созданные ключи TLS
были временными test fixtures и не помещались в Git.

## Модули

`tlm_core.py` создаёт telemetry-v1 JSON, UUIDv4 и flash outbox. Исходный пакет
с checksum записывается до передачи, затем не переименовывается при retry.
Полный staging file восстанавливается; повреждение/переполнение останавливает
программу без очистки. Очередь привязана к provisioned device_id.

`hcsr04.py` измеряет физический ECHO через machine.time_pulse_us, а не генерирует
случайное значение. Host tests подставляют определённую длительность импульса.
Неполученное/некорректное измерение не превращается в 0 или stale reading.

`tlm_http.py` выполняет ограниченный HTTP/1.1 POST с token, обязательной
проверкой CA/hostname для HTTPS, ограничением ответа и проверкой полного
Content-Length/chunked/EOF framing. Redirect не переносит token на другой host.

`tlm_runtime.py` использует один последовательный loop: persisted message
повторяется до ACK и полностью блокирует следующий sensor read. ACK удаляет
только точные подтверждённые bytes. Retry сохраняет их; постоянные ошибки пакета
ведут в quarantine; ошибки доступа требуют оператора. Новые измерения после
restart получают новый stream, старые файлы сохраняют прежний.

`main.py` загружает приватный config, проверяет GPIO/UUID/token/endpoint и
управляет Wi-Fi. Требуется подходящий ESP32 build MicroPython 1.29.0. Linux
agent, SQL migration history и серверный telemetry contract не меняются.

## Сквозная проверка

Добавлены три database tests, использующие существующую изолированную
restricted-login fixture и реальный API server. Физический pulse заменён
явно тестовым значением, но остальной путь использует настоящий код firmware:

```text
pulse fixture → HCSR04.read → MCU encoder → persistent file queue
  → restart/reopen → MCU HTTPTransport → real TCP HTTP → TLM API
  → PostgreSQL under restricted LOGIN → COMMIT → MCU ACK removal
```

Дополнительно проверяются потерянное подтверждение с идентичным повтором и
подмена device_id с отказом доступа и сохранением очереди. Отсутствующая DB
конфигурация вызывает ошибку существующей fixture, а не skip. Быстрый Python job
явно исключает database marker; полный Supabase job выполняет эти тесты.

Отдельный workflow `ESP32 firmware` собирает mpy-cross из официального commit
`0fd6c573ea815774668bbb16b8e197c8822368b2` (MicroPython v1.29.0) и компилирует
все пять source modules. Он не меняет branch protection и не переименовывает
существующие required checks. Компиляция проверяет синтаксическую совместимость,
но не Wi-Fi/TLS stack на ESP32 и не наличие физического датчика.

Актуальные результаты полного suite смотреть на **точном HEAD PR #3** в Checks.
Успех промежуточного commit не означает успех финального. Запуски, отменённые
новым push, не считаются прошедшей проверкой.

## Намеренные ограничения

- 10 секунд — номинальное soft-real-time расписание. MicroPython DNS/ntptime,
  flash и GC могут давать задержки; asyncio не превращает их в hard-real-time.
- captured_at всегда null; NTP используется для TLS RTC, не как доказательство
  достоверного времени физического измерения.
- Flash queue — bounded pilot implementation. Нет доказательства ресурса
  накопителя, абсолютной сохранности при отключении питания и длительного offline.
- Token находится на filesystem устройства; защиты от физического извлечения
  через USB/flash в этом пилоте нет.
- Аппаратный запуск, фактические уровни GPIO, реальные расстояния, Wi-Fi/TLS на
  плате, USB flashing и hosted deployment не выполнялись в этой сессии.
- Supabase credentials не передаются устройству. Remote Supabase не изменялся,
  дополнительная SQL-структура для distance_cm не требуется.

Для следующей сессии прочитать AGENTS.md, этот файл и firmware README; проверить
фактические refs и результаты CI. Не merge PR #2/#3, не удалять ветки, не прошивать
плату и не изменять remote Supabase без соответствующего разрешения.

## Последующая физическая проверка — 03.10.2026

Перечень выше описывает исходную разработку PR #3 и остаётся исторической
записью. Позднее оператор проверил ESP32-D0WD-V3, MicroPython 1.29.0,
HC-SR04 на GPIO26/GPIO27, Wi-Fi 2,4 ГГц, TLM API и свежие строки
`tlm.telemetry_messages` в реальной Supabase. После исправления делителя
датчик вернул физические расстояния; после открытия узкого правила UFW и
чистого reset один runtime стабильно выводил `sample_persisted`/`delivery_ack`.
При нескольких вызовах runtime номера sequence перемежались. Этот факт
мотивировал отдельные lifecycle regression tests и guard в общем модуле
`tlm_runtime.py`. [Операторское руководство](ESP32_REAL_HARDWARE_BRINGUP_RU.md)
содержит команды, доказательства и ограничения; HTTPS production и длительная
эксплуатация не были частью этого испытания.

### Обоснование исправления и проверки

В исходном `tlm_runtime.run()` не было проверки занятого runtime, а `finally`
только вызывал `task.cancel()` без ожидания завершения задач. Два host-теста
сначала дали RED: второй запуск не отклонялся, а ошибка delivery позволяла
`run()` выйти до завершения collection cleanup. Дополнительный boot-тест дал
RED до импорта hardware modules; четыре диагностических случая дали RED до
добавления ограниченных категорий ошибок. После минимального исправления все
ESP32 host tests прошли: `141 passed`.

На commit `16d796e7159ba0f9a20145134e5551deb727d4e5` локально выполнены:

```text
.venv/bin/python -m pytest -m 'not database' -q
256 passed, 22 deselected
```

Официальный MicroPython 1.29.0 commit
`0fd6c573ea815774668bbb16b8e197c8822368b2` собран локально; все шесть
исходных `.py` скомпилированы `mpy-cross -march=xtensawin`. Локальные DB-тесты
не запускались: `TLM_TEST_ADMIN_DSN` отсутствовал, Docker daemon недоступен.
На **том же точном commit** GitHub Actions CI run
[#71](https://github.com/evinlort/TLM_device_data_platform/actions/runs/37147349807)
успешно выполнил `278 pytest passed` и `34 pgTAP` на одноразовой Supabase;
ESP32 firmware run
[#12](https://github.com/evinlort/TLM_device_data_platform/actions/runs/37147349826)
успешно скомпилировал шесть модулей. Это результаты указанного commit, не
автоматическое утверждение о будущих HEAD и не новая аппаратная прошивка.

Подтверждённые операторские причины: неверная разводка делителя, попытка
использовать 5 GHz, закрытый входящий порт UFW и несколько запущенных runtime.
Нельзя доказать по журналу, что каждый `MemoryError`/`OSError(-203)` вызван
именно перекрытием runtime. Экспериментальный HTTP timeout 20 s, дополнительная
пауза 8 s и GC-логи не подтвердили причину и в прошивку не перенесены.
HTTP framing/TLS и правило точного duplicate ACK не изменены.

## Большая flash-очередь — 04.10.2026

На физическом стенде после первой успешной доставки накопились сотни файлов.
Аппаратный замер показал, что прежние `os.listdir()` и `sorted()` временно
занимали около 35 KiB при 390 directory entries. Старый `enqueue()` дополнительно
строил список числовых индексов, а delivery loop дважды вызывал `peek()` перед
одним POST. Эти allocations совпадали по времени с asyncio, JSON и socket
objects; это подтверждённый peak-memory defect, но не доказательство причины
каждого исторического timeout.

Исправление сохраняет прежний layout `owner` + 16-digit `.msg/.bad/.tmp` и не
вводит metadata file. Startup использует `os.ilistdir()`, полностью валидирует
имена, восстанавливает целые `.tmp`, затем cache-ит `head`, `tail` и `count`.
Обычные `peek`, `enqueue`, capacity и empty checks не обходят каталог. После
ACK/quarantine следующий последовательный индекс проверяется точечно; сильно
разреженный layout использует memory-bounded streaming fallback. Запись по-прежнему
идёт через `.tmp`, flush/fsync, rename и directory sync. ACK по-прежнему удаляет
только совпавшие checksum/body bytes. I/O failure пересобирает cache streaming
scan и пробрасывается вызывающему коду.

TDD добавил old-layout очереди на 400, 512 и 1000 сообщений, запрет directory
scan во время steady-state operations, FIFO/holes/tail/count/capacity,
quarantine, completed/duplicate/ambiguous `.tmp`, unexpected-file corruption и
два startup passes без staging. Отдельный HTTP timeout test подтвердил close,
bounded `wait_closed()` и отсутствие оставшейся request task; второго firmware
network lifecycle defect на host не обнаружено.

Локальная проверка ветки:

```text
ESP32 host tests: 153 passed
pytest -m 'not database': 268 passed, 22 deselected
MicroPython 1.29.0 mpy-cross 0fd6c573...: six modules compiled
```

Disposable Supabase suite локально не выполнялся: Docker socket недоступен.
Это не скрытый skip; database tests явно deselected. Их результат нужно проверить
в CI на точном опубликованном SHA.

На ESP32 до обновления было `389 .msg`, `0 .bad`, `0 .tmp`; прежний показатель
390 включал `owner`. После обновления новые HC-SR04 samples продолжали сохраняться,
а десятки сообщений получили `delivery_ack` без `MemoryError`. Финальный firmware
логирует total count: при работающем API и продолжающемся сборе он уменьшился
с 457 до 450 во время стабильного окна. Zero-byte staging-файлы, созданные
принудительными `mpremote` interruptions во время диагностики, не удалялись:
оператор сохранил их как `.bad`, поэтому они продолжают учитываться в capacity
и total count. Исходные pending bytes не удалялись и device identity не менялась.

LittleFS оказался почти заполнен: overwrite source modules получил `ENOSPC`.
Повреждённый partial `tlm_core.py` и старый `tlm_runtime.py` были заменены только
после проверки на pinned `.mpy` (5310 и 1868 bytes) с совпавшими SHA-256; outbox,
config и остальные firmware files не менялись. После установки оставался один
4 KiB free block. Configured capacity 512 поэтому не является гарантией, что
конкретная filesystem вместит 512 records: backlog должен продолжать уходить,
а свободное место — контролироваться без удаления pending telemetry.

Во время hardware run API→Supabase периодически сообщал `OperationalError` и
`ConnectionTimeout`; прямой runtime login один раз подтвердился как `tlm_api`,
но последующие read-only SQL checks дважды не дошли до БД из-за временного DNS
failure для pooler hostname. Поэтому новые Supabase rows и duplicate query нужно
повторно подтвердить после восстановления DNS. Firmware timeout при этом сохранял
точные сообщения и sampling продолжался; это внешний remaining risk, а не повод
менять token, DSN, CA или очищать outbox.

После этой проверки общий host DNS outage продолжился, API снова перестал писать
в PostgreSQL, и total начал расти. Для защиты почти заполненного LittleFS runtime
был остановлен в REPL без reset. Эта остановка также попала в начало flash write;
третий нулевой `.tmp` был сохранён как `.bad`. Проверенное состояние на момент
остановки было `458 .msg`, `3 .bad`, `0 .tmp`; плата оставалась остановленной до
восстановления DNS/API→Supabase. Значение 450 выше остаётся фактическим
подтверждением net drain в стабильном окне, а 458 — более поздним состоянием
после внешнего outage. Не делать reset до восстановления backend path: autostart
снова начнёт sampling при минимальном свободном месте.

## Последовательный single-message runtime

После восстановления DNS отдельный drain-only запуск теми же `send_once()` и
ACK checks удалил 32 подтверждённых backlog records: total уменьшился строго
`462 → 430` без sensor reads. Этот результат показал, что простая последовательная
модель подходит фактическому требованию лучше прежних независимых collector и
delivery tasks. Перед drain неудачная попытка обычного startup при полном flash
создала ещё один нулевой staging artifact; он также сохранён как `.bad`. Поэтому
после drain фактическое состояние — `426 .msg`, `4 .bad`, `0 .tmp`.

По явному решению пользователя ESP32 runtime теперь не измеряет новый sample,
пока существует pending `.msg`. Один loop выполняет:

```text
legacy/pending message → POST same bytes until valid ACK → exact delete
empty outbox + due cadence → HC-SR04 read → persist one message → POST
```

Timeout/5xx/429 сохраняют единственный message и применяют прежний backoff;
интервальные measurements во время ожидания ACK намеренно пропускаются. После
очистки существующего backlog steady state содержит не более одного `.msg`.
Формат файлов, checksum, power-loss staging, message identity, HTTP contract и
Supabase schema не менялись.

Новые RED tests сначала подтвердили прежний дефект policy: retry всё ещё читал
sensor, а blocked DNS/NTP накопил по три файла. После удаления `collect()`/
`deliver()` и `asyncio.gather()` tests требуют ноль sensor reads при pending,
ровно один новый sample после ACK, один persisted file при blocked network,
exact retry bytes и корректный single-runtime guard.

На плату был скопирован только новый `tlm_runtime.mpy`; `config.secret.json` и
outbox не изменялись. После reset production runtime последовательно уменьшил
total `430 → 4`: все 426 `.msg` получили ACK, а четыре диагностических `.bad`
остались на flash. До `delivery_ack 4` не было ни одного `sample_persisted`, то
есть HC-SR04 не читался во время backlog drain. `MemoryError` не повторился.

Во время drain реальный API кратко сообщил PostgreSQL `ConnectionTimeout` и
`OperationalError`. ESP32 сохранила текущий файл, прошла retry/backoff
`1, 2, 4, 8, 16, 32` и после восстановления backend продолжила с того же места.
После drain наблюдались последовательные пары `sample_persisted N` /
`delivery_ack 4`; как минимум samples 1–23 завершили цикл, а невалидные
HC-SR04 readings логировались как `sensor_error` без создания telemetry.

Read-only Supabase query показал свежие реальные `distance_cm` rows для
зафиксированного device ID; duplicate query по `(device_id, message_id)` вернул
ноль строк. Host validation: 154 ESP32 tests и 269 non-database tests прошли.
