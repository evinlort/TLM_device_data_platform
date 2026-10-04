# ESP32 + HC-SR04: телеметрия через TLM API

## Назначение и границы

Клиент для классического ESP32 DevKit / ESP32-WROOM, в том числе DOIT ESP32
DEVKIT V1 с подходящей разводкой. Выбран MicroPython 1.29.0; Arduino sketch
не добавлен. Wi-Fi уже встроен в ESP32. ESP32-C3/S3, WROVER и другие платы
требуют отдельной проверки варианта firmware и доступных GPIO.

**Модель датчика принята как HC-SR04, питание 5 V.** Перед подключением сверить
маркировку своего датчика. Эта схема не является универсальной для всех
ультразвуковых модулей. Физическая плата в процессе разработки не подключалась.

**Последующая проверка 03.10.2026:** ESP32-D0WD-V3 с MicroPython 1.29.0 и
реальным HC-SR04 прошёл путь до строк Supabase через TLM API. Пошаговый
[аппаратный запуск](../../docs/device_ingestion/ESP32_REAL_HARDWARE_BRINGUP_RU.md)
включает делитель из доступных резисторов, LAN/UFW и чистый автозапуск.

```text
HC-SR04 → ESP32 → постоянная flash-очередь → HTTPS /v1/telemetry
        → существующий TLM API → PostgreSQL COMMIT → ACK → удаление из очереди
```

В испытании 03.10.2026 использовался HTTP только в изолированной LAN с
явным разрешением на API и устройстве; production требует HTTPS.

Первое измерение выполняется после запуска, далее — по расписанию 10 секунд.
В payload отправляется `distance_cm`; дополнительные реальные датчики можно
добавить в словарь `read()`. Данные не отправляются напрямую в Supabase.
Новая SQL-миграция не нужна: используется существующая `tlm.telemetry_messages`
с JSONB payload из [протокола v1](../../docs/device_ingestion/PROTOCOL_V1.md).

## Подключение

Собирать при отключённом питании. ESP32 получает питание через USB. HC-SR04
нужен источник 5 V; выход ECHO нельзя напрямую подключать к GPIO ESP32.

| HC-SR04 | Подключение |
| --- | --- |
| VCC | Стабилизированные 5 V |
| GND | Общий GND с ESP32 |
| TRIG | GPIO26 ESP32 |
| ECHO | Через делитель ниже к GPIO27 ESP32 |

```text
ESP32 GPIO26 -------------------------- HC-SR04 TRIG

HC-SR04 ECHO ---- R1 = 2.2 kOhm ----+---- ESP32 GPIO27
                                  |
                              R2 = 3.3 kOhm
                                  |
ESP32 GND ------------------------+---- HC-SR04 GND

regulated 5 V ------------------------- HC-SR04 VCC
USB ----------------------------------- ESP32 USB connector
```

R1 и R2: резисторы 1%, например 0.125 W или 0.25 W. При ECHO = 5 V расчёт
напряжения GPIO27: `5 × 3.3 / (2.2 + 3.3) = 3.0 V`. Это расчёт делителя,
не утверждение об измеренном напряжении конкретного клона датчика.

На некоторых DevKit доступен USB-derived 5 V pin, обозначенный `5V` или `VIN`.
Использовать его для датчика можно только после проверки схемы и маркировки
конкретной платы. Не подавать 5 V на `3V3`. Не объединять внешние 5 V и USB
питание платы без проверки развязки. При отдельном источнике датчика объединить
только GND с ESP32; VCC датчика подключить к этому источнику, не к GPIO.

GPIO26/27 — номера GPIO, не номера контактов разъёма. TRIG выдаёт 10 us импульс,
ECHO измеряется с timeout 30000 us. Номинальная формула HC-SR04: `pulse_us / 58`
с результатом в сантиметрах; проверяется диапазон 2–400 cm. Клоны, температура,
форма/угол цели и отражения требуют проверки на реальном стенде. Две цифры после
точки не означают такую же физическую точность.

Основания: [datasheet HC-SR04](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf),
страницы 1–2; [ESP32 Series Datasheet](https://documentation.espressif.com/esp32_datasheet_en.pdf),
раздел 5.3 и IO_MUX. При VDD=3.3 V таблица DC characteristics задаёт максимум
высокого входного уровня VDD+0.3 V; 5 V на GPIO недопустимы.

## Подготовка API и регистрации устройства

Сначала выполнить [установку стенда](../../docs/device_ingestion/STAND_SETUP.md):
применить проверенные migrations к выбранной dev-БД, запустить TLM API,
зарегистрировать устройство и получить `TLM_DEVICE_ID` / `TLM_DEVICE_TOKEN`.
Исторически исходная ESP32-ветка зависела от ingestion PR; оба PR впоследствии
были объединены в `main`. Текущий порядок запуска — в аппаратном руководстве.

Устройство получает только собственный token, UUID и адрес TLM API. Пароль БД,
Supabase service_role/secret key и admin config на плату не копировать.

На компьютере скопировать `config.example.json` в `config.secret.json`, задать
права `0600` и заменить все заглушки. UUID/token взять из регистрации, не
придумывать вручную. Указать доступную сети платы Wi-Fi 2.4 GHz и HTTPS URL
ровно `/v1/telemetry`, без query string. Файл с секретами исключён через .gitignore.

`CA_FILE` указывает на доверенный CA certificate для вашего API, обычно `ca.pem`.
Получить CA у оператора API/официального издателя сертификата; не доверять
случайному сертификату, скачанному с непроверенного соединения. Клиент включает
`CERT_REQUIRED` и передаёт имя сервера для проверки. Поддерживается один CA file.
Не отключать TLS validation. `ALLOW_INSECURE_HTTP=true` разрешён только для
явно изолированного лабораторного HTTP на private/loopback IPv4; по умолчанию false.

Для TLS нужны корректные часы ESP32. `mpremote rtc --set` задаёт время с
компьютера; после потери питания может понадобиться повторная синхронизация.
При начальном годе до 2024 клиент пытается получить время через `NTP_HOST`.
`NTP_HOST=null` отключает эту попытку. NTP не считается доверенным источником
времени измерения: клиент всегда отправляет `captured_at: null`, как допускает
протокол. Без подходящих часов TLS не подтверждает доставку; очередь сохраняется.

Обычный MicroPython filesystem не скрывает token от человека с физическим
доступом/USB REPL. Secure boot, flash encryption и защищённое provisioning
в этом пилоте не реализованы.

## Установка через USB

Следующие команды — общий пример; конкретные команды и результаты проверки
03.10.2026 приведены в аппаратном руководстве.
`/dev/ttyUSB0` — пример: сначала определить реальный порт и убедиться, что это
именно нужная ESP32. Закрыть другие программы, использующие Serial/REPL.
На компьютере удобно использовать отдельное окружение:

```bash
python3 -m venv .venv-device-tools
.venv-device-tools/bin/python -m pip install esptool mpremote
.venv-device-tools/bin/mpremote connect list
```

Скачать именно **ESP32_GENERIC v1.29.0 .bin** для своей классической платы
с [официальной страницы ESP32/WROOM](https://micropython.org/download/ESP32_GENERIC/).
Не брать `.app-bin` вместо полного `.bin` и не прошивать вариант C3/S3 в WROOM.
Generic предполагает не менее 4 MiB flash; проверить свою плату.

**Первичная установка со стиранием уничтожает прежнюю прошивку, файлы и очередь.**
До неё сохранить нужное содержимое/резервную копию. Следующие две команды
выполнять только после этой проверки и с выбранным файлом `.bin`:

```bash
.venv-device-tools/bin/python -m esptool --chip esp32 --port /dev/ttyUSB0 erase-flash
.venv-device-tools/bin/python -m esptool --chip esp32 --port /dev/ttyUSB0 write-flash 0x1000 /path/to/ESP32_GENERIC-v1.29.0.bin
```

Имя в последней команде заменить фактическим путём скачанного файла. Адрес
`0x1000` относится к классическому ESP32 и полному generic image, а не ко всем
ESP32-модификациям. Если плата не переходит в download mode, использовать её
кнопки BOOT/EN по инструкции производителя, не менять случайно flash offsets.

Если MicroPython 1.29.0 уже установлен, повторное erase не нужно. Для USB-копирования
из корня репозитория выполнить:

```bash
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 fs cp firmware/esp32_micropython/tlm_core.py firmware/esp32_micropython/hcsr04.py firmware/esp32_micropython/tlm_http.py firmware/esp32_micropython/tlm_runtime.py firmware/esp32_micropython/tlm_net_worker.py :
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 fs cp firmware/esp32_micropython/config.secret.json :config.secret.json
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 rtc --set
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 exec 'from hcsr04 import HCSR04; print(HCSR04(26, 27).read())'
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 fs cp firmware/esp32_micropython/main.py :main.py
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 reset
.venv-device-tools/bin/mpremote connect /dev/ttyUSB0 repl
```

Для HTTPS до `main.py` отдельно скопировать доверенный CA API как `:ca.pem`;
для лабораторного HTTP он не нужен. Датчик должен дать реальное расстояние
до установки `main.py`; при ошибке сначала проверить делитель и проводку.
`main.py` копируется последним. Эти команды могут останавливать текущую программу
и выполнять soft reset. Перед обновлением остановить сбор и сохранить нужную
очередь. Не копировать `.venv`, тесты, серверный пакет или полный репозиторий
на ESP32. На плате используются только шесть `.py`, приватная конфигурация и,
для HTTPS, CA.
Сторонние Python-пакеты на MicroPython устанавливать не требуется.

После автозапуска не вызывать `import main; main.start()` вручную. Повторный
runtime теперь отклоняется; при перемежающихся sequence сделать чистый reset,
сохранив outbox.

Команды копирования подходят Bash и fish без активации venv. В REPL `Ctrl-C`
останавливает программу, `Ctrl-]` выходит из mpremote. Никогда не публиковать
содержимое `config.secret.json` в чате, GitHub или Serial log.

## Очередь, расписание и ошибки

Сбор и доставка выполняются одним последовательным asyncio-loop. Если в outbox
есть `.msg`, sensor не читается: firmware отправляет oldest message и повторяет
те же bytes/ID до валидного ACK. Только после ACK и удаления файла разрешено
следующее измерение. Поэтому в нормальном режиме одновременно pending только
одно сообщение; существующий старый backlog доставляется полностью до нового
sensor read. DNS и получение NTP-времени вынесены в один worker
`tlm_net_worker.py`; очередь и установка RTC остаются в основном loop. TCP
использует полученный числовой IPv4, но TLS проверяет
исходное имя API, которое также сохраняется в HTTP Host. Повтор не создаёт
новый поток, пока прежний вызов не завершён; запоздалый результат отбрасывается.
Ожидание задания ограничено 5 секундами, но это не прерывает native DNS:
при зависании worker сохранённое сообщение остаётся единственным pending, а
следующее измерение не выполняется.
После `network_worker_busy` перезапустить плату перед повторным запуском программы.
Для HTTP разрешены только канонические частные/loopback IPv4 без ведущих нулей.
Flash I/O, GC, Wi-Fi и измерение ECHO всё ещё могут давать задержки.
**10 секунд — минимальная номинальная cadence после освобождения outbox, не
hard-real-time гарантия.** Если ACK ждёт дольше, измерения за это время намеренно
пропускаются и позднее не заполняются выдуманными показаниями. Для непрерывной
offline-записи нужен другой явно выбранный способ сбора/буферизации.

Файлы очереди содержат SHA-256 и исходные bytes сообщения. Запись идёт через
staging/flush/rename; при перезапуске целый staging file восстанавливается.
Повреждённая запись останавливает программу и сохраняется для диагностики.
Очередь привязана к UUID устройства. Для этого клиента нужен корректно работающий
LittleFS/VFS с поддержкой используемых операций; ничего не форматируется автоматически.

При открытии существующей очереди имена читаются через streaming `os.ilistdir()`:
они не материализуются и не сортируются. Startup scans восстанавливают
`head`, `tail` и общее число `.msg`/`.bad`/`.tmp`; затем обычные `peek`, `enqueue` и
проверка capacity используют только эти значения. ACK и quarantine сверяют
checksum и точные bytes выбранной записи до filesystem mutation. После ACK log
содержит оставшееся общее число queue-файлов, например `delivery_ack 450`;
quarantine учитывается в этом числе. Редкий сильно разреженный старый layout
может потребовать дополнительный streaming scan для поиска следующего `.msg`,
но не создаёт список имён в RAM.

После перезапуска создаётся новый `stream_id` только для новых показаний.
Старые bytes, IDs и sequence старой очереди не меняются. ACK принимается только
с совпадающими device/message IDs и статусом 201/stored или 200/duplicate.

Timeout/5xx/429 сохраняют сообщение, выполняется backoff. 400/409/413/422
перемещают пакет в `.bad`, сохраняя bytes; остальные могут отправляться дальше.
401/403, redirect или ошибочный endpoint требуют оператора и останавливают
программу. Нет эха, stuck-high ECHO и расстояние вне диапазона дают `sensor_error`:
пакет этого измерения не создаётся, ноль вместо ошибки не отправляется.

Лимит по умолчанию — 512 файлов, включая quarantine и legacy backlog. При
заполнении или ошибке flash клиент останавливается без вытеснения старых пакетов.
После очистки legacy backlog последовательный runtime не наращивает очередь при
offline: он повторяет один сохранённый пакет и откладывает sensor read.
Фактический LittleFS может закончиться раньше configured capacity из-за размера
partition, filesystem metadata и других firmware/config files. Проверяйте
`os.statvfs()` на конкретной плате; не освобождайте место удалением pending
telemetry. При недостатке места сначала восстановите доставку backlog либо
выполните согласованное резервирование/перенос данных.
При стабильных быстрых ACK и интервале 10 секунд возможно до 8640 новых записей
в сутки, плюс filesystem операции. Ресурс flash и поведение при внезапном отключении питания не
сертифицированы; длительная промышленная эксплуатация требует отдельного решения.

## Проверки и аппаратная приёмка

Host pytest выполняет ровно те исходники, которые загружаются на ESP32.
Подменяется физический pulse acquisition; реальные TCP HTTP/TLS проверяются
отдельно. Database job выполняет MCU encoder/queue/HTTP → API → restricted
PostgreSQL → ACK. Это проверка ПО на компьютере, не запуск ESP32 Wi-Fi stack.

Отдельный workflow `ESP32 firmware / MicroPython bytecode` компилирует все шесть
модулей через mpy-cross официального MicroPython 1.29.0, закреплённого SHA
`0fd6c573ea815774668bbb16b8e197c8822368b2`. Компиляция не заменяет выполнение
на плате и не подтверждает электрическое соединение.

Модуль `_thread` в MicroPython экспериментальный: host-тесты и компиляция не
подтверждают поведение потоков конкретной платы. Подробности реализации и
проверок: [network worker](../../docs/device_ingestion/ESP32_NETWORK_REVIEW.md).

После прошивки проверить:

1. Правильные питания/GND/делитель, затем расстояние до большой плоской цели
   рулеткой; в журнале появляются `sample_persisted` и `delivery_ack`.
2. Отключение Wi-Fi и restart: старая очередь сохраняется, после восстановления
   сети доставляется без новых IDs и дублей. Ошибка сертификата не должна
   приводить к успешному ACK или отправке через отключённую проверку TLS.
3. Недоступные DNS и NTP не прекращают `sample_persisted`; после восстановления
   сети накопленная очередь доставляется. Проверить на целевой плате с реальным
   датчиком; измерения не подменять программными значениями.
4. В dev-БД появляются реальные показания правильного устройства:

```sql
SELECT message_id, stream_id, sequence_no, captured_at, received_at,
       payload ->> 'distance_cm' AS distance_cm
FROM tlm.telemetry_messages
WHERE device_id = '<PROVISIONED_DEVICE_UUID>'::uuid
ORDER BY received_at DESC
LIMIT 20;
```

Этот SQL выполняет оператор на backend; он не загружается на ESP32.
Порядок received_at — порядок получения, не текущий физический state после replay.

## Официальные технические источники

- [MicroPython ESP32 images и установка](https://micropython.org/download/ESP32_GENERIC/).
- [mpremote: USB copy, RTC, reset](https://docs.micropython.org/en/v1.29.0/reference/mpremote.html).
- [MicroPython SSL: CERT_REQUIRED, CA, RTC](https://docs.micropython.org/en/v1.29.0/library/ssl.html).
- [MicroPython asyncio: ограничения DNS](https://docs.micropython.org/en/v1.29.0/library/asyncio.html).
- [esptool: flash commands](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html).

Состояние выполнения тестов смотреть в PR #3 → Checks на точном текущем HEAD.
Исторически создание исходной ESP32-ветки само по себе не меняло remote
Supabase и не подключало плату. Последующее аппаратное испытание 03.10.2026
проверило именно этот путь в лабораторной сети; production HTTPS на плате
отдельно не подтверждён.
