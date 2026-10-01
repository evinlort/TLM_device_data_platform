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

`tlm_runtime.py` разделяет coroutine сбора и доставки. ACK удаляет только точные
подтверждённые bytes. Retry сохраняет их; постоянные ошибки пакета ведут в
quarantine; ошибки доступа требуют оператора. Новые измерения после restart
получают новый stream, старые файлы сохраняют прежний.

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
