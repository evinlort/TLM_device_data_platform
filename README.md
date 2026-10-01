# TLM Device Data Platform

Лабораторный приём телеметрии от устройств с независимым TLM API и заменяемым
PostgreSQL storage adapter. Supabase — текущий PostgreSQL provider, не часть
протокола устройства.

```text
Linux sensor adapter / ESP32 MicroPython + HC-SR04
  → номинальное измерение каждые 10 секунд
  → постоянная очередь (Linux: SQLite; ESP32: flash files)
  → HTTPS POST /v1/telemetry
  → проверка token и device_id
  → PostgreSQL transaction / COMMIT
  → подтверждение устройству
```

## Начать здесь

- [Протокол v1 и границы пилота](docs/device_ingestion/PROTOCOL_V1.md).
- [Установка, SQL, provisioning, API и Linux-агент](docs/device_ingestion/STAND_SETUP.md).
- [ESP32: схема HC-SR04, USB, MicroPython и приёмка](firmware/esp32_micropython/README.md).
- [ESP32: TDD и границы проверки](docs/device_ingestion/ESP32_IMPLEMENTATION.md).
- [Ход реализации backend и Linux-агента](docs/device_ingestion/IMPLEMENTATION.md).
- [SQL-миграция реальных устройств](supabase/migrations/20261002010000_add_device_ingestion.sql).

## Основные модули

| Модуль | Назначение |
| --- | --- |
| `telemetry_v1.py` | Версионированный JSON contract и validation |
| `ingestion.py` | HTTP endpoint, ограничение размера, обработка ошибок |
| `postgres_ingestion.py` | Authentication, транзакция, идемпотентность |
| `edge_agent.py` | Linux: независимые сбор и доставка, SQLite-очередь |
| `provision.py` | Явная регистрация runtime LOGIN и устройства |
| `serve_api.py` | Запуск сервера с приватной конфигурацией |
| `firmware/esp32_micropython/` | ESP32: HC-SR04, flash outbox, HTTPS client |

## Проверки

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -c requirements/test.txt -c requirements/server.txt '.[test]'
.venv/bin/python -m pytest -m 'not database'
```

Полный suite требует одноразовую локальную Supabase/PostgreSQL и
`TLM_TEST_ADMIN_DSN`. GitHub Actions поднимает её автоматически и выполняет
настоящие HTTP → PostgreSQL tests под ограниченным LOGIN. Новые ESP32 host tests
используют те же исходники, которые загружаются по USB. Отдельный workflow
компилирует пять MicroPython-модулей закреплённым mpy-cross 1.29.0.

Старые `simulation.py`, `telemetry_fixture.py` и `local_integration.py` остаются
CI-fixtures. Они не используются как production telemetry contract.

## Что не заявлено готовым

Код драйвера HC-SR04 добавлен, но аппаратная проверка датчика, GPIO, Wi-Fi/TLS
на реальной ESP32 и hosted dev deployment ещё не выполнены. Host tests и
bytecode compilation не заменяют эту проверку. `demo_sensor:read` возвращает
только явно тестовые показания. Нет dashboard, current_state, school/student
isolation, управления оборудованием и гарантий production fleet scale.

Секреты не коммитить. Required CI не подключается к remote Supabase и не требует
физической платы. История исходной CI-подготовки сохранена в `docs/ci/`.
Новая ESP32-ветка и её PR зависят от пока не объединённого PR #2.
