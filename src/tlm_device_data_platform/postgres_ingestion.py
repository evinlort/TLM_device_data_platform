"""Transactional PostgreSQL storage; works with local and hosted Supabase."""
from __future__ import annotations

import hashlib
import logging

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .telemetry_v1 import (
    AuthenticationFailed, DeviceMismatch, IngestReceipt, MessageConflict,
    StorageUnavailable, TelemetryV1,
)

_LOG = logging.getLogger(__name__)
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_dsn(dsn: str) -> None:
    """Require explicit host and verified TLS outside a loopback laboratory DB."""
    try:
        config = conninfo_to_dict(dsn)
    except psycopg.Error:
        raise ValueError("Invalid database configuration") from None
    host = config.get("host", "")
    local = host in _LOCAL_HOSTS and config.get("hostaddr", host) in _LOCAL_HOSTS
    if not host or (not local and config.get("sslmode") != "verify-full"):
        raise ValueError("An explicit database host and remote sslmode=verify-full are required")


class PostgresTelemetryRepository:
    def __init__(self, dsn: str):
        validate_dsn(dsn)
        self._dsn = dsn

    @staticmethod
    def _check_runtime_role(connection) -> None:
        forbidden = connection.execute("""
            SELECT r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb
                OR EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'tlm' AND c.relkind = 'r'
                      AND pg_has_role(current_user, c.relowner, 'MEMBER')
                ) AS forbidden
            FROM pg_roles r WHERE r.rolname = current_user
        """).fetchone()
        if forbidden is None or forbidden["forbidden"]:
            raise StorageUnavailable("Runtime requires a non-owner, non-privileged login")

    def accept(self, token: str, message: TelemetryV1) -> IngestReceipt:
        params = {
            "device_id": message.device_id, "message_id": message.message_id,
            "stream_id": message.stream_id, "sequence_no": message.sequence_no,
            "captured_at": message.captured_at, "payload": Jsonb(dict(message.payload)),
        }
        try:
            with psycopg.connect(self._dsn, connect_timeout=5, row_factory=dict_row,
                                 prepare_threshold=None, application_name="tlm-ingestion") as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                connection.execute("SET LOCAL statement_timeout = '5s'")
                connection.execute("SET LOCAL lock_timeout = '2s'")
                self._check_runtime_role(connection)
                credential = connection.execute("""
                    SELECT c.device_id
                    FROM tlm.device_credentials c JOIN tlm.devices d USING (device_id)
                    WHERE c.token_sha256 = %s AND c.revoked_at IS NULL
                      AND (c.expires_at IS NULL OR c.expires_at > clock_timestamp())
                      AND d.is_active
                """, (hashlib.sha256(token.encode("ascii")).digest(),)).fetchone()
                if credential is None:
                    raise AuthenticationFailed
                if credential["device_id"] != message.device_id:
                    raise DeviceMismatch
                # Both unique indexes may race for an identical concurrent retry.
                # Handle either here, then distinguish duplicates from conflicts by PK.
                inserted = connection.execute("""
                    INSERT INTO tlm.telemetry_messages
                        (device_id, message_id, schema_version, stream_id,
                         sequence_no, captured_at, payload)
                    VALUES (%(device_id)s, %(message_id)s, 1, %(stream_id)s,
                            %(sequence_no)s, %(captured_at)s, %(payload)s)
                    ON CONFLICT DO NOTHING
                    RETURNING received_at
                """, params).fetchone()
                if inserted is not None:
                    receipt = IngestReceipt(message.device_id, message.message_id,
                                            inserted["received_at"], False)
                else:
                    # A separate READ COMMITTED statement sees a concurrent winner.
                    # No matching PK means another message occupied the stream position.
                    existing = connection.execute("""
                        SELECT received_at,
                               schema_version = 1 AND stream_id = %(stream_id)s
                               AND sequence_no = %(sequence_no)s
                               AND captured_at IS NOT DISTINCT FROM %(captured_at)s
                               AND payload = %(payload)s AS same
                        FROM tlm.telemetry_messages
                        WHERE device_id = %(device_id)s AND message_id = %(message_id)s
                    """, params).fetchone()
                    if existing is None or not existing["same"]:
                        raise MessageConflict
                    receipt = IngestReceipt(message.device_id, message.message_id,
                                            existing["received_at"], True)
            # The connection context has committed successfully before any ACK.
            return receipt
        except psycopg.Error as error:
            # Never log the connection string, token, request body or error detail.
            _LOG.error("Persistence failed (%s)", type(error).__name__)
            raise StorageUnavailable from None
