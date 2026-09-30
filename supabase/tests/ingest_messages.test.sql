BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;
SET LOCAL search_path = extensions, public;

SELECT plan(18);

SELECT has_table(
  'public',
  'ingest_messages',
  'ingest_messages table exists'
);
SELECT columns_are(
  'public',
  'ingest_messages',
  ARRAY['id', 'body'],
  'ingest_messages has only the approved columns'
);
SELECT col_type_is(
  'public',
  'ingest_messages',
  'id',
  'bigint',
  'id is bigint'
);
SELECT col_is_pk(
  'public',
  'ingest_messages',
  'id',
  'id is the primary key'
);
SELECT col_not_null(
  'public',
  'ingest_messages',
  'id',
  'id is not null'
);
SELECT is(
  (
    SELECT identity_generation
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'ingest_messages'
      AND column_name = 'id'
  ),
  'ALWAYS',
  'id is generated always as identity'
);
SELECT col_type_is(
  'public',
  'ingest_messages',
  'body',
  'bytea',
  'body is bytea'
);
SELECT col_not_null(
  'public',
  'ingest_messages',
  'body',
  'body is not null'
);
SELECT ok(
  (
    SELECT relrowsecurity
    FROM pg_catalog.pg_class
    WHERE oid = 'public.ingest_messages'::regclass
  ),
  'row level security is enabled'
);
SELECT policies_are(
  'public',
  'ingest_messages',
  ARRAY[]::text[],
  'ingest_messages has no RLS policies'
);
SELECT ok(
  NOT has_table_privilege('anon', 'public.ingest_messages', 'SELECT'),
  'anon cannot select ingest messages'
);
SELECT ok(
  NOT has_table_privilege('anon', 'public.ingest_messages', 'INSERT'),
  'anon cannot insert ingest messages'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.ingest_messages', 'SELECT'),
  'authenticated cannot select ingest messages'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.ingest_messages', 'INSERT'),
  'authenticated cannot insert ingest messages'
);
SELECT ok(
  has_table_privilege('service_role', 'public.ingest_messages', 'INSERT'),
  'service_role can insert ingest messages'
);

INSERT INTO public.ingest_messages (body)
VALUES (decode('00ff', 'hex')),
       (decode('', 'hex')),
       (decode('00ff', 'hex'));

SELECT results_eq(
  $$SELECT encode(body, 'hex') FROM public.ingest_messages ORDER BY id LIMIT 1$$,
  $$VALUES ('00ff'::text)$$,
  'opaque bytes round-trip exactly'
);
SELECT results_eq(
  $$SELECT count(*) FROM public.ingest_messages WHERE octet_length(body) = 0$$,
  $$VALUES (1::bigint)$$,
  'empty bytea is allowed'
);
SELECT results_eq(
  $$SELECT count(*) FROM public.ingest_messages WHERE body = decode('00ff', 'hex')$$,
  $$VALUES (2::bigint)$$,
  'duplicate bodies are allowed'
);

SELECT * FROM finish();
ROLLBACK;
