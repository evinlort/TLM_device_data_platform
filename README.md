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

- [Полное руководство TLM API: endpoints, аутентификация, отправка и ошибки](docs/device_ingestion/API_GUIDE_RU.md).
- [Tutorial регистрации и входа пользователей — дополнение session-user-access](docs/device_ingestion/AUTHENTICATION_TUTORIAL_RU.md).
- [Tutorial Dashboard: экраны, роли и учебные сессии — дополнение session-user-access](docs/device_ingestion/DASHBOARD_TUTORIAL_RU.md).
- [Протокол v1 и границы пилота](docs/device_ingestion/PROTOCOL_V1.md).
- [Установка, SQL, provisioning, API и Linux-агент](docs/device_ingestion/STAND_SETUP.md).
- [Практический запуск с Supabase: миграции, TLS, provisioning, timeout и demo-запись](docs/device_ingestion/SUPABASE_BRINGUP_RU.md).
- [ESP32: схема HC-SR04, USB, MicroPython и приёмка](firmware/esp32_micropython/README.md).
- [ESP32: полный запуск физического стенда до строки Supabase](docs/device_ingestion/ESP32_REAL_HARDWARE_BRINGUP_RU.md).
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
компилирует шесть MicroPython-модулей закреплённым mpy-cross 1.29.0.

Старые `simulation.py`, `telemetry_fixture.py` и `local_integration.py` остаются
CI-fixtures. Они не используются как production telemetry contract.

## Проверено и ограничения

**Операторская проверка 02.10.2026:** программный путь `Linux demo → локальный TLM API
→ удалённый Supabase → ACK` подтверждён. Порядок запуска и диагностика описаны в
[практическом руководстве](docs/device_ingestion/SUPABASE_BRINGUP_RU.md). Найденное
там исправление Linux HTTP timeout `5 → 15 s` теперь включено в исходники вместе
с regression-тестами завершения агента. Это исторический результат 02.10.2026.

**Физическая проверка 03.10.2026:** ESP32-D0WD-V3 с MicroPython 1.29.0 и
HC-SR04 на GPIO26/GPIO27 через делитель передал настоящие расстояния по Wi-Fi
2,4 ГГц в TLM API; свежие строки подтверждены в удалённой Supabase. Полный
порядок и границы проверки — в [руководстве](docs/device_ingestion/ESP32_REAL_HARDWARE_BRINGUP_RU.md).
`demo_sensor:read` по-прежнему возвращает только тестовые показания. Не
проверены все варианты ESP32/HC-SR04, production HTTPS на плате, длительный
ресурс flash, устойчивость к потере питания, долгий offline и fleet scale.
Нет dashboard, current_state, school/student isolation и управления оборудованием.

Секреты не коммитить. Required CI не подключается к remote Supabase и не требует
физической платы. История исходной CI-подготовки сохранена в `docs/ci/`.
PR #2 с ingestion v1 и PR #3 с ESP32-клиентом объединены в `main`.
