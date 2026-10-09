# TLM Dashboard: руководство пользователя

Dashboard — браузерное рабочее место для доступа к лабораторной телеметрии,
учебным сессиям и административным настройкам. Это руководство описывает
все его разделы, кнопки, права, обычные действия и диагностику.

**Доступность:** описана реализация `feat/session-user-access`, snapshot
`480d0cdf6f533c025f781193f3ce7b1ed4ea5099`, проверенная по исходникам
09.10.2026. На момент подготовки `main` находится на commit
`3864893dc5d76a9a5f011e1a3a60a115953413d6` и не содержит Dashboard.
Tutorial публикуется как документация в `main`; для выполнения действий
нужен сервер с установленным дополнением, его migrations и конфигурацией.
Наличие документа не подтверждает удалённое развёртывание.

Названия экранов и кнопок ниже приведены **точно на английском**, как в UI.
Порядок регистрации, входа, восстановления сессии и выхода — в
[tutorial аутентификации](AUTHENTICATION_TUTORIAL_RU.md).
Отправка сообщений устройством — в [руководстве API](API_GUIDE_RU.md).

## Содержание

1. [Назначение и подготовка](#1-назначение-и-подготовка)
2. [Какие разделы доступны каждой роли](#2-какие-разделы-доступны-каждой-роли)
3. [Общие элементы интерфейса](#3-общие-элементы-интерфейса)
4. [Первичная настройка администратором](#4-первичная-настройка-администратором)
5. [Teacher: создание, запуск и завершение сессии](#5-teacher-создание-запуск-и-завершение-сессии)
6. [Student: просмотр своих измерений](#6-student-просмотр-своих-измерений)
7. [Manager и admin: общая история](#7-manager-и-admin-общая-история)
8. [Как читать Device context](#8-как-читать-device-context)
9. [Справочник экранов и API](#9-справочник-экранов-и-api)
10. [Ошибки и ограничения](#10-ошибки-и-ограничения)
11. [Учебная приёмка и источники](#11-учебная-приёмка-и-источники)

## 1. Назначение и подготовка

Dashboard открывается по `/` origin TLM API, например
`https://tlm-api.example.org`. Этот адрес — заглушка: получите фактический
URL у оператора. UI assets и API обслуживаются одним серверным процессом;
отдельный frontend URL для этой реализации не требуется.
Supabase Studio и TLM Dashboard — разные интерфейсы.

В Dashboard можно:

- видеть доступные учебные сессии и читать их историю;
- создавать группу с несколькими student accounts и устройствами;
- запускать и завершать сессии при наличии прав;
- проверять, пришёл ли пакет с назначенной принадлежностью;
- управлять школами, ролями, статусами и школьными привязками устройств как admin.

Dashboard не измеряет sensor values, не регистрирует device credentials
и не запускает hardware driver. Он показывает уже записанную телеметрию.
Для групповой истории устройства должны использовать v2: message содержит
сохранённый `session_id`. Сообщения v1 остаются без учебной сессии.

Перед началом должны быть подготовлены сервер дополнения, approved аккаунт
с нужной ролью и для учебного сценария — школа, approved students,
активное зарегистрированное устройство и его клиент v2.
Оператор отвечает за firmware, сеть, token, CA и sensor driver.
Эти настройки не передаются через форму пользовательского входа.

Если аккаунт ещё pending, пройдите одобрение по
[инструкции входа](AUTHENTICATION_TUTORIAL_RU.md#3-регистрация-и-первый-вход-в-браузере).
Если сервер отвечает `404` по `/`, оператор проверяет установленную версию
и конфигурацию. Health `alive` не доказывает наличие UI или готовность БД/Auth.

## 2. Какие разделы доступны каждой роли

Все права таблицы предполагают статус **approved**. Pending/disabled
пользователь видит только соответствующее сообщение об отсутствии доступа.

| Действие/раздел | student | teacher | manager | admin |
| --- | --- | --- | --- | --- |
| Sessions | Только свои участия | Все разрешённые сессии своей школы | Все школы | Все школы |
| Open: session history | Свои сессии | Своя школа | Все школы | Все школы |
| Create session / Edit roster / Start / End | Нет | Своя школа | Нет | Все школы |
| Device context | Нет | Устройства своей школы | Нет | Все устройства в области admin |
| All telemetry | Нет | Нет | Да | Да |
| User access | Нет | Нет | Нет | Да |
| Schools / Add school | Нет | Нет | Нет | Да |
| Device school bindings | Нет | Нет | Нет | Да |

Student видит сессию по участию, а не просто по совпадению школы.
Teacher может управлять разрешёнными сессиями школы, а не только созданными
им самим. Manager — роль чтения: она не запускает занятия и не одобряет людей.
Admin работает глобально согласно правилам дополнения.

UI скрывает недоступные controls, а сервер дополнительно проверяет права
в БД для каждого запроса. Изменение URL, user UUID или HTML в браузере
не даёт доступа к чужой истории. При смене роли нажмите **Refresh**,
чтобы интерфейс перечитал профиль.

## 3. Общие элементы интерфейса

### 3.1. Шапка, профиль и уведомления

Название страницы — **Telemetry workspace**. В шапке показывается email
вошедшего человека; toolbar выводит role/status, например `teacher · approved`.
Ошибки API отображаются текстом в области уведомлений над workspace.

Для нового аккаунта показано **Awaiting administrator approval**,
для заблокированного — **Access disabled**. Перерегистрация не заменяет
одобрение или восстановление доступа.

### 3.2. Refresh и Log out

**Refresh** перечитывает профиль, Sessions, доступные roster options,
Device context и admin sections. В этой версии нет автоматического polling:
после прихода новых сообщений или действий другого пользователя
обновите нужное представление вручную.

Открытая **Telemetry history** не перечитывается только от нажатия toolbar
Refresh. Для обновления конкретной истории нажмите **Open** у сессии снова;
для общей — **All telemetry**. Это также возвращает paging на первую страницу.
Обновление данных/списков может сбросить несохранённый выбор в форме:
сохраните нужный draft roster перед Refresh.

**Log out** завершает текущий пользовательский сеанс.
Он не завершает активные учебные сессии и не останавливает устройства.
Auth errors и особенности remote revocation описаны в
[tutorial аутентификации](AUTHENTICATION_TUTORIAL_RU.md#3-регистрация-и-первый-вход-в-браузере).

### 3.3. Таблица Sessions

| Колонка | Что означает |
| --- | --- |
| Session | Название учебной сессии |
| Status | `draft`, `active` или `ended` |
| Students | Число участников в roster, не число вошедших сейчас пользователей |
| Devices | Число назначенных устройств, не число online-устройств |
| Actions | Open и разрешённые lifecycle/roster controls |

При отсутствии доступных сессий показано **No sessions available**.
Это может означать отсутствие групп или отсутствие разрешённого участия.
Sessions содержит доступные сессии разных статусов, включая draft;
student может увидеть назначенный draft с пока пустой историей.

Список упорядочен по `started_at` убывающе с ещё не начатыми draft впереди
и UUID как дополнительным порядком. UI не содержит search/filter или
pagination этого списка. Порядок истории сообщений другой — раздел 6.

## 4. Первичная настройка администратором

### 4.1. Создайте школу

Войдите как approved admin. В разделе **Schools**:

1. Введите согласованное название в **School name**.
2. Нажмите **Add school**.
3. Убедитесь, что школа появилась в списке.

Название непустое после удаления крайних пробелов, не длиннее 200 символов.
Перед созданием проверьте уже существующие записи: API не обещает уникальность
школьного названия. UI не предоставляет rename/delete school.

### 4.2. Одобрите участников и преподавателя

Каждый будущий student/teacher сначала регистрируется.
При отключённом email confirmation заявленный email не подтверждает личность.
До выдачи роли и одобрения независимо проверьте человека по заранее известному
доверенному каналу и сопоставьте его authenticated `user_id` с pending-профилем
по [инструкции проверки аккаунта](AUTHENTICATION_TUTORIAL_RU.md#41-одобрите-профиль).
До такой проверки оставьте статус `pending` и не назначайте роль.
В **User access** найдите нужный email, задайте **Role**, **School**,
**Status: approved**, нажмите **Save**, дождитесь **Saved**.
Для student и teacher школа обязательна. Попросите человека нажать Refresh
или войти заново.

Пошаговое управление pending/disabled и правильные сочетания полей — в
[административном разделе Auth tutorial](AUTHENTICATION_TUTORIAL_RU.md#4-одобрение-и-блокировка-администратором).
Teacher не может включить в roster ещё не одобренного пользователя
или student другой школы.

### 4.3. Привяжите зарегистрированное устройство к школе

Оператор сначала регистрирует устройство отдельным provisioning CLI
и передаёт token самому устройству. Dashboard не создаёт и не раскрывает token.

В **Device school bindings**:

1. Найдите устройство по **system_type и полному device UUID**.
2. Выберите нужную **Device school**.
3. Нажмите **Save binding**.
4. Проверьте обновлённый список и доступность устройства в roster нужной школы.

`Unassigned` означает отсутствие школьной привязки. Такое устройство
не подходит для групповой сессии этой школы. Неактивное устройство
также не появляется среди разрешённых choices формы.
UI не содержит toggle для device `is_active`; это операторская настройка.

Нельзя сменить школу устройства, пока оно занято активной сессией:
сервер возвращает conflict. Сначала выясните текущее назначение
и согласованно завершите занятие. Перепривязка не переносит
старые сообщения в другие исторические сессии.

## 5. Teacher: создание, запуск и завершение сессии

Для учебного примера используйте согласованную TEST-школу, TEST-аккаунты
и TEST-устройство. Название группы, например **TEST tutorial group**,
маркирует программную пробу. Сам Dashboard не создаёт synthetic readings.
Учебные сообщения от software client не являются hardware measurements.

### 5.1. Создайте draft

Войдите как approved teacher своей школы или как admin.
В разделе **Create session** заполните:

| Поле | Что выбрать |
| --- | --- |
| Session name | Название группы, 1–200 символов; не только пробелы |
| Session school | Школу группы, разрешённую вашей роли |
| Students | Одного или нескольких approved students этой школы |
| Devices | Одно или несколько активных зарегистрированных устройств этой школы |

Для нескольких значений используйте Ctrl/Command или поддерживаемый
браузером способ multiple selection. API допускает 1–200 student IDs
и 1–200 device IDs. При смене школы choices пересчитываются;
выберите состав заново.

Нажмите **Create draft**. При успехе новая строка появляется в Sessions
со статусом **draft** и нужными counts. Draft ещё не назначает устройство
активной группе. Проверьте состав до запуска.

Пустые списки не принимаются. Если student/device отсутствует в choices,
проверьте approval, роль, школьную привязку и active flag с admin/operator.
Не подставляйте UUID другой школы для обхода формы.

### 5.2. Измените состав до старта

У draft нажмите **Edit roster**. Форма меняется на **Edit draft roster**,
а submit button — на **Save roster**.

Измените выбор Students/Devices, оставив хотя бы одно значение каждого типа.
Нажмите **Save roster**. Возврат к обычной форме и перечитанный список
подтверждают завершение UI-операции. **Cancel edit** отменяет локальное
редактирование, а не удаляет draft.

Session name и Session school в этом режиме disabled: UI изменяет только
roster. Не предусмотрены rename session, delete draft или cancel session.
Если потребуется другой школьный/именованный сценарий, согласуйте создание
новой записи; старая не исчезает автоматически.

### 5.3. Запустите сессию

У нужного draft нажмите **Start** и дождитесь статуса **active**.
Сервер заново проверяет участников и устройства, фиксирует состав
и назначает device context. Одно устройство может занимать только
одну active session одновременно.

```text
draft -> Start -> active -> End -> ended
```

После успешного старта:

- roster фиксирован: Edit roster исчезает;
- устройство получает desired session при следующем получении context;
- сессия может пока не содержать ни одного packet;
- `Awaiting packet` означает отсутствие полученного v2 сообщения этой группы.

**Start не включает датчик и не гарантирует online-связь.** Клиент устройства
должен уже работать и использовать protocol v2. Контекст запрашивается по
`GET /v2/devices/{device_id}/context` с device token. К Dashboard cookies
эта операция отношения не имеет.

При `409` проверьте, не занято ли устройство другой active session,
не изменились ли роли/школы/active flags между созданием и стартом
и не запустил ли другой человек эту запись. Нажмите Refresh и сверяйте
фактическое состояние перед повтором: Start не является идемпотентным retry.

### 5.4. Убедитесь в доставке

Откройте **Device context** и найдите UUID устройства. Нажмите Refresh
после ожидаемой доставки. При наличии сообщения группы значение
**Delivery evidence** меняется с **Awaiting packet** на **Packet confirmed**.

Затем нажмите **Open** у нужной сессии. В **Telemetry history**
должны появиться её разрешённые сообщения. Сообщение без группы или v1
не попадёт в её историю только из-за времени поступления.

Если подтверждения нет, проверьте с оператором endpoint v2, device token,
сохранённый context, сеть, outbox и ACK. Не удаляйте pending очередь
и не переписывайте session ID старого пакета ради появления строки.

### 5.5. Завершите занятие и создайте новую группу

У active session нажмите **End**. При успехе статус становится **ended**,
активное назначение устройства освобождается, desired context становится
без группы. История и roster завершённой сессии сохраняются.

End не останавливает sensor driver. Offline-клиент может ещё использовать
последний сохранённый context, а сообщения старой очереди остаются
приписаны исходной сессии. Дополнение принимает допустимые поздние сообщения
завершённой группы; поэтому её история может пополняться после End.

Ended нельзя снова Start, а состав нельзя редактировать. Для следующей
группы создайте **новую draft**, выберите новый состав, Start и дождитесь
Packet confirmed именно для нового назначения. Устройство может использоваться
повторно после освобождения; его credential не нужно менять ради новой группы.

## 6. Student: просмотр своих измерений

1. Войдите approved student account.
2. Найдите свою сессию в **Sessions**.
3. Нажмите **Open** в её строке.
4. Прочитайте **Telemetry history** и при необходимости перейдите
   по **Next**/**Previous**.

Student читает **все сообщения разрешённой сессии**, а не только строки
одного «персонального датчика». Привязка сообщения к конкретному ученику
внутри группы не реализована. Start/End, roster editing, Device context
и User access этому пользователю не предоставляются.

### 6.1. Колонки Telemetry history

| Колонка | Значение |
| --- | --- |
| Device | UUID устройства, отправившего сообщение |
| Captured | Время измерения, сообщённое устройством; `Unsynchronized` при `null` |
| Received | Время первой вставки в БД |
| Readings | Все пары sensor name/value из payload |

Отсутствие capture time не означает отсутствие показания.
ESP32-клиент выбранного пилота отправляет `captured_at: null`.
Единицы согласует оборудование: UI не переводит их автоматически
и не рисует графики физических диапазонов.

В одной строке — одно сообщение, в Readings может быть несколько sensors.
Повтор с `200 duplicate` не добавляет новую строку истории.
UI не выводит message ID/schema version/stream position отдельными columns;
полный JSON при наличии прав доступен через API.

### 6.2. Порядок, страницы и обновление

История упорядочена по `received_at`, затем device UUID и message UUID
**по возрастанию**. Первая страница содержит более ранние вставки,
а не автоматически последние readings. Размер UI page — 50 сообщений.
**Next** включается при следующей странице, **Previous** — при ненулевом offset.

API допускает limit 1–200 и offset 0–2147483647; возвращает `items`
и `next_offset`, где `null` означает конец страницы. UI использует limit=50
и не предлагает отдельную настройку page size.
Это offset pagination без snapshot: при изменении истории набор страниц
не закреплён как неизменный экспорт.

**No telemetry available** означает пустой результат выбранной страницы.
У новой draft/active session это нормально до первого подходящего v2 packet.
После ожидаемого поступления нажмите **Open** снова и при необходимости
перейдите дальше к новым вставкам. Общий Refresh не перезагружает
уже открытую таблицу истории автоматически.

### 6.3. Если сессия не видна

Проверьте email/роль/status в шапке. Попросите teacher проверить student UUID
в roster. Школьное членство без участия не делает сессию доступной student.
Если roster уже started, его не расширяют: для нового состава нужна новая группа.

Недоступный session history endpoint может вернуть `404 Session unavailable`,
не раскрывая чужую запись. Не трактуйте такой ответ как доказательство,
что сессия вообще не существует в системе.

## 7. Manager и admin: общая история

Approved manager/admin видят кнопку **All telemetry** у Sessions.
Она открывает историю всех разрешённых им сообщений с теми же четырьмя
columns и paging. В неё входят:

- v2 сообщения учебных сессий;
- v2 сообщения с `session_id: null`;
- сохранённые v1 сообщения без сессии.

Student/teacher не видят общий поток и не получают group-less messages
через свою session history. Учебный packet автоматически не принадлежит
активной группе только по текущему времени: membership берётся из envelope.

Manager может Open конкретную сессию, но не получает teacher/admin controls.
Admin также работает с User access, Schools и Device school bindings.
Общая UI-таблица не содержит отдельной колонки session ID; для проверки
исходной принадлежности используйте permitted API JSON или операторскую сверку.
Нет UI export в CSV, date range filter, charts или live sensor display.

## 8. Как читать Device context

Этот раздел видят teacher/admin. Он описывает **назначение и свидетельство
доставки**, а не текущие значения sensors, online status или command execution.

| Колонка | Значение |
| --- | --- |
| Device | system type и UUID, по которому нужно сверить оборудование |
| Desired session | Сессия, которую сервер сейчас назначил устройству, либо `No session` |
| Delivery evidence | `Awaiting packet`, `Packet confirmed` или `No group requested` |
| Last confirmed group | Последняя подтверждённая ненулевая группа по историческому context revision, либо `No group confirmed` |
| Last received session | Принадлежность последнего вставленного v2 packet и received timestamp, либо `No v2 packet received` |

**Packet confirmed** означает, что сервер уже получил v2 сообщение
этого устройства с desired session ID. Это не проверка физической точности
измерения и не доказательство, что устройство всё ещё online.

**Last confirmed group** выбирается по максимальной исторической revision
назначения среди групп, для которых есть v2 packet. В UI revision не показана
отдельной колонкой. **Last received session** выбирается по порядку вставки
packet, поэтому она может относиться к более старой группе.

### 8.1. Пример смены группы и позднего replay

Имена A/B ниже — условные названия двух сессий, не реальные показания:

| Шаг | Desired session | Delivery evidence | Last confirmed group | Last received session |
| --- | --- | --- | --- | --- |
| Группа A Start, packet ещё не пришёл | A | Awaiting packet | Прежняя подтверждённая группа или отсутствует | Прежний packet или отсутствует |
| Получен v2 packet A | A | Packet confirmed | A | A |
| A завершена, B запущена; packet B ещё не пришёл | B | Awaiting packet | A | A |
| Получен v2 packet B | B | Packet confirmed | B | B |
| Затем доставлен старый сохранённый packet A | B | Packet confirmed | B | A |

Последний шаг корректен: поздний A не отменяет подтверждение B.
Учитывайте все columns, а не только Last received session.
Если имя исторической сессии не найдено в доступном Sessions list,
UI показывает её UUID.

### 8.2. Что означает завершение группы

После End desired session очищена, а Delivery evidence показывает
**No group requested**. Last confirmed group может продолжать показывать
прошлую ненулевую группу как историческое свидетельство.

Пакет v2 с `session_id: null` означает сохранённый контекст без группы.
Он не передаёт context revision, поэтому не доказывает конкретную revision
отключения назначения. UI не заявляет такое подтверждение.
Поздний packet ещё завершённой группы не переносится в новую группу.

Если нужен актуальный sensor state или достоверный offline/online indicator,
это отдельное требование: этот Dashboard таких guarantees не предоставляет.

## 9. Справочник экранов и API

| Экран/action | API дополнения | Основные правила |
| --- | --- | --- |
| Profile / Refresh | `GET /v1/auth/me` | Собственный профиль; Auth recovery при необходимости |
| Sessions | `GET /v1/sessions` | Только доступные пользователю сессии |
| Create form choices / Device context | `GET /v1/sessions/options` | Teacher/admin; schools, approved students, visible devices/evidence |
| Create draft | `POST /v1/sessions` | Teacher/admin; school/name/student IDs/device IDs; успех `201` |
| Save roster | `PUT /v1/sessions/{session_id}/roster` | Teacher/admin; только draft; успех `200` |
| Start | `POST /v1/sessions/{session_id}/start` | Draft → active; успех `200` |
| End | `POST /v1/sessions/{session_id}/finish` | Active → ended; успех `200` |
| Open | `GET /v1/sessions/{session_id}/telemetry` | Разрешённая session history; limit/offset |
| All telemetry | `GET /v1/telemetry` | Только approved manager/admin; limit/offset |
| Schools list | `GET /v1/admin/schools` | Admin |
| Add school | `POST /v1/admin/schools` | Admin; JSON name; успех `201` |
| User access list | `GET /v1/admin/users` | Admin |
| Save user | `PATCH /v1/admin/users/{user_id}` | Admin; role/school_id/status; успех `200` |
| Device bindings list | `GET /v1/admin/devices` | Admin; tokens не возвращаются |
| Save binding | `PATCH /v1/admin/devices/{device_id}` | Admin; JSON school_id или null; успех `200` |
| Log out | `POST /v1/auth/logout` | Cookies + CSRF |

Для GET history query используется `?limit=50&offset=0`.
Все user endpoints используют session cookies; изменяющие запросы
дополнительно требуют CSRF и допустимый Origin согласно
[Auth tutorial](AUTHENTICATION_TUTORIAL_RU.md#5-как-работают-cookies-csrf-и-обновление).
Передача device token не заменяет user login.

Иллюстративный JSON для Create draft:

```json
{
  "school_id": "11111111-1111-4111-8111-111111111111",
  "name": "TEST tutorial group",
  "student_ids": ["22222222-2222-4222-8222-222222222222"],
  "device_ids": ["33333333-3333-4333-8333-333333333333"]
}
```

Замените UUID существующими разрешёнными records. Save roster передаёт
только `student_ids` и `device_ids`, без name/school_id. Start/End body
не нужен. Не добавляйте лишние поля: models запрещают extra fields.
Start/End и Add school/Create draft не обещают автоматическую HTTP
идемпотентность: при потерянном ответе перечитайте состояние перед повтором.

## 10. Ошибки и ограничения

### 10.1. Диагностика

| Симптом | Причина/проверка | Следующее действие |
| --- | --- | --- |
| `/` даёт `404` | Сервер v1 или отсутствует user configuration | Оператор проверяет установленную версию/конфигурацию дополнения |
| Pending/disabled вместо Sessions | Профиль не approved | Проверить назначение доступа с admin |
| Нет Create session | Роль student/manager либо не approved | Проверить role/status; создавать может teacher/admin |
| Нет students в choices | Не одобрены, другая роль/школа | Admin проверяет профили, затем Refresh |
| Нет устройства в choices | Нет registration, неверная school binding или inactive | Operator/admin проверяет UUID, binding, active flag |
| Нет сессий у student | Student не включён в roster | Teacher проверяет состав, для started roster создаёт новую группу |
| Start `409` | Занято устройство или изменены условия/статус | Refresh, проверить активные назначения и состав; не повторять бесконечно |
| Save roster `409` | Сессия уже начата или изменилась | Перечитать статус; новый состав требует новой сессии |
| Save binding `409` | Устройство в active session | Согласованно завершить занятие перед перепривязкой |
| Save user `409` | Несовместимые role/school/status | Проверить school для student/teacher и null fields для pending |
| `422 Invalid request fields` | Неверные поля/UUID/длина/пустые массивы | Исправить входные данные; не добавлять metadata к строгим models |
| `403` после изменения роли | Сервер уже проверяет новые права | Refresh профиля и использовать разрешённую операцию |
| Awaiting packet | Нет полученного v2 packet desired группы | Проверить client v2/context/network/outbox с оператором |
| Есть записи global history, но пусто в сессии | v1, null или другой session_id | Проверить исходный envelope; не переписывать старые queued packets |
| После End приходят строки | Доставляется сохранённая история | Проверить original membership; это допустимый replay |
| Refresh не обновил открытые readings | Toolbar load не вызывает history reload | Нажать Open/All telemetry снова, затем paging |
| Last received session старая | Поздний replay старой группы | Сравнить Desired и Last confirmed group |
| `503` или login recovery error | Auth/DB/runtime/server недоступны | Повторить позже, длительный сбой передать оператору |

При timeout Create/Start/End перечитайте Sessions/Device context:
сервер мог уже завершить действие. Перезагрузка UI не отменяет транзакцию.
Для отчёта передайте operator время, origin, безопасный error body,
user/session/device IDs. Password, cookies, tokens и DSN не публикуйте.

### 10.2. Возможности, которых нет в этом UI

Нет редактирования/удаления сохранённой телеметрии, sensor commands,
live charts, CSV export, поиска, date filtering, current-state projection,
device registration/token rotation, настройки драйверов и password recovery.
Нет удаления/перезапуска ended session и редактирования started roster.
No sessions / No telemetry означают результат текущего permitted запроса,
а не автоматическую диагностику hardware.

Номинальные 10 секунд относятся к сборщикам, а не частоте обновления UI.
Linux и ESP32 имеют разные offline collection policies. Queue delivery,
сбой clocks, storage capacity и hardware accuracy требуют отдельной
операторской проверки. Dashboard не задаёт retention, fleet-scale или uptime SLA.

## 11. Учебная приёмка и источники

Для согласованного программного tutorial ожидается такой результат:

1. Admin создал TEST-school, одобрил TEST-teacher/student и привязал TEST-device.
2. Teacher создал draft с нужным составом, исправил roster до старта,
   затем получил active и Awaiting packet.
3. Операторский software client отправил явно обозначенный TEST v2 packet
   с context этой сессии; UUID/token не взяты у физического стенда.
4. Teacher обновил context и увидел Packet confirmed и запись через Open.
5. Student увидел свою историю, не получил controls управления.
6. Manager прочитал общую историю, не получил admin actions.
7. Teacher завершил группу, создал новую и проверил независимость
   Last confirmed group от позднего packet старой группы.

Этот список — критерии выполнения tutorial, не заявление о новом
remote/hardware тесте. Пакеты с `test_*` должны быть помечены программными,
не выдавайте их за результаты датчиков.

Описание UI сверено с неизменяемым snapshot:

- [index.html: все экраны, поля и кнопки](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/dashboard/index.html).
- [app.js: видимость по ролям, Refresh, paging и actions](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/dashboard/app.js).
- [user_api.py: routes и JSON models](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/user_api.py).
- [user_access.py: история и delivery evidence](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/src/tlm_device_data_platform/user_access.py).
- [Session migration: школы, RLS, roster и lifecycle](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/supabase/migrations/20261008010000_add_session_user_access.sql).
- [Protocol v2: сохранённая принадлежность](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/docs/device_ingestion/PROTOCOL_V2.md).
- [Технический handoff и исторические browser tests](https://github.com/evinlort/TLM_device_data_platform/blob/480d0cdf6f533c025f781193f3ce7b1ed4ea5099/docs/device_ingestion/SESSION_USER_ACCESS.md).

При изменении UI/deployment сверяйте эти действия с фактической версией.
Успех прежних тестов в handoff не является приёмкой нового сервера.
