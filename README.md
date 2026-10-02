# TLM Device Data Platform

Лабораторный приём телеметрии от устройств с независимым TLM API и заменяемым
PostgreSQL storage adapter. Supabase — текущий PostgreSQL provider, не часть
протокола устройства.

```text
Linux sensor adapter
  → измерение каждые 10 секунд
  → постоянная SQLite-очередь
  → HTTPS POST /v1/telemetry
  → проверка token и device_id
  → PostgreSQL transaction / COMMIT
  → подтверждение устройству
```

## Начать здесь

- [Протокол v1 и границы пилота](docs/device_ingestion/PROTOCOL_V1.md).
- [Установка, SQL, provisioning, API и агент](docs/device_ingestion/STAND_SETUP.md).
- [Ход реализации и подтверждённые результаты](docs/device_ingestion/IMPLEMENTATION.md).
- [SQL-миграция реальных устройств](supabase/migrations/20261002010000_add_device_ingestion.sql).

## Основные модули

| Модуль | Назначение |
| --- | --- |
| `telemetry_v1.py` | Версионированный JSON contract и validation |
| `ingestion.py` | HTTP endpoint, ограничение размера, обработка ошибок |
| `postgres_ingestion.py` | Authentication, транзакция, идемпотентность |
| `edge_agent.py` | Независимые сбор и доставка, постоянная очередь |
| `provision.py` | Явная регистрация runtime LOGIN и устройства |
| `serve_api.py` | Запуск сервера с приватной конфигурацией |

## Проверки

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -c requirements/test.txt -c requirements/server.txt '.[test]'
.venv/bin/python -m pytest -m 'not database'
```

Полный suite требует одноразовую локальную Supabase/PostgreSQL и
`TLM_TEST_ADMIN_DSN`. GitHub Actions поднимает её автоматически и выполняет
настоящие HTTP → PostgreSQL tests под ограниченным LOGIN.

Старые `simulation.py`, `telemetry_fixture.py` и `local_integration.py` остаются
CI-fixtures. Они не используются как production telemetry contract.

## Что не заявлено готовым

Физический sensor driver, hosted dev deployment и аппаратная приёмка не
подменяются программным примером. `demo_sensor:read` возвращает только явно
тестовые показания. Нет ESP32 firmware, dashboard, current_state, school/student
isolation, управления оборудованием и гарантий production fleet scale.

Секреты не коммитить. Required CI не подключается к remote Supabase и не требует
физической платы. История исходной CI-подготовки сохранена в `docs/ci/`.
