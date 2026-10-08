"""Real Auth, API, RLS, session lifecycle and v2 ingestion on disposable Supabase."""
import hashlib
import os
import secrets
import socket
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier, Event, Thread
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest
import uvicorn

from tlm_device_data_platform.ingestion import create_app
from tlm_device_data_platform.postgres_ingestion import PostgresTelemetryRepository
from tlm_device_data_platform.user_access import UserRepository, SupabaseAuth

pytestmark = pytest.mark.database


@contextmanager
def serve_app(app):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    ready = Event()

    class Server(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()
    server = Server(uvicorn.Config(
        app, access_log=False, log_level='critical'))
    thread = Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        assert ready.wait(10)
        yield f'http://127.0.0.1:{sock.getsockname()[1]}'
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not thread.is_alive()


@pytest.fixture
def access(tmp_path):
    dsn = os.environ.get('TLM_TEST_ADMIN_DSN')
    url, key = os.environ.get(
        'TLM_TEST_AUTH_URL'), os.environ.get('TLM_TEST_AUTH_KEY')
    if not all((dsn, url, key)):
        pytest.fail(
            'Real disposable Auth and DB configuration is required; no skips')
    config = conninfo_to_dict(dsn)
    if config.get('host') not in {'127.0.0.1', 'localhost', '::1'} or config.get('hostaddr', config['host']) not in {'127.0.0.1', 'localhost', '::1'}:
        pytest.fail('Only disposable loopback databases are allowed')
    if httpx.URL(url).host not in {'127.0.0.1', 'localhost', '::1'}:
        pytest.fail('Only disposable loopback Auth is allowed')
    suffix = uuid4().hex
    users = []
    logins = ['tlm_test_user_' + suffix, 'tlm_test_ingest_' + suffix]
    with psycopg.connect(dsn, autocommit=True) as admin:
        runtime_dsns = []
        for login, group in zip(logins, ['tlm_user', 'tlm_ingest']):
            password = secrets.token_urlsafe(32)
            admin.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOBYPASSRLS PASSWORD {}').format(
                sql.Identifier(login), sql.Literal(password)))
            admin.execute(sql.SQL('GRANT {} TO {}').format(
                sql.Identifier(group), sql.Identifier(login)))
            runtime_dsns.append(make_conninfo(
                dsn, user=login, password=password))
        school_ids = [uuid4(), uuid4()]
        device_ids = [uuid4(), uuid4(), uuid4()]
        tokens = [secrets.token_urlsafe(32) for _ in device_ids]
        admin.execute('INSERT INTO tlm.schools(school_id,name) VALUES (%s,%s),(%s,%s)',
                      (school_ids[0], 'TEST A '+suffix, school_ids[1], 'TEST B '+suffix))
        for i, (device, token) in enumerate(zip(device_ids, tokens)):
            admin.execute(
                "INSERT INTO tlm.devices(device_id,system_type,school_id) VALUES (%s,'TEST software',%s)", (device, school_ids[i//2]))
            admin.execute('INSERT INTO tlm.device_credentials(device_id,token_sha256) VALUES (%s,%s)',
                          (device, hashlib.sha256(token.encode()).digest()))
        app = create_app(PostgresTelemetryRepository(runtime_dsns[1]),
                         user_repository=UserRepository(runtime_dsns[0]),
                         auth_provider=SupabaseAuth(
                             url, key, allow_insecure_local=True),
                         cookie_secure=False)
        with serve_app(app) as api_url:
            clients = []

            def register(role=None, school=None):
                client = httpx.Client(base_url=api_url)
                clients.append(client)
                assert client.get('/v1/auth/csrf').status_code == 200
                client.headers['X-CSRF-Token'] = client.cookies.get('tlm_csrf')
                email = 'test-'+uuid4().hex+'@example.com'
                response = client.post(
                    '/v1/auth/register', json={'email': email, 'password': 'TEST-password-'+suffix})
                assert response.status_code == 201, response.text
                profile = client.get('/v1/auth/me').json()
                uid = UUID(profile['user_id'])
                users.append(uid)
                if role:
                    admin.execute(
                        "UPDATE tlm.user_profiles SET role=%s,school_id=%s,status='approved' WHERE user_id=%s", (role, school, uid))
                client.headers['X-CSRF-Token'] = client.cookies.get('tlm_csrf')
                return client, uid, email

            class PrivateFixture(dict):
                def __repr__(self):
                    return '<DisposableAuthAndDatabase: credentials redacted>'
            data = PrivateFixture({'admin': admin, 'register': register, 'url': api_url,
                                   'schools': school_ids, 'devices': device_ids, 'tokens': tokens,
                                   'track_user': users.append, 'password': 'TEST-password-'+suffix, 'user_dsn': runtime_dsns[0], 'ingest_dsn': runtime_dsns[1], 'app': app, 'tmp_path': tmp_path})
            try:
                yield data
            finally:
                for client in clients:
                    client.close()
                admin.execute('SET session_replication_role = replica')
                admin.execute(
                    'DELETE FROM tlm.telemetry_messages WHERE device_id = ANY(%s)', (device_ids,))
                admin.execute(
                    'DELETE FROM tlm.active_device_sessions WHERE device_id = ANY(%s)', (device_ids,))
                admin.execute(
                    'DELETE FROM tlm.device_contexts WHERE device_id = ANY(%s)', (device_ids,))
                admin.execute(
                    'DELETE FROM tlm.session_devices WHERE session_id IN (SELECT session_id FROM tlm.sessions WHERE school_id = ANY(%s))', (school_ids,))
                admin.execute(
                    'DELETE FROM tlm.session_participants WHERE session_id IN (SELECT session_id FROM tlm.sessions WHERE school_id = ANY(%s))', (school_ids,))
                admin.execute(
                    'DELETE FROM tlm.sessions WHERE school_id = ANY(%s)', (school_ids,))
                admin.execute(
                    'DELETE FROM tlm.device_credentials WHERE device_id = ANY(%s)', (device_ids,))
                admin.execute(
                    'DELETE FROM tlm.devices WHERE device_id = ANY(%s)', (device_ids,))
                admin.execute(
                    'DELETE FROM tlm.user_profiles WHERE user_id = ANY(%s)', (users,))
                admin.execute(
                    'DELETE FROM auth.users WHERE id = ANY(%s)', (users,))
                admin.execute(
                    'DELETE FROM tlm.schools WHERE school_id = ANY(%s)', (school_ids,))
                admin.execute('SET session_replication_role = origin')
                for login in logins:
                    admin.execute(sql.SQL('DROP ROLE {}').format(
                        sql.Identifier(login)))


def draft(client, school, students, devices):
    r = client.post('/v1/sessions', json={'name': 'TEST session', 'school_id': str(school),
                    'student_ids': [str(s) for s in students], 'device_ids': [str(d) for d in devices]})
    assert r.status_code == 201, r.text
    return r.json()['session_id']


def packet(device, session=None, version=2):
    result = {'schema_version': version, 'device_id': str(device), 'message_id': str(uuid4()),
              'stream_id': str(uuid4()), 'sequence_no': 1, 'captured_at': None, 'payload': {'test_sensor': 42}}
    if version == 2:
        result['session_id'] = session
    return result


def ingest(a, message, token=None):
    return httpx.post(a['url']+'/v%d/telemetry' % message['schema_version'], json=message,
                      headers={'Authorization': 'Bearer '+(token or a['tokens'][0])})


def test_auth_pending_admin_approval_refresh_disable_logout(access):
    a = access
    pending, uid, email = a['register']()
    assert pending.get('/v1/auth/me').json()['status'] == 'pending'
    assert pending.get('/v1/telemetry').status_code == 403
    assert pending.get('/v1/sessions').status_code == 403
    admin, _, _ = a['register']('admin')
    assert pending.patch('/v1/admin/users/'+str(uid), json={
                         'role': 'admin', 'status': 'approved', 'school_id': None}).status_code == 403
    assert admin.patch('/v1/admin/users/'+str(uid), json={
                       'role': 'student', 'status': 'approved', 'school_id': str(a['schools'][0])}).status_code == 200
    assert pending.get('/v1/sessions').status_code == 200
    refresh = pending.cookies.get('tlm_refresh')
    assert pending.post('/v1/auth/refresh').status_code == 200
    assert pending.cookies.get('tlm_refresh') != refresh
    pending.headers['X-CSRF-Token'] = pending.cookies.get('tlm_csrf')
    assert admin.patch('/v1/admin/users/'+str(uid), json={
                       'role': 'student', 'status': 'disabled', 'school_id': str(a['schools'][0])}).status_code == 200
    assert pending.get('/v1/sessions').status_code == 403
    current_refresh = pending.cookies.get('tlm_refresh')
    assert pending.post('/v1/auth/logout').status_code == 200
    revoked = httpx.post(os.environ['TLM_TEST_AUTH_URL']+'/auth/v1/token?grant_type=refresh_token', headers={
                         'apikey': os.environ['TLM_TEST_AUTH_KEY']}, json={'refresh_token': current_refresh})
    assert revoked.status_code in (400, 401)
    assert pending.get('/v1/auth/me').status_code == 401
    assert not pending.cookies.get('tlm_refresh')
    assert pending.post(
        '/v1/auth/refresh', json={'refresh_token': refresh}).status_code in (401, 403)
    pending.get('/v1/auth/csrf')
    pending.headers['X-CSRF-Token'] = pending.cookies.get('tlm_csrf')
    assert pending.post(
        '/v1/auth/login', json={'email': email, 'password': 'wrong-password'}).status_code == 401


def test_isolation_late_ingestion_and_immutable_roster(access):
    a = access
    teacher, _, _ = a['register']('teacher', a['schools'][0])
    student, uid, _ = a['register']('student', a['schools'][0])
    other, oid, _ = a['register']('student', a['schools'][1])
    teacher_b, _, _ = a['register']('teacher', a['schools'][1])
    manager, _, _ = a['register']('manager')
    session = draft(teacher, a['schools'][0], [uid], a['devices'][:2])
    assert teacher.post('/v1/sessions/'+session+'/start').status_code == 200
    assert teacher.put('/v1/sessions/'+session+'/roster', json={'student_ids': [
                       str(oid)], 'device_ids': [str(a['devices'][0])]}).status_code == 409
    message = packet(a['devices'][0], session)
    assert ingest(a, message).status_code == 201
    assert ingest(a, message).status_code == 200
    assert ingest(a, packet(a['devices'][1], session),
                  a['tokens'][1]).status_code == 201
    assert student.get('/v1/sessions/'+session+'/telemetry').status_code == 200
    assert len(student.get('/v1/sessions/'+session +
               '/telemetry?limit=1').json()['items']) == 1
    for denied in (other, teacher_b):
        assert denied.get('/v1/sessions/'+session +
                          '/telemetry').status_code == 404
        assert denied.post('/v1/sessions/'+session +
                           '/finish').status_code == 403
    assert student.get('/v1/telemetry').status_code == 403
    assert ingest(a, packet(a['devices'][0], version=1)).status_code == 201
    assert len(manager.get('/v1/telemetry').json()['items']) == 3
    assert teacher.post('/v1/sessions/'+session+'/finish').status_code == 200
    assert ingest(a, packet(a['devices'][0], session)).status_code == 201
    changed = dict(message, session_id=None)
    assert ingest(a, changed).status_code == 409
    assert ingest(a, dict(message, session_id=str(uuid4()))).status_code == 409
    assert ingest(a, packet(a['devices'][2], session),
                  a['tokens'][2]).status_code == 403
    assert httpx.get(a['url']+'/v2/devices/'+str(a['devices'][0])+'/context',
                     headers={'Authorization': 'Bearer '+a['tokens'][0]}).json()['revision'] == 2
    assert httpx.get(a['url']+'/v2/devices/'+str(a['devices'][1])+'/context',
                     headers={'Authorization': 'Bearer '+a['tokens'][0]}).status_code == 403


def test_concurrent_start_and_direct_rls(access):
    a = access
    teacher, tid, _ = a['register']('teacher', a['schools'][0])
    student, uid, _ = a['register']('student', a['schools'][0])
    sessions = [draft(teacher, a['schools'][0], [uid],
                      a['devices'][:1]) for _ in range(2)]
    barrier = Barrier(2)

    def start(s):
        barrier.wait()
        return teacher.post('/v1/sessions/'+s+'/start').status_code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(start, sessions)) == [200, 409]
    with psycopg.connect(a['user_dsn']) as db:
        db.execute("SELECT set_config('tlm.user_id',%s,true)", (str(uid),))
        assert db.execute(
            'SELECT count(*) FROM tlm.telemetry_messages').fetchone()[0] == 0
        assert db.execute(
            "UPDATE tlm.user_profiles SET role='admin' WHERE user_id=%s", (uid,)).rowcount == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('SELECT * FROM tlm.device_credentials')


def test_csrf_and_unauthenticated(access):
    a = access
    client, _, _ = a['register']('admin')
    client.headers.pop('X-CSRF-Token')
    assert client.post('/v1/admin/schools',
                       json={'name': 'TEST blocked'}).status_code == 403
    client.headers['X-CSRF-Token'] = client.cookies.get('tlm_csrf')
    assert client.post('/v1/admin/schools', json={'name': 'TEST blocked'}, headers={
                       'Origin': 'https://attacker.example'}).status_code == 403
    assert httpx.get(a['url']+'/v1/telemetry').status_code == 401
    assert client.post('/v1/auth/register', json={
                       'email': 'test@example.com', 'password': 'password', 'role': 'admin'}).status_code == 422


def test_cross_school_creation_forgery_and_password_redaction(access):
    a = access
    teacher, _, _ = a['register']('teacher', a['schools'][0])
    other, oid, _ = a['register']('student', a['schools'][1])
    manager, _, _ = a['register']('manager')
    data = {'name': 'TEST forged', 'school_id': str(a['schools'][1]), 'student_ids': [
        str(oid)], 'device_ids': [str(a['devices'][2])]}
    assert teacher.post('/v1/sessions', json=data).status_code == 403
    assert manager.post('/v1/sessions', json=data).status_code == 403
    data['school_id'] = str(a['schools'][0])
    assert teacher.post('/v1/sessions', json=data).status_code == 409
    with httpx.Client(base_url=a['url']) as forged:
        forged.cookies.set('tlm_access', 'TEST-forged-jwt')
        assert forged.get('/v1/auth/me?user_id='+str(oid)).status_code == 401
        forged.get('/v1/auth/csrf')
        forged.headers['X-CSRF-Token'] = forged.cookies.get('tlm_csrf')
        invalid = forged.post(
            '/v1/auth/login', json={'email': 'invalid', 'password': 'TEST-short'})
        assert invalid.status_code == 422
        assert 'TEST-short' not in invalid.text
