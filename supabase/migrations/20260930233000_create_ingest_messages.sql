CREATE TABLE public.ingest_messages (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  body bytea NOT NULL
);

COMMENT ON TABLE public.ingest_messages IS
  'Opaque messages accepted by the provider-independent backend storage boundary.';
COMMENT ON COLUMN public.ingest_messages.id IS
  'Internal surrogate key only; it does not define product message ordering.';
COMMENT ON COLUMN public.ingest_messages.body IS
  'Opaque bytes; their contents do not define the production telemetry contract.';

ALTER TABLE public.ingest_messages ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.ingest_messages
FROM PUBLIC, anon, authenticated, service_role;
GRANT INSERT ON TABLE public.ingest_messages TO service_role;

REVOKE ALL ON SEQUENCE public.ingest_messages_id_seq
FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SEQUENCE public.ingest_messages_id_seq TO service_role;
