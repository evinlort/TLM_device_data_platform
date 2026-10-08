"""Real Linux and ESP32 v2 clients against the local Auth/API/database fixture."""
from uuid import UUID, uuid4

import pytest

from .test_session_access import access, draft, ingest, packet

pytestmark = pytest.mark.database


def test_real_linux_mixed_replay_reboot_and_session_switch(access):
    from tlm_device_data_platform.edge_agent import Outbox, HTTPSender, run_agent
    from tlm_device_data_platform.device_context import ContextTracker
    from tlm_device_data_platform.telemetry_v1 import TelemetryV1
    from tlm_device_data_platform.telemetry_v2 import TelemetryV2
    a = access
    teacher, _, _ = a['register']('teacher', a['schools'][0])
    _, uid, _ = a['register']('student', a['schools'][0])
    old_session = draft(teacher, a['schools'][0], [uid], a['devices'][:1])
    assert teacher.post('/v1/sessions/'+old_session +
                        '/start').status_code == 200
    sender = HTTPSender(a['url']+'/v2/telemetry',
                        a['tokens'][0], allow_insecure_http=True)
    queue = Outbox(a['tmp_path']/'mixed.sqlite3', a['devices'][0])
    queue.save_context(sender.context(a['devices'][0]))
    old = TelemetryV2(a['devices'][0], uuid4(), uuid4(), 1, None, {
                      'test_sensor': 1}, UUID(old_session)).to_bytes()
    legacy = TelemetryV1(a['devices'][0], uuid4(), uuid4(), 1, None, {
                         'test_sensor': 0}).to_bytes()
    assert sender.send(old).action == 'ack'
    queue.enqueue(legacy)
    queue.enqueue(old)
    assert teacher.post('/v1/sessions/'+old_session +
                        '/finish').status_code == 200
    new_session = draft(teacher, a['schools'][0], [uid], a['devices'][:1])
    assert teacher.post('/v1/sessions/'+new_session +
                        '/start').status_code == 200
    reopened = Outbox(queue.path, a['devices'][0])
    tracker = ContextTracker(reopened, sender)
    assert run_agent(reopened, sender, lambda: {
                     'test_sensor': 2}, count=1, interval=.01, context_tracker=tracker) == {}
    rows = a['admin'].execute(
        'SELECT schema_version,session_id,stream_id,payload FROM tlm.telemetry_messages WHERE device_id=%s ORDER BY received_at', (a['devices'][0],)).fetchall()
    assert len(rows) == 3
    assert {(r[0], r[1]) for r in rows} == {(1, None),
                                            (2, UUID(old_session)), (2, UUID(new_session))}
    assert rows[0][2] != rows[-1][2]
    assert TelemetryV2.parse(old).session_id == UUID(old_session)
    assert ingest(a, packet(a['devices'][0], old_session)).status_code == 201
    context = teacher.get('/v1/sessions/options').json()['devices']
    evidence = next(
        d for d in context if d['device_id'] == str(a['devices'][0]))
    assert evidence['confirmed_session_id'] == new_session
    assert evidence['last_received_session_id'] == old_session
    assert evidence['desired_session_confirmed'] is True


def test_real_esp32_v2_context_and_mixed_endpoints(access, monkeypatch):
    import asyncio
    import importlib.util
    import sys
    from pathlib import Path
    a = access
    teacher, _, _ = a['register']('teacher', a['schools'][0])
    _, uid, _ = a['register']('student', a['schools'][0])
    session = draft(teacher, a['schools'][0], [uid], a['devices'][:1])
    assert teacher.post('/v1/sessions/'+session+'/start').status_code == 200
    root = Path('firmware/esp32_micropython')
    modules = []
    for name in ('tlm_core', 'tlm_http'):
        spec = importlib.util.spec_from_file_location(name, root/(name+'.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    core, transport_module = modules
    monkeypatch.setitem(sys.modules, 'tlm_core', core)
    transport = transport_module.HTTPTransport(
        a['url']+'/v2/telemetry', a['tokens'][0], allow_insecure_http=True)

    async def scenario():
        context = await transport.fetch_context(str(a['devices'][0]))
        assert context['session_id'] == session
        old = core.make_message(str(a['devices'][0]), str(
            uuid4()), 1, {'test_sensor': 1}, str(uuid4()))
        modern = core.make_message(str(a['devices'][0]), str(uuid4()), 1, {
                                   'test_sensor': 2}, str(uuid4()), context=context)
        assert (await transport.post(old))[0] == 201
        assert (await transport.post(modern))[0] == 201
        assert (await transport.post(modern))[0] == 200
    asyncio.run(scenario())
