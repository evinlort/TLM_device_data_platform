BEGIN;
CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;
SET LOCAL search_path = extensions, public;
SELECT plan(16);
SELECT has_schema('tlm', 'private backend schema exists');
SELECT has_table('tlm', 'devices', 'device registry exists');
SELECT has_table('tlm', 'device_credentials', 'credential registry exists');
SELECT has_table('tlm', 'telemetry_messages', 'telemetry history exists');
SELECT col_type_is('tlm', 'telemetry_messages', 'payload', 'jsonb', 'payload is jsonb');
SELECT is((SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'tlm' AND c.relkind = 'r' AND c.relrowsecurity),
          3::bigint, 'all application tables enable RLS');
SELECT ok(has_table_privilege('tlm_ingest', 'tlm.telemetry_messages', 'SELECT'),
          'backend can compare duplicate messages');
SELECT ok(NOT has_schema_privilege('anon', 'tlm', 'USAGE'), 'anon has no schema access');
SELECT ok(NOT has_schema_privilege('authenticated', 'tlm', 'USAGE'),
          'browser users have no schema access');
SELECT ok(NOT has_schema_privilege('service_role', 'tlm', 'USAGE'),
          'service_role is not the runtime identity');
SELECT ok(has_column_privilege('tlm_ingest', 'tlm.telemetry_messages', 'payload', 'INSERT'),
          'backend can insert payload');
SELECT ok(NOT has_column_privilege('tlm_ingest', 'tlm.telemetry_messages', 'received_at', 'INSERT'),
          'backend cannot supply server time');
SELECT ok(NOT has_table_privilege('tlm_ingest', 'tlm.telemetry_messages', 'UPDATE'),
          'backend cannot rewrite history');
SELECT ok(NOT has_table_privilege('tlm_ingest', 'tlm.telemetry_messages', 'DELETE'),
          'backend cannot delete history');
SELECT ok((SELECT NOT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls
                  AND NOT rolcreaterole AND NOT rolcreatedb
           FROM pg_roles WHERE rolname = 'tlm_ingest'), 'group role is unprivileged');
SELECT ok(EXISTS(SELECT 1 FROM pg_constraint
                 WHERE conrelid = 'tlm.telemetry_messages'::regclass
                   AND conname = 'telemetry_stream_sequence_uk' AND contype = 'u'),
          'stream positions are unique');
SELECT * FROM finish();
ROLLBACK;
