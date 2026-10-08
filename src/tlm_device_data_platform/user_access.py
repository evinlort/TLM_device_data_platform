"""Supabase Auth adapter and transaction-scoped PostgreSQL user access."""
from contextlib import contextmanager
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException
import httpx
import psycopg
from psycopg.rows import dict_row

from .postgres_ingestion import PostgresTelemetryRepository, validate_dsn
from .telemetry_v1 import StorageUnavailable


class SupabaseAuth:
    def __init__(self, url, key, *, allow_insecure_local=False):
        parsed = urlsplit(url)
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/') or not key or
                (parsed.scheme != 'https' and not (allow_insecure_local and parsed.scheme == 'http'
                 and parsed.hostname in {'localhost', '127.0.0.1', '::1'}))):
            raise ValueError(
                'Auth requires a Supabase HTTPS origin or explicit loopback test origin')
        self._url, self._key = url.rstrip('/')+'/auth/v1', key

    async def _request(self, method, path, *, data=None, token=None):
        headers = {'apikey': self._key}
        if token:
            headers['Authorization'] = 'Bearer '+token
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                response = await client.request(method, self._url+path, json=data, headers=headers)
            if response.status_code >= 500 or response.status_code == 429:
                raise HTTPException(503, 'Authentication provider unavailable')
            if not 200 <= response.status_code < 300:
                raise HTTPException(401, 'Authentication rejected')
            return response.json() if response.content else {}
        except (httpx.HTTPError, ValueError):
            raise HTTPException(
                503, 'Authentication provider unavailable') from None

    async def register(self, email, password):
        return await self._request('POST', '/signup', data={'email': email, 'password': password})

    async def login(self, email, password):
        return await self._request('POST', '/token?grant_type=password', data={'email': email, 'password': password})

    async def refresh(self, refresh_token):
        return await self._request('POST', '/token?grant_type=refresh_token', data={'refresh_token': refresh_token})

    async def get_user(self, access_token):
        if not access_token:
            raise HTTPException(401, 'Login required')
        data = await self._request('GET', '/user', token=access_token)
        try:
            return UUID(data['id'])
        except (KeyError, ValueError, TypeError):
            raise HTTPException(
                503, 'Invalid authentication provider response') from None

    async def logout(self, access_token):
        await self._request('POST', '/logout?scope=local', token=access_token)


class UserRepository:
    def __init__(self, dsn):
        validate_dsn(dsn)
        self._dsn = dsn

    @contextmanager
    def transaction(self, user_id, *, approved=True, roles=None):
        try:
            with psycopg.connect(self._dsn, connect_timeout=5, row_factory=dict_row,
                                 prepare_threshold=None, application_name='tlm-user-access') as db:
                db.execute("SET LOCAL statement_timeout = '5s'")
                db.execute("SET LOCAL lock_timeout = '2s'")
                PostgresTelemetryRepository._check_runtime_role(db)
                membership = db.execute(
                    "SELECT pg_has_role(current_user,'tlm_user','MEMBER') AS allowed, pg_has_role(current_user,'tlm_ingest','MEMBER') AS broad").fetchone()
                if not membership['allowed'] or membership['broad']:
                    raise HTTPException(
                        503, 'User runtime must be separate from ingestion')
                db.execute(
                    "SELECT set_config('tlm.user_id',%s,true)", (str(user_id),))
                profile = db.execute(
                    'SELECT * FROM tlm.user_profiles WHERE user_id=%s', (user_id,)).fetchone()
                if profile is None:
                    raise HTTPException(403, 'User profile unavailable')
                if approved and profile['status'] != 'approved':
                    raise HTTPException(403, 'Administrator approval required')
                if roles and profile['role'] not in roles:
                    raise HTTPException(
                        403, 'Role does not permit this action')
                yield db, profile
        except StorageUnavailable:
            raise HTTPException(
                503, 'User runtime requires restricted database identity') from None
        except psycopg.errors.InsufficientPrivilege:
            raise HTTPException(403, 'Access denied') from None
        except (psycopg.errors.CheckViolation, psycopg.errors.UniqueViolation,
                psycopg.errors.ForeignKeyViolation, psycopg.errors.LockNotAvailable,
                psycopg.errors.DeadlockDetected):
            raise HTTPException(
                409, 'Session or assignment conflict') from None
        except psycopg.Error:
            raise HTTPException(503, 'User storage unavailable') from None

    def profile(self, uid):
        with self.transaction(uid, approved=False) as (_, profile):
            return profile

    def schools(self, uid, name=None):
        with self.transaction(uid, roles={'admin'}) as (db, _):
            if name is not None:
                return db.execute('INSERT INTO tlm.schools(name) VALUES (%s) RETURNING *', (name,)).fetchone()
            return db.execute('SELECT * FROM tlm.schools ORDER BY name,school_id').fetchall()

    def users(self, uid, target=None, change=None):
        with self.transaction(uid, roles={'admin'}) as (db, _):
            if target:
                row = db.execute('UPDATE tlm.user_profiles SET role=%s,school_id=%s,status=%s WHERE user_id=%s RETURNING *',
                                 (change.role, change.school_id, change.status, target)).fetchone()
                if row is None:
                    raise HTTPException(404, 'User unavailable')
                return row
            return db.execute('SELECT * FROM tlm.user_profiles ORDER BY email,user_id').fetchall()

    def devices(self, uid, target=None, school=None):
        with self.transaction(uid, roles={'admin'}) as (db, _):
            if target:
                row = db.execute(
                    'UPDATE tlm.devices SET school_id=%s WHERE device_id=%s RETURNING device_id,system_type,school_id,is_active', (school, target)).fetchone()
                if row is None:
                    raise HTTPException(404, 'Device unavailable')
                return row
            return self._devices(db)

    @staticmethod
    def _devices(db):
        # This is delivery evidence, not current sensor state. Replayed packets
        # remain attributed to their original session and can arrive out of order.
        return db.execute('''SELECT d.device_id,d.system_type,d.school_id,d.is_active,
            c.session_id AS desired_session_id,c.revision,
            t.session_id AS last_received_session_id,t.received_at AS last_v2_received_at,
            confirmed.session_id AS confirmed_session_id, confirmed.context_revision AS confirmed_revision,
            EXISTS (SELECT FROM tlm.telemetry_messages m WHERE m.device_id=d.device_id
              AND m.schema_version=2 AND m.session_id=c.session_id) AS desired_session_confirmed
            FROM tlm.devices d JOIN tlm.device_contexts c USING(device_id)
            LEFT JOIN LATERAL (SELECT session_id,received_at FROM tlm.telemetry_messages m
              WHERE m.device_id=d.device_id AND schema_version=2 ORDER BY received_at DESC,message_id DESC LIMIT 1) t ON true
            LEFT JOIN LATERAL (SELECT sd.session_id,sd.context_revision FROM tlm.session_devices sd
              WHERE sd.device_id=d.device_id AND sd.context_revision IS NOT NULL AND EXISTS
                (SELECT FROM tlm.telemetry_messages m WHERE m.device_id=d.device_id AND m.session_id=sd.session_id AND m.schema_version=2)
              ORDER BY sd.context_revision DESC LIMIT 1) confirmed ON true
            ORDER BY d.device_id''').fetchall()

    def options(self, uid):
        with self.transaction(uid, roles={'teacher', 'admin'}) as (db, _):
            return {'schools': db.execute('SELECT * FROM tlm.schools ORDER BY name').fetchall(),
                    'students': db.execute("SELECT user_id,email,school_id FROM tlm.user_profiles WHERE role='student' AND status='approved' ORDER BY email").fetchall(),
                    'devices': self._devices(db)}

    def sessions(self, uid):
        with self.transaction(uid) as (db, _):
            return self._sessions(db)

    @staticmethod
    def _sessions(db, session=None):
        return db.execute('''SELECT s.*,
          ARRAY(SELECT p.user_id FROM tlm.session_participants p WHERE p.session_id=s.session_id ORDER BY p.user_id) AS student_ids,
          ARRAY(SELECT d.device_id FROM tlm.session_devices d WHERE d.session_id=s.session_id ORDER BY d.device_id) AS device_ids
          FROM tlm.sessions s WHERE (%s::uuid IS NULL OR s.session_id=%s) ORDER BY s.started_at DESC NULLS FIRST,s.session_id''', (session, session)).fetchall()

    @staticmethod
    def _roster(db, session, data):
        db.execute(
            'DELETE FROM tlm.session_participants WHERE session_id=%s', (session,))
        db.execute(
            'DELETE FROM tlm.session_devices WHERE session_id=%s', (session,))
        for student in data.student_ids:
            db.execute(
                'INSERT INTO tlm.session_participants(session_id,user_id) VALUES (%s,%s)', (session, student))
        for device in data.device_ids:
            db.execute(
                'INSERT INTO tlm.session_devices(session_id,device_id) VALUES (%s,%s)', (session, device))

    def create_session(self, uid, data):
        with self.transaction(uid, roles={'teacher', 'admin'}) as (db, _):
            session = db.execute('INSERT INTO tlm.sessions(school_id,name,created_by) VALUES (%s,%s,%s) RETURNING session_id', (
                data.school_id, data.name, uid)).fetchone()['session_id']
            self._roster(db, session, data)
            return self._sessions(db, session)[0]

    def roster(self, uid, session, data):
        with self.transaction(uid, roles={'teacher', 'admin'}) as (db, _):
            row = db.execute(
                'SELECT * FROM tlm.sessions WHERE session_id=%s', (session,)).fetchone()
            if row is None or not db.execute('SELECT tlm.can_manage_school(%s) AS ok', (row['school_id'],)).fetchone()['ok']:
                raise HTTPException(403, 'Session unavailable')
            if row['status'] != 'draft':
                raise HTTPException(409, 'Started session roster is immutable')
            if not db.execute('SELECT session_id FROM tlm.sessions WHERE session_id=%s FOR UPDATE', (session,)).fetchone():
                raise HTTPException(409, 'Session changed while editing')
            self._roster(db, session, data)
            return self._sessions(db, session)[0]

    def transition(self, uid, session, action):
        with self.transaction(uid, roles={'teacher', 'admin'}) as (db, _):
            query = 'SELECT tlm.start_session(%s)' if action == 'start' else 'SELECT tlm.finish_session(%s)'
            db.execute(query, (session,))
            return self._sessions(db, session)[0]

    def telemetry(self, uid, session, limit, offset):
        with self.transaction(uid, roles=None if session else {'manager', 'admin'}) as (db, _):
            if session and not db.execute('SELECT session_id FROM tlm.sessions WHERE session_id=%s', (session,)).fetchone():
                raise HTTPException(404, 'Session unavailable')
            rows = db.execute('''SELECT * FROM tlm.telemetry_messages
              WHERE (%s::uuid IS NULL OR session_id=%s)
              ORDER BY received_at,device_id,message_id LIMIT %s OFFSET %s''', (session, session, limit+1, offset)).fetchall()
            return {'items': rows[:limit], 'next_offset': offset+limit if len(rows) > limit else None}
