# ESP32 + HC-SR04 → TLM API → Supabase: запуск реального устройства

Это инструкция для классического ESP32 с MicroPython 1.29.0 и HC-SR04. Проверка
2026-10-03: ESP32-D0WD-V3 rev 3.1, 4 MiB flash, USB CH340 (1a86:7523),
TRIG GPIO26, ECHO GPIO27 через делитель, сеть 2,4 ГГц, TLM API на Ubuntu и
реальная таблица `tlm.telemetry_messages` в Supabase. Host работал на Python
3.11.9, esptool 5.4.0 и mpremote 1.29.0. Это один проверенный стенд, а не
сертификация всех плат, датчиков и сетей.

## 1. Маршрут и необходимые права

```text
HC-SR04 → ESP32 / MicroPython → flash outbox → POST /v1/telemetry
  → TLM API → restricted PostgreSQL runtime connection → Supabase COMMIT
  → 201 stored / 200 duplicate ACK → удаление точного сообщения из outbox
```

Устройство знает только `TLM_DEVICE_ID`, `TLM_DEVICE_TOKEN`, адрес TLM API,
Wi-Fi, GPIO и при HTTPS — доверенный CA. Supabase URL **не является** адресом
телеметрии устройства. Пароли/DSN PostgreSQL, admin credential и Supabase
service key остаются только на операторском компьютере/API. Везде ниже
`YOUR_*` — параметры своего стенда; примеры IP не следует копировать вслепую.

Нужны доступ к USB-порту, разрешённый development Supabase project, право
применить миграции/зарегистрировать устройство и возможность запустить API на
Ubuntu. Удалённую БД не сбрасывать. Если проект уже развёрнут, использовать
существующие runtime/device credentials, не создавать их повторно.

## 2. Безопасно собрать цепь без питания

**Никогда не соединять 5 V ECHO непосредственно с GPIO27 и не подавать 5 V на
`3V3` ESP32.** Общая земля обязательна. Маркировка `VIN`/`5V` различается у
DevKit-клонов: проверить схему и фактическое напряжение именно своей платы.
Собирать при отключённом USB и питании датчика.

```text
ESP32 GPIO26 --------------------- HC-SR04 TRIG

HC-SR04 ECHO -- R1 --+----------- ESP32 GPIO27
                     |
                     R2
                     |
                    GND

HC-SR04 GND ---------+----------- ESP32 GND
HC-SR04 VCC --------------------- regulated 5 V
```

Штатный делитель: `R1=2.2 kΩ`, `R2=3.3 kΩ`. Формула:
`V_GPIO = V_ECHO × R2 / (R1 + R2)`; при 5 V получается 3,0 V.
В проверенном стенде при наличии только резисторов 1 kΩ и 220 Ω была собрана
альтернатива: верхняя ветвь `R1=1 kΩ+220 Ω=1.22 kΩ`, нижняя
`R2=1 kΩ+1 kΩ=2.0 kΩ`; номинально `5 × 2.0/(1.22+2.0)≈3.11 V`.
В цепи мультиметр показал около 1.2 kΩ сверху и 1.69 kΩ снизу: последнее
**не номинал BOM**, измерению сопротивления в цепи мешают другие пути.
Проверить топологию делителя и напряжение на GPIO до подключения GPIO.
Официальные [электрические пределы ESP32](https://documentation.espressif.com/esp32_datasheet_en.html)
описывают питание 3,3 V и пределы GPIO; прямые 5 V недопустимы. Питание и
времена HC-SR04: [datasheet HC-SR04](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf).

## 3. Чистый checkout, Python и база

В новом checkout проверить ветку, состояние и инструкции:

```bash
git clone https://github.com/evinlort/TLM_device_data_platform.git
cd TLM_device_data_platform
git fetch origin fix/esp32-real-hardware-bringup
git switch --track origin/fix/esp32-real-hardware-bringup
git status --short
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements/server.txt '.[server]'
.venv/bin/python -m pip check
```

Требуется Python 3.11+. Если этот checkout использует локальные `.secrets/`,
исключить каталог из Git локально и проверить, что секреты не отслеживаются:

```bash
mkdir -p .secrets
chmod 700 .secrets
git ls-files -- .secrets
```

Добавить `.secrets/` в `.git/info/exclude` редактором; последняя команда должна
вывести пусто. Для полной настройки выбранного Supabase проекта, безопасного
создания admin DSN с `sslmode=verify-full` и CA из Dashboard см.
[проверенную процедуру Supabase](SUPABASE_BRINGUP_RU.md), разделы 2–7.
На новом проекте сначала проверить project ref и историю миграций:

```bash
npm ci
npx --no-install supabase login
npx --no-install supabase link --project-ref YOUR_DEV_PROJECT_REF
npx --no-install supabase migration list
npx --no-install supabase db push --dry-run
```

После сверки плана и **только для выбранного проекта** применить недостающие
миграции один раз: `npx --no-install supabase db push`, затем повторить
`migration list`. Нужна в том числе
`20261002010000_add_device_ingestion.sql`; старую migration/CI fixture не
переписывать. Для уже развёрнутой БД не выполнять `db reset` и не перезапускать
provisioning вслепую.

Если credentials ещё нет, после создания `.secrets/admin.secret.json` с
проверенным административным DSN выполнить:

```bash
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config .secrets/admin.secret.json --apply runtime \
  --pooler-project-ref YOUR_DEV_PROJECT_REF \
  --output .secrets/runtime.secret.json
.venv/bin/python -m tlm_device_data_platform.provision \
  --admin-config .secrets/admin.secret.json --apply device \
  --system-type esp32-hcsr04 \
  --output .secrets/esp32-hcsr04.secret.json
stat -c '%a %n' .secrets/*.secret.json
```

Runtime-файл нужен только API, device-файл содержит только UUID и token. CLI
создаёт файлы с правами `0600` до операции с БД; при неясном исходе COMMIT
сначала сверить БД, **не** удалять файлы и не повторять provisioning. Если
используется прямое PostgreSQL-подключение без Session pooler, опустить
`--pooler-project-ref` по инструкции Supabase.

## 4. Найти USB-порт, определить чип и установить MicroPython

Подключить ESP32 по USB (CH340 в проверенном стенде), закрыть serial monitor:

```bash
python3 -m venv .venv-device-tools
.venv-device-tools/bin/python -m pip install esptool mpremote
.venv-device-tools/bin/mpremote connect list
ls -l /dev/serial/by-id/
lsusb
```

В проверке порт был `/dev/ttyUSB0`; на другом компьютере он может быть иным.
Выбрать фактический `YOUR_SERIAL_PORT` и далее подставлять его явно:

```bash
.venv-device-tools/bin/python -m esptool --chip esp32 \
  --port YOUR_SERIAL_PORT read-mac
.venv-device-tools/bin/python -m esptool --chip esp32 \
  --port YOUR_SERIAL_PORT flash-id
```

Ожидается классический ESP32 и не менее 4 MiB flash для выбранного полного
образа. Сверить чип/flash с маркировкой платы. Скачать **ESP32_GENERIC
v1.29.0, полный `.bin`**, с
[официальной страницы MicroPython](https://micropython.org/download/ESP32_GENERIC/).
Не брать C3/S3 image или `.app-bin`; сверить опубликованный hash, если доступен.
Версия MicroPython ограничена совместимостью прошивки; специального pin
версии esptool нет.

`erase-flash` уничтожает старую прошивку, файлы и outbox. После явного решения
оператора и резервирования нужных данных выполнить:

```bash
.venv-device-tools/bin/python -m esptool --chip esp32 \
  --port YOUR_SERIAL_PORT erase-flash
.venv-device-tools/bin/python -m esptool --chip esp32 \
  --port YOUR_SERIAL_PORT write-flash 0x1000 /path/to/ESP32_GENERIC-v1.29.0.bin
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT exec \
  'import sys; print(sys.platform, sys.implementation.version)'
```

`0x1000` относится к полному образу для классического ESP32. Проверить
`esp32` и версию не ниже 1.29.0; проверенный образ сообщил `(1, 29, 0, '')`.
Если 1.29.0 уже установлена и файловая система нужна, стирание не требуется.

## 5. LAN, 2,4 ГГц, API и firewall

На Ubuntu узнать адрес интерфейса, SSID и частоту:

```bash
ip -4 addr show
nmcli -f IN-USE,SSID,FREQ,CHAN,RATE,SIGNAL,BARS dev wifi
nmcli -f SSID,FREQ,CHAN,SIGNAL dev wifi
```

Классический ESP32 использует совместимую сеть **2,4 ГГц**. В проверке 5 GHz
на 5220 MHz не подошла; рабочая сеть была на 2472 MHz, канал 13. Имена этих
сетей не являются конфигурацией проекта. Пример адресов 2026-10-03:
Ubuntu `10.100.102.3/24`, ESP32 `10.100.102.226`, подсеть
`10.100.102.0/24`; свои адреса определить заново. Проверить, что WLAN не
изолирует клиентов друг от друга.

По умолчанию API слушает только loopback. Для **изолированной лабораторной
LAN** запустить его на фактическом IP Ubuntu, оставив окно открытым:

```bash
.venv/bin/python -m tlm_device_data_platform.serve_api \
  --config .secrets/runtime.secret.json \
  --host YOUR_LAN_IP --port 8000 --allow-insecure-lan
```

Флаг явно разрешает HTTP без TLS на внешнем listener. Для production нужен
HTTPS с валидируемым сертификатом; флаг там не применять. Проверить listener
и доступность с Ubuntu:

```bash
ss -ltnp "sport = :8000"
curl -i http://YOUR_LAN_IP:8000/v1/telemetry
```

Ожидаемый ответ GET: `405 Method Not Allowed`, `Allow: POST`. Это доказывает
доступность endpoint с Ubuntu, **не** успешный POST с ESP32. Протокол требует
поле **`schema_version`: 1** (не `version`); неправильное имя давало 422.
Тело имеет форму `{"schema_version":1,"device_id":"YOUR_DEVICE_UUID",
"message_id":"YOUR_MESSAGE_UUID","stream_id":"YOUR_STREAM_UUID",
"sequence_no":1,"captured_at":null,"payload":{"distance_cm":123.45}}`.
При необходимости ручного POST использовать приватный credential безопасным
способом, не вставляя token в shell history или лог.

Если соединение с ESP32 не устанавливается, проверить UFW (может отсутствовать
или быть неактивным):

```bash
sudo ufw status verbose
```

При `active` и `Default: deny (incoming)` открыть **только нужную подсеть** для
временного лабораторного доступа:

```bash
sudo ufw allow from YOUR_LAN_SUBNET to any port 8000 proto tcp
```

Пример только для стенда 2026-10-03:
`sudo ufw allow from 10.100.102.0/24 to any port 8000 proto tcp`.
В том стенде до правила tcpdump видел повторные `ESP32 → Ubuntu:8000 SYN` без
`SYN-ACK`; после правила соединение проходило `SYN → SYN-ACK → ACK`.
Если нужно, диагностировать только сетевые метаданные:

```bash
sudo tcpdump -ni YOUR_WIFI_INTERFACE host YOUR_ESP32_IP and port 8000
```

Не отключать firewall и не открывать 8000 для всего Интернета. После теста
посмотреть `sudo ufw status numbered` и удалить **именно созданное** правило,
например `sudo ufw delete allow from YOUR_LAN_SUBNET to any port 8000 proto tcp`.
Остановить лабораторный API после проверки или заменить HTTPS listener согласно
плану развёртывания.

## 6. Конфигурация и копирование файлов на ESP32

Использовать [config.example.json](../../firmware/esp32_micropython/config.example.json)
как шаблон; создать `firmware/esp32_micropython/config.secret.json` локальным
редактором. Вставить **только** UUID/token из device-файла, реальные Wi-Fi
credentials и адрес TLM API. Не переносить на плату admin/runtime DSN.
Фрагмент для лаборатории:

```json
{
  "TLM_DEVICE_ID": "YOUR_PROVISIONED_DEVICE_UUID",
  "TLM_DEVICE_TOKEN": "YOUR_PROVISIONED_DEVICE_TOKEN",
  "TLM_API_URL": "http://YOUR_LAN_IP:8000/v1/telemetry",
  "WIFI_SSID": "YOUR_2_4_GHZ_SSID",
  "WIFI_PASSWORD": "YOUR_WIFI_PASSWORD",
  "TRIG_PIN": 26,
  "ECHO_PIN": 27,
  "OUTBOX_CAPACITY": 512,
  "OUTBOX_PATH": "/tlm-outbox",
  "CA_FILE": "ca.pem",
  "NTP_HOST": "pool.ntp.org",
  "ALLOW_INSECURE_HTTP": true
}
```

`ALLOW_INSECURE_HTTP=true` допускается только для приватного IPv4 в
изолированной лаборатории. В production использовать HTTPS URL,
`ALLOW_INSECURE_HTTP=false` и доверенный CA для **TLM API**, не автоматически
CA PostgreSQL. Сохранить права и проверить Git:

```bash
chmod 600 firmware/esp32_micropython/config.secret.json
git status --short
git check-ignore firmware/esp32_micropython/config.secret.json
```

Не печатать конфигурацию, token и пароль в терминал, чаты, документацию и
Serial log. После проверки порта копировать модули (без `main.py`):

```bash
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT fs cp \
  firmware/esp32_micropython/tlm_core.py \
  firmware/esp32_micropython/hcsr04.py \
  firmware/esp32_micropython/tlm_http.py \
  firmware/esp32_micropython/tlm_runtime.py \
  firmware/esp32_micropython/tlm_net_worker.py :
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT fs cp \
  firmware/esp32_micropython/config.secret.json :config.secret.json
```

Только для HTTPS отдельно скопировать доверенный CA API как `:ca.pem`. Для
TLS нужны правдоподобные часы; если требуется, **до копирования `main.py`**:

```bash
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT rtc --set
```

## 7. Проверить датчик до автозапуска

При включённом датчике и неподвижной плоской цели выполнить:

```bash
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT exec \
  'from hcsr04 import HCSR04; s = HCSR04(26, 27); print(s.read())'
```

Ожидается `{'distance_cm': <реальное значение>}`. В проверке после исправления
делителя было `12.12 cm`, затем встречались 8.55, 31.50, 55.45, 89.16 и
217.83 cm. Не подменять показания генератором и не сглаживать их ради теста.

Если `SensorReadError: No valid echo`, проверить 5 V между VCC/GND датчика,
общий GND, GPIO26 → TRIG, **обе ветви** делителя и его выход → GPIO27,
ориентацию/расстояние цели. `machine.time_pulse_us(...)= -2` по
[MicroPython 1.29.0](https://docs.micropython.org/en/v1.29.0/library/machine.html)
означает timeout ожидания начала импульса. При исходно неверном делителе в
этом стенде наблюдались `echo_idle=0`, `pulse_us=-2`; после переподключения
появились настоящие расстояния. Отсутствие эха — ошибка измерения, **не 0 cm**.

## 8. Последним установить `main.py`, перезапустить и увидеть ACK

После успешного ручного теста:

```bash
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT fs cp \
  firmware/esp32_micropython/main.py :main.py
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT reset
.venv-device-tools/bin/mpremote connect YOUR_SERIAL_PORT repl
```

`main.py` загружается автоматически. **Не выполнять** `import main;
main.start()` поверх уже запущенной программы. После прерывания REPL для
чистого опыта выполнить reset и дать одному autostart работать. При нескольких
runtime встречались перемежающиеся номера sequence, `TimeoutError`,
`OSError(-203)`, `MemoryError`; чистый reset устранил это состояние на стенде.
Новый runtime-guard отклоняет повторный запуск, не стирая outbox.

Ожидаемые строки:

```text
sample_persisted 1
delivery_ack
sample_persisted 2
delivery_ack
```

`sample_persisted` означает запись в flash **до** передачи; `delivery_ack` —
проверенный ответ API и удаление точного файла очереди. Возможное
`sensor_error: no valid distance; sample omitted` не создаёт фиктивного нуля.
`delivery_error timeout`, `delivery_error os_error -203`, `delivery_error eof`
или `delivery_error invalid_response` не содержат секретов: очередь остаётся,
действует backoff. Потерянный ACK может означать, что COMMIT уже прошёл:
повторяется тот же `message_id`, API отвечает `200 duplicate`, затем клиент
подтверждает/удаляет запись. **Не очищать outbox** при timeout.

### Быстрая диагностика

| Симптом | Что проверить |
| --- | --- |
| USB permission denied / порт пропал | `mpremote connect list`, `ls -l /dev/serial/by-id/`, права пользователя на фактический порт; закрыть другой serial monitor |
| `SensorReadError`, `pulse_us=-2` | Питание 5 V, общий GND, GPIO26/27, обе ветви делителя, цель; ECHO не подключать напрямую |
| Нет Wi-Fi | Частоту SSID через `nmcli`; для классического ESP32 нужна совместимая сеть 2,4 ГГц, проверить пароль локально без вывода |
| `delivery_error timeout`, ESP32 посылает SYN без ответа | `ss`, IP API-хоста, UFW, subnet rule, клиентская изоляция WLAN; не менять timeout наугад |
| `delivery_error os_error -203` | Сначала исключить второй runtime, проверить DNS/сеть и reset; код ошибки сам по себе не доказывает причину |
| `405` на GET | Нормальная проверка reachability; телеметрию проверять POST и строкой БД |
| `422` на POST | Проверить строгое `schema_version`, UUID/sequence/payload по [протоколу v1](PROTOCOL_V1.md) |
| Есть строка в БД, но файл остаётся в outbox | Возможен потерянный ACK; оставить точный пакет для повтора и `200 duplicate` |
| Перемежаются номера sequence / `MemoryError` | Остановить ручные вызовы, сделать чистый reset, дождаться одного autostart; не форматировать flash |

### Граница лаборатории и production

Лабораторный `--allow-insecure-lan` плюс `ALLOW_INSECURE_HTTP=true` передаёт
device token по HTTP в частной сети; это сознательное исключение только для
изолированного испытания. Рабочий deployment требует HTTPS endpoint TLM API,
проверки имени и CA на ESP32 и отдельной проверки часов/сертификата. API →
Supabase использует ограниченную PostgreSQL-роль и `sslmode=verify-full` с
доверенным CA по [процедуре Supabase](SUPABASE_BRINGUP_RU.md). Ни один DSN или
DB-пароль не должен оказаться в firmware. Этот аппаратный сеанс не проверял
production HTTPS на плате.

## 9. Проверить Supabase и завершить лабораторный сеанс

В SQL Editor **выбранного development-проекта** выполнить, подставив только
UUID зарегистрированного устройства:

```sql
select device_id, message_id, sequence_no, received_at, payload
from tlm.telemetry_messages
where device_id = 'YOUR_DEVICE_UUID'::uuid
order by received_at desc
limit 10;
```

В проверке 2026-10-03 свежие строки от платы включали sequence 13–16 со
значениями `31.52`, `31.52`, `31.52`, `31.5 cm`; ранее sequence 7 имел
`217.83 cm`. Ручной POST корректного payload через TLM API давал HTTP 201
`stored`; payload с `"version":1` вместо `"schema_version":1` давал 422.
Это исторические результаты стенда, не результаты запуска по этой инструкции.

Критерии завершения:

1. Датчик локально возвращает физическое расстояние, которое меняется при
   перемещении цели; ошибка эха не становится нулём.
2. ESP32 подключён к совместимому Wi-Fi 2,4 ГГц и достигает TLM API.
3. Есть `sample_persisted`, затем `delivery_ack`; подтверждённый файл удалён.
4. В реальной Supabase появились свежие строки именно этого `device_id` с
   меняющимся `payload.distance_cm`.
5. На плате нет PostgreSQL/Supabase credentials; после reset работает один
   автоматический runtime без ручного `main.start()`.

Оставить API работающим, пока устройство должно доставлять данные. После
лаборатории закрыть listener и узкое UFW-правило или перейти на HTTPS.
Не удалять outbox/credentials при неразобранных pending-записях. Долгий offline,
power loss, ресурс flash, варианты плат/датчиков, fleet scale и production HTTPS
на физической плате требуют отдельных испытаний. 10 секунд — номинальный
интервал, не жёсткая гарантия реального времени.
