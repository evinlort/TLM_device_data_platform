"""Real TCP HTTP -> restricted PostgreSQL login; only a disposable loopback DB."""
import hashlib
import json
import os
import secrets
import socket
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from threading import Barrier, Event, Thread
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest
import uvicorn

from tlm_device_data_platform.ingestion import create_app
from tlm_device_data_platform.postgres_ingestion import PostgresTelemetryRepository
from tlm_device_data_platform.telemetry_v1 import StorageUnavailable, TelemetryV1

pytestmark = pytest.mark.database


class PrivateTestDatabase(SimpleNamespace):
    def __repr__(self):
        return "<DisposableTestDatabase: credentials redacted>"


@contextmanager
def serve(repository):
    ready = Event()

    class Server(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    server = Server(uvicorn.Config(create_app(repository), access_log=False,
                                   log_level="critical", lifespan="off"))
    thread = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        assert ready.wait(5), "Test HTTP server did not start"
        yield f"http://127.0.0.1:{sock.getsockname()[1]}/v1/telemetry"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        assert not thread.is_alive(), "Test HTTP server did not stop"


def post(url, token, message):
    request = Request(url, data=message.to_bytes(), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


@pytest.fixture
def database():
    admin_dsn = os.environ.get("TLM_TEST_ADMIN_DSN")
    if not admin_dsn:
        pytest.fail("TLM_TEST_ADMIN_DSN is required for database tests; do not silently skip")
    config = conninfo_to_dict(admin_dsn)
    if config.get("host") not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Database tests refuse non-loopback databases")
    if config.get("hostaddr", config["host"]) not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Database tests refuse non-loopback hostaddr")
    login, password, token = "tlm_test_" + uuid4().hex, secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    device_id, other_device = uuid4(), uuid4()
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOCREATEDB "
                              "NOCREATEROLE NOBYPASSRLS PASSWORD {}")
                      .format(sql.Identifier(login), sql.Literal(password)))
        try:
            admin.execute(sql.SQL("GRANT tlm_ingest TO {}").format(sql.Identifier(login)))
            admin.execute("INSERT INTO tlm.devices (device_id, system_type) VALUES (%s, 'test-fixture'), (%s, 'test-fixture')",
                          (device_id, other_device))
            admin.execute("INSERT INTO tlm.device_credentials (device_id, token_sha256) VALUES (%s, %s)",
                          (device_id, hashlib.sha256(token.encode()).digest()))
            runtime_dsn = make_conninfo(admin_dsn, user=login, password=password)
            message = TelemetryV1(device_id, uuid4(), uuid4(), 1,
                                  datetime(2026, 10, 2, tzinfo=timezone.utc),
                                  {"test_temperature": 21.5, "test_distance": 123})
            yield PrivateTestDatabase(admin=admin, admin_dsn=admin_dsn, runtime_dsn=runtime_dsn,
                token=token, message=message, other_device=other_device,
                repository=PostgresTelemetryRepository(runtime_dsn))
        finally:
            for table in ("telemetry_messages", "device_credentials", "devices"):
                admin.execute(sql.SQL("DELETE FROM tlm.{} WHERE device_id IN (%s, %s)")
                              .format(sql.Identifier(table)), (device_id, other_device))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(login)))


def test_real_http_commits_exact_readings(database):
    with serve(database.repository) as url:
        status, receipt = post(url, database.token, database.message)
        assert status == 201
        row = database.admin.execute("SELECT payload, captured_at FROM tlm.telemetry_messages WHERE device_id = %s",
                                     (database.message.device_id,)).fetchone()
        assert row == (dict(database.message.payload), database.message.captured_at)
        assert receipt["status"] == "stored"


@pytest.mark.parametrize("round_no", range(5))
def test_concurrent_retries_create_exactly_one_row(database, round_no):
    with serve(database.repository) as url:
        barrier = Barrier(4)
        def synchronized_post(_):
            barrier.wait(timeout=5)
            return post(url, database.token, database.message)
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(synchronized_post, range(4)))
        assert sorted(status for status, _ in results) == [200, 200, 200, 201]
        assert len({receipt["received_at"] for _, receipt in results}) == 1
        assert database.admin.execute("SELECT count(*) FROM tlm.telemetry_messages WHERE device_id = %s",
                                      (database.message.device_id,)).fetchone()[0] == 1


def test_replay_after_unobserved_ack_and_conflicting_payload(database):
    database.repository.accept(database.token, database.message)
    with serve(database.repository) as url:
        assert post(url, database.token, database.message)[0] == 200
        changed = replace(database.message, payload={"test_temperature": 99})
        assert post(url, database.token, changed)[0] == 409


def test_stream_position_cannot_be_reused(database):
    with serve(database.repository) as url:
        assert post(url, database.token, database.message)[0] == 201
        assert post(url, database.token, replace(database.message, message_id=uuid4()))[0] == 409


@pytest.mark.parametrize("change", ["revoked", "expired", "inactive", "unknown"])
def test_invalid_credentials_never_write(database, change):
    token = database.token
    if change == "revoked":
        database.admin.execute("UPDATE tlm.device_credentials SET revoked_at = clock_timestamp() WHERE device_id = %s",
                               (database.message.device_id,))
    elif change == "expired":
        database.admin.execute("UPDATE tlm.device_credentials SET expires_at = clock_timestamp() - interval '1 day' WHERE device_id = %s",
                               (database.message.device_id,))
    elif change == "inactive":
        database.admin.execute("UPDATE tlm.devices SET is_active = false WHERE device_id = %s", (database.message.device_id,))
    else:
        token = secrets.token_urlsafe(32)
    with serve(database.repository) as url:
        assert post(url, token, database.message)[0] == 401
    assert database.admin.execute("SELECT count(*) FROM tlm.telemetry_messages WHERE device_id = %s",
                                  (database.message.device_id,)).fetchone()[0] == 0


def test_token_cannot_impersonate_another_device(database):
    with serve(database.repository) as url:
        assert post(url, database.token, replace(database.message, device_id=database.other_device))[0] == 403


def test_actual_runtime_login_cannot_rewrite_history_or_set_server_time(database):
    database.repository.accept(database.token, database.message)
    with psycopg.connect(database.runtime_dsn, autocommit=True) as runtime:
        for statement in (
            "UPDATE tlm.telemetry_messages SET payload = '{}'::jsonb",
            "DELETE FROM tlm.telemetry_messages", "TRUNCATE tlm.telemetry_messages",
            "UPDATE tlm.device_credentials SET revoked_at = NULL",
            "INSERT INTO tlm.devices (device_id, system_type) VALUES (gen_random_uuid(), 'test')",
            "INSERT INTO tlm.telemetry_messages (received_at) VALUES (clock_timestamp())",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                runtime.execute(statement)


def test_admin_identity_is_rejected_by_runtime_guard(database):
    with pytest.raises(StorageUnavailable):
        PostgresTelemetryRepository(database.admin_dsn).accept(database.token, database.message)


def test_unreachable_database_returns_503_not_ack(database):
    with socket.socket() as blocked:
        blocked.bind(("127.0.0.1", 0))
        dsn = make_conninfo(database.runtime_dsn, port=blocked.getsockname()[1])
        with serve(PostgresTelemetryRepository(dsn)) as url:
            assert post(url, database.token, database.message)[0] == 503


def test_reboot_and_late_old_stream_keep_history(database):
    old = database.message
    reboot = replace(old, message_id=uuid4(), stream_id=uuid4())
    late = replace(old, message_id=uuid4(), sequence_no=2)
    with serve(database.repository) as url:
        for message in (old, reboot, late):
            assert post(url, database.token, message)[0] == 201
    assert database.admin.execute("SELECT count(*) FROM tlm.telemetry_messages WHERE device_id = %s",
                                  (old.device_id,)).fetchone()[0] == 3


def test_edge_outbox_reconnect_crosses_real_http_and_database(database, tmp_path):
    from tlm_device_data_platform.edge_agent import Delivery, HTTPSender, Outbox, deliver_one
    queue_path = tmp_path / "outbox.sqlite3"
    outbox = Outbox(queue_path, database.message.device_id)
    original = database.message.to_bytes()
    outbox.enqueue(original)
    class OfflineSender:
        def send(self, body):
            assert body == original
            return Delivery("retry", "test_offline")
    assert deliver_one(outbox, OfflineSender()).action == "retry"
    reopened = Outbox(queue_path, database.message.device_id)
    assert reopened.oldest()[1] == original
    with serve(database.repository) as url:
        sender = HTTPSender(url, database.token, allow_insecure_http=True)
        assert deliver_one(reopened, sender).action == "ack"
    assert reopened.oldest() is None
    assert database.admin.execute("SELECT payload FROM tlm.telemetry_messages WHERE device_id = %s",
                                  (database.message.device_id,)).fetchone()[0] == dict(database.message.payload)


def test_provisioned_device_and_runtime_work_end_to_end(database, tmp_path):
    from tlm_device_data_platform.private_config import load_private_config
    from tlm_device_data_platform.provision import provision_device, provision_runtime
    login = "tlm_api_" + uuid4().hex
    device_id = uuid4()
    runtime_file = tmp_path / "runtime.secret.json"
    device_file = tmp_path / "device.secret.json"
    try:
        provision_runtime(database.admin_dsn, runtime_file, role=login)
        provision_device(database.admin_dsn, device_file, system_type="test-provisioned", device_id=device_id)
        runtime = load_private_config(runtime_file, {"TLM_DATABASE_DSN"})
        device = load_private_config(device_file, {"TLM_DEVICE_ID", "TLM_DEVICE_TOKEN"})
        repository = PostgresTelemetryRepository(runtime["TLM_DATABASE_DSN"])
        message = replace(database.message, device_id=device_id, message_id=uuid4())
        with serve(repository) as url:
            assert post(url, device["TLM_DEVICE_TOKEN"], message)[0] == 201
        with pytest.raises(FileExistsError):
            provision_device(database.admin_dsn, device_file, system_type="test-provisioned", device_id=uuid4())
    finally:
        for table in ("telemetry_messages", "device_credentials", "devices"):
            database.admin.execute(sql.SQL("DELETE FROM tlm.{} WHERE device_id = %s")
                                   .format(sql.Identifier(table)), (device_id,))
        database.admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login)))
