# Телеметрия учебных сессий — v2

`POST /v2/telemetry`, JSON, `Authorization: Bearer <device-token>`.
Все поля, ограничения и ACK/error semantics v1 сохраняются. Отличия:
`schema_version=2` и обязательный `session_id` — UUID string либо null.
Неизвестные поля по-прежнему отклоняются. Context revision в packet не передаётся.

Перед первым измерением клиент получает:

```text
GET /v2/devices/{device_id}/context
Authorization: Bearer <device-token>
```

Ответ содержит ровно device_id, session_id, revision (неотрицательный bigint).
Credential проверяется так же, как при ingestion; чужой device_id даёт 403.
Desired context первоначально null/revision=0. Start назначает сессию и увеличивает
revision; finish освобождает устройство и снова увеличивает revision.

Контекст сохраняется локально. Без успешного первого ответа измерений v2 нет.
Offline использует сохранённый контекст; после восстановления связи контекст
обновляется перед новыми измерениями. Linux обновляет независимо от датчика,
ESP32 сохраняет последовательную отправку. Старые queue bytes/IDs/stream/session
никогда не изменяются. Новая сессия создаёт новый stream для новых измерений.
Выбор endpoint при replay определяется schema_version исходного packet, поэтому
существующая очередь v1 может доставляться вместе с v2.

Ненулевой session_id принимается только у устройства, которое назначено начатой
сессии. Историческое назначение сохраняется после завершения: поздние пакеты
допустимы. Время измерения и получения не определяют принадлежность. Null означает
сохранённый клиентом контекст без группы; сервер не подставляет desired сессию.

Идемпотентность включает schema_version и session_id. Идентичный повтор получает
200/duplicate; изменение session_id известного message_id — 409. v1 всегда
остаётся без сессии и виден только approved manager/admin. v2 с null также виден
только этим ролям. Student/teacher читают только разрешённую session history.

Это программно проверенный session contract. Он не добавляет команды датчикам,
current_state, гарантии flash/power loss, retention или hardware validation v2.
