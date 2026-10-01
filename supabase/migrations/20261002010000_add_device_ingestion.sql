-- Laboratory ingestion v1. No production data or runtime password.
CREATE SCHEMA tlm;
REVOKE ALL ON SCHEMA tlm FROM PUBLIC, anon, authenticated, service_role;

CREATE TABLE tlm.devices (
    device_id uuid PRIMARY KEY,
    system_type text NOT NULL CHECK (length(btrim(system_type)) > 0),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE tlm.device_credentials (
    credential_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid NOT NULL REFERENCES tlm.devices(device_id) ON DELETE RESTRICT,
    token_sha256 bytea NOT NULL UNIQUE CHECK (octet_length(token_sha256) = 32),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    revoked_at timestamptz,
    expires_at timestamptz
);
CREATE INDEX device_credentials_device_idx ON tlm.device_credentials (device_id);

CREATE TABLE tlm.telemetry_messages (
    device_id uuid NOT NULL REFERENCES tlm.devices(device_id) ON DELETE RESTRICT,
    message_id uuid NOT NULL,
    schema_version smallint NOT NULL CHECK (schema_version = 1),
    stream_id uuid NOT NULL,
    sequence_no bigint NOT NULL CHECK (sequence_no >= 1),
    captured_at timestamptz,
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    payload jsonb NOT NULL CHECK (
        jsonb_typeof(payload) = 'object' AND payload <> '{}'::jsonb
    ),
    CONSTRAINT telemetry_messages_pkey PRIMARY KEY (device_id, message_id),
    CONSTRAINT telemetry_stream_sequence_uk
        UNIQUE (device_id, stream_id, sequence_no)
);
CREATE INDEX telemetry_device_received_idx
    ON tlm.telemetry_messages (device_id, received_at DESC, message_id);

COMMENT ON TABLE tlm.telemetry_messages IS
    'Append-only laboratory telemetry history. Not a current-state projection.';
COMMENT ON COLUMN tlm.telemetry_messages.received_at IS
    'Database wall-clock time of first insertion; not device capture time or commit time.';
COMMENT ON COLUMN tlm.telemetry_messages.captured_at IS
    'Untrusted device capture time; NULL when the device has no synchronized UTC clock.';
COMMENT ON COLUMN tlm.telemetry_messages.payload IS
    'Laboratory sensor map. Numeric and per-system validation belongs to TLM API v1.';
COMMENT ON COLUMN tlm.device_credentials.token_sha256 IS
    'SHA-256 digest of a high-entropy random device token; never a plaintext token.';

ALTER TABLE tlm.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.device_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.telemetry_messages ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE tlm.devices, tlm.device_credentials, tlm.telemetry_messages
    FROM PUBLIC, anon, authenticated, service_role;

DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tlm_ingest') THEN
        CREATE ROLE tlm_ingest NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
            NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    ELSIF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = 'tlm_ingest'
          AND (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole
               OR rolreplication OR rolbypassrls OR rolinherit)
    ) THEN
        RAISE EXCEPTION 'Existing tlm_ingest role has incompatible attributes; review it';
    END IF;
END;
$role$;

REVOKE ALL ON SCHEMA tlm FROM tlm_ingest;
GRANT USAGE ON SCHEMA tlm TO tlm_ingest;
REVOKE ALL ON TABLE tlm.devices, tlm.device_credentials, tlm.telemetry_messages
    FROM tlm_ingest;
GRANT SELECT ON TABLE tlm.devices, tlm.device_credentials, tlm.telemetry_messages
    TO tlm_ingest;
GRANT INSERT (device_id, message_id, schema_version, stream_id, sequence_no,
              captured_at, payload)
    ON TABLE tlm.telemetry_messages TO tlm_ingest;

CREATE POLICY backend_read_devices ON tlm.devices
    FOR SELECT TO tlm_ingest USING (true);
CREATE POLICY backend_read_credentials ON tlm.device_credentials
    FOR SELECT TO tlm_ingest USING (true);
CREATE POLICY backend_read_telemetry ON tlm.telemetry_messages
    FOR SELECT TO tlm_ingest USING (true);
CREATE POLICY backend_insert_telemetry ON tlm.telemetry_messages
    FOR INSERT TO tlm_ingest
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM tlm.devices AS d
            WHERE d.device_id = telemetry_messages.device_id
              AND d.is_active
        )
    );

-- The API authenticates the token and binds the payload to that device_id.
-- These policies grant trusted backend-wide access, NOT student/device isolation.
-- No UPDATE, DELETE, TRUNCATE, CREATE, or credential-provisioning grant is added.
-- received_at cannot be supplied explicitly by the runtime role.
