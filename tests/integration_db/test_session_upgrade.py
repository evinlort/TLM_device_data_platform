"""Apply the ordered migration to a disposable pre-feature database with rows."""
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest

pytestmark = pytest.mark.database


def test_upgrade_preserves_fixture_and_sessionless_history():
    dsn = os.environ.get('TLM_TEST_ADMIN_DSN')
    if not dsn:
        pytest.fail('TLM_TEST_ADMIN_DSN is required')
    config = conninfo_to_dict(dsn)
    if config.get('host') not in {'localhost', '127.0.0.1', '::1'} or config.get('hostaddr', config['host']) not in {'localhost', '127.0.0.1', '::1'}:
        pytest.fail('Upgrade test requires disposable loopback PostgreSQL')
    name = 'tlm_upgrade_'+uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(
            sql.Identifier(name)))
        try:
            with psycopg.connect(make_conninfo(dsn, dbname=name)) as db:
                # Only the Auth FK surface is needed for this SQL upgrade test;
                # real Supabase Auth is exercised separately in the API suite.
                db.execute(
                    'CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY,email text)')
                migrations = sorted(Path('supabase/migrations').glob('*.sql'))
                for migration in migrations[:2]:
                    db.execute(migration.read_text(), prepare=False)
                device, message, stream = uuid4(), uuid4(), uuid4()
                db.execute(
                    "INSERT INTO tlm.devices(device_id,system_type) VALUES (%s,'TEST upgrade')", (device,))
                db.execute(
                    "INSERT INTO public.ingest_messages(body) VALUES (%s)", (b'TEST legacy bytes',))
                db.execute('INSERT INTO tlm.telemetry_messages(device_id,message_id,schema_version,stream_id,sequence_no,payload) VALUES (%s,%s,1,%s,1,%s)',
                           (device, message, stream, '{"test_sensor":123}'))
                before = db.execute(
                    'SELECT * FROM tlm.telemetry_messages').fetchone()
                db.execute(migrations[2].read_text(), prepare=False)
                after = db.execute(
                    'SELECT device_id,message_id,schema_version,stream_id,sequence_no,captured_at,received_at,payload FROM tlm.telemetry_messages').fetchone()
                assert before == after
                assert db.execute(
                    'SELECT session_id FROM tlm.telemetry_messages').fetchone() == (None,)
                assert bytes(db.execute('SELECT body FROM public.ingest_messages').fetchone()[
                             0]) == b'TEST legacy bytes'
        finally:
            admin.execute(sql.SQL('DROP DATABASE {}').format(
                sql.Identifier(name)))
