-- User/session access is separate from the trusted device ingestion login.
DO $role$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tlm_user') THEN
        CREATE ROLE tlm_user NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    ELSIF EXISTS (SELECT FROM pg_roles WHERE rolname = 'tlm_user' AND
        (rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
        OR pg_has_role('tlm_user', 'tlm_ingest', 'MEMBER') THEN
        RAISE EXCEPTION 'Existing tlm_user role is incompatible; review it';
    END IF;
END;
$role$;
GRANT USAGE ON SCHEMA tlm TO tlm_user;

CREATE TABLE tlm.schools (
    school_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200)
);
CREATE TABLE tlm.user_profiles (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE RESTRICT,
    email text NOT NULL,
    role text CHECK (role IN ('student', 'teacher', 'manager', 'admin')),
    school_id uuid REFERENCES tlm.schools ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'disabled')),
    CHECK (status <> 'pending' OR (role IS NULL AND school_id IS NULL)),
    CHECK (status <> 'approved' OR (role IS NOT NULL AND
        (role NOT IN ('student', 'teacher') OR school_id IS NOT NULL)))
);
CREATE FUNCTION tlm.new_user_profile() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = pg_catalog, tlm AS $$
BEGIN
    INSERT INTO tlm.user_profiles(user_id, email) VALUES (NEW.id, coalesce(NEW.email, ''));
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION tlm.new_user_profile() FROM PUBLIC;
CREATE TRIGGER tlm_new_auth_user AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION tlm.new_user_profile();
-- Existing Auth users also start pending; metadata is never an authorization source.
INSERT INTO tlm.user_profiles(user_id, email) SELECT id, coalesce(email, '') FROM auth.users;

ALTER TABLE tlm.devices ADD COLUMN school_id uuid REFERENCES tlm.schools ON DELETE RESTRICT;
CREATE TABLE tlm.sessions (
    session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id uuid NOT NULL REFERENCES tlm.schools ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
    created_by uuid NOT NULL REFERENCES tlm.user_profiles ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'ended')),
    started_at timestamptz,
    ended_at timestamptz,
    CHECK ((status = 'draft' AND started_at IS NULL AND ended_at IS NULL) OR
           (status = 'active' AND started_at IS NOT NULL AND ended_at IS NULL) OR
           (status = 'ended' AND started_at IS NOT NULL AND ended_at IS NOT NULL))
);
CREATE TABLE tlm.session_participants (
    session_id uuid NOT NULL REFERENCES tlm.sessions ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES tlm.user_profiles ON DELETE RESTRICT,
    PRIMARY KEY(session_id, user_id)
);
CREATE TABLE tlm.session_devices (
    session_id uuid NOT NULL REFERENCES tlm.sessions ON DELETE RESTRICT,
    device_id uuid NOT NULL REFERENCES tlm.devices ON DELETE RESTRICT,
    context_revision bigint,
    PRIMARY KEY(session_id, device_id)
);
CREATE TABLE tlm.active_device_sessions (
    device_id uuid PRIMARY KEY REFERENCES tlm.devices ON DELETE RESTRICT,
    session_id uuid NOT NULL,
    FOREIGN KEY(session_id, device_id) REFERENCES tlm.session_devices ON DELETE RESTRICT
);
CREATE TABLE tlm.device_contexts (
    device_id uuid PRIMARY KEY REFERENCES tlm.devices ON DELETE CASCADE,
    session_id uuid REFERENCES tlm.sessions ON DELETE RESTRICT,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0)
);
INSERT INTO tlm.device_contexts(device_id) SELECT device_id FROM tlm.devices;
CREATE FUNCTION tlm.new_device_context() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = pg_catalog, tlm AS $$
BEGIN
    INSERT INTO tlm.device_contexts(device_id) VALUES (NEW.device_id);
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION tlm.new_device_context() FROM PUBLIC;
CREATE TRIGGER tlm_new_device AFTER INSERT ON tlm.devices
FOR EACH ROW EXECUTE FUNCTION tlm.new_device_context();

ALTER TABLE tlm.telemetry_messages DROP CONSTRAINT telemetry_messages_schema_version_check;
ALTER TABLE tlm.telemetry_messages ADD COLUMN session_id uuid;
ALTER TABLE tlm.telemetry_messages ADD CHECK (schema_version IN (1, 2));
ALTER TABLE tlm.telemetry_messages ADD CHECK (schema_version <> 1 OR session_id IS NULL);
ALTER TABLE tlm.telemetry_messages ADD CONSTRAINT telemetry_session_device_fk
    FOREIGN KEY(session_id, device_id) REFERENCES tlm.session_devices ON DELETE RESTRICT;
CREATE INDEX telemetry_session_received_idx ON tlm.telemetry_messages(session_id, received_at, device_id, message_id);
GRANT INSERT(session_id) ON tlm.telemetry_messages TO tlm_ingest;
GRANT SELECT ON tlm.device_contexts, tlm.session_devices TO tlm_ingest;

CREATE FUNCTION tlm.actor_id() RETURNS uuid LANGUAGE sql STABLE
SET search_path = pg_catalog AS $$ SELECT nullif(current_setting('tlm.user_id', true), '')::uuid $$;
CREATE FUNCTION tlm.actor_role() RETURNS text LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, tlm AS $$
    SELECT role FROM tlm.user_profiles WHERE user_id = tlm.actor_id() AND status = 'approved'
$$;
CREATE FUNCTION tlm.can_manage_school(target uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, tlm AS $$
    SELECT coalesce(EXISTS (SELECT FROM tlm.user_profiles WHERE user_id = tlm.actor_id()
        AND status = 'approved' AND (role = 'admin' OR (role = 'teacher' AND school_id = target))), false)
$$;
CREATE FUNCTION tlm.can_read_session(target uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, tlm AS $$
    SELECT EXISTS (SELECT FROM tlm.sessions s JOIN tlm.user_profiles p ON p.user_id = tlm.actor_id()
      WHERE s.session_id = target AND p.status = 'approved' AND
        (p.role IN ('admin', 'manager') OR (p.role = 'teacher' AND p.school_id = s.school_id) OR
         (p.role = 'student' AND EXISTS (SELECT FROM tlm.session_participants m
              WHERE m.session_id = target AND m.user_id = p.user_id))))
$$;

CREATE FUNCTION tlm.guard_roster() RETURNS trigger LANGUAGE plpgsql
SET search_path = pg_catalog, tlm AS $$
DECLARE target uuid; school uuid; state text;
BEGIN
    target := CASE WHEN TG_OP = 'DELETE' THEN OLD.session_id ELSE NEW.session_id END;
    SELECT school_id, status INTO school, state FROM tlm.sessions WHERE session_id = target FOR UPDATE;
    IF state IS DISTINCT FROM 'draft' THEN
        RAISE EXCEPTION 'Started session roster is immutable' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.session_id <> OLD.session_id THEN
        RAISE EXCEPTION 'Assignment cannot change session' USING ERRCODE = '23514';
    END IF;
    IF TG_OP <> 'DELETE' THEN
        IF TG_TABLE_NAME = 'session_participants' THEN
            IF NOT EXISTS (SELECT FROM tlm.user_profiles WHERE user_id = NEW.user_id
                AND status = 'approved' AND role = 'student' AND school_id = school) THEN
                RAISE EXCEPTION 'Participant must be an approved student of the session school' USING ERRCODE = '23514';
            END IF;
        ELSE
            IF NOT EXISTS (SELECT FROM tlm.devices WHERE device_id = NEW.device_id
                AND is_active AND school_id = school) THEN
                RAISE EXCEPTION 'Device must belong to the session school' USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER guard_participants BEFORE INSERT OR UPDATE OR DELETE ON tlm.session_participants
    FOR EACH ROW EXECUTE FUNCTION tlm.guard_roster();
CREATE TRIGGER guard_session_devices BEFORE INSERT OR UPDATE OR DELETE ON tlm.session_devices
    FOR EACH ROW EXECUTE FUNCTION tlm.guard_roster();

CREATE FUNCTION tlm.guard_device_school() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = pg_catalog, tlm AS $$
BEGIN
    IF NEW.school_id IS DISTINCT FROM OLD.school_id AND EXISTS
        (SELECT FROM tlm.active_device_sessions WHERE device_id = OLD.device_id) THEN
        RAISE EXCEPTION 'Active device cannot change school' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_device_school BEFORE UPDATE ON tlm.devices FOR EACH ROW EXECUTE FUNCTION tlm.guard_device_school();

CREATE FUNCTION tlm.start_session(target uuid) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, tlm AS $$
DECLARE s tlm.sessions; d record; rev bigint;
BEGIN
    SELECT * INTO s FROM tlm.sessions WHERE session_id = target FOR UPDATE;
    IF s.session_id IS NULL OR NOT tlm.can_manage_school(s.school_id) THEN
        RAISE EXCEPTION 'Session unavailable' USING ERRCODE = '42501';
    END IF;
    IF s.status <> 'draft' THEN RAISE EXCEPTION 'Session is not draft' USING ERRCODE = '23514'; END IF;
    IF NOT EXISTS (SELECT FROM tlm.session_participants WHERE session_id = target) OR
       NOT EXISTS (SELECT FROM tlm.session_devices WHERE session_id = target) THEN
        RAISE EXCEPTION 'Session requires students and devices' USING ERRCODE = '23514';
    END IF;
    -- Recheck students under a lock; profile changes cannot race the snapshot.
    PERFORM 1 FROM tlm.user_profiles p JOIN tlm.session_participants m USING(user_id)
        WHERE m.session_id = target ORDER BY p.user_id FOR UPDATE OF p;
    IF EXISTS (SELECT FROM tlm.session_participants m JOIN tlm.user_profiles p USING(user_id)
        WHERE m.session_id = target AND (p.status <> 'approved' OR p.role <> 'student' OR p.school_id <> s.school_id)) THEN
        RAISE EXCEPTION 'Invalid participant at start' USING ERRCODE = '23514';
    END IF;
    FOR d IN SELECT dev.* FROM tlm.devices dev JOIN tlm.session_devices m USING(device_id)
             WHERE m.session_id = target ORDER BY dev.device_id FOR UPDATE OF dev LOOP
        IF NOT d.is_active OR d.school_id IS DISTINCT FROM s.school_id THEN
            RAISE EXCEPTION 'Invalid device at start' USING ERRCODE = '23514';
        END IF;
        INSERT INTO tlm.active_device_sessions(device_id, session_id) VALUES (d.device_id, target);
        UPDATE tlm.device_contexts SET session_id = target, revision = revision + 1
            WHERE device_id = d.device_id RETURNING revision INTO rev;
        UPDATE tlm.session_devices SET context_revision = rev WHERE session_id = target AND device_id = d.device_id;
    END LOOP;
    UPDATE tlm.sessions SET status = 'active', started_at = clock_timestamp() WHERE session_id = target;
END $$;
CREATE FUNCTION tlm.finish_session(target uuid) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, tlm AS $$
DECLARE s tlm.sessions; d record;
BEGIN
    SELECT * INTO s FROM tlm.sessions WHERE session_id = target FOR UPDATE;
    IF s.session_id IS NULL OR NOT tlm.can_manage_school(s.school_id) THEN
        RAISE EXCEPTION 'Session unavailable' USING ERRCODE = '42501';
    END IF;
    IF s.status <> 'active' THEN RAISE EXCEPTION 'Session is not active' USING ERRCODE = '23514'; END IF;
    FOR d IN SELECT dev.device_id FROM tlm.devices dev JOIN tlm.active_device_sessions a USING(device_id)
        WHERE a.session_id = target ORDER BY dev.device_id FOR UPDATE OF dev LOOP
        UPDATE tlm.device_contexts SET session_id = NULL, revision = revision + 1 WHERE device_id = d.device_id;
    END LOOP;
    DELETE FROM tlm.active_device_sessions WHERE session_id = target;
    UPDATE tlm.sessions SET status = 'ended', ended_at = clock_timestamp() WHERE session_id = target;
END $$;

-- Explicit function privileges: no Data API execution or default PUBLIC execute.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA tlm FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION tlm.actor_id(), tlm.actor_role(), tlm.can_manage_school(uuid),
    tlm.can_read_session(uuid), tlm.start_session(uuid), tlm.finish_session(uuid) TO tlm_user;
GRANT SELECT ON tlm.schools, tlm.user_profiles, tlm.sessions, tlm.session_participants,
    tlm.session_devices, tlm.device_contexts, tlm.telemetry_messages TO tlm_user;
GRANT SELECT(device_id, system_type, is_active, school_id, created_at) ON tlm.devices TO tlm_user;
GRANT INSERT(name), UPDATE(name) ON tlm.schools TO tlm_user;
GRANT UPDATE(role, school_id, status) ON tlm.user_profiles TO tlm_user;
GRANT UPDATE(school_id) ON tlm.devices TO tlm_user;
GRANT INSERT(school_id, name, created_by), UPDATE(name) ON tlm.sessions TO tlm_user;
GRANT INSERT(session_id, user_id), DELETE ON tlm.session_participants TO tlm_user;
GRANT INSERT(session_id, device_id), DELETE ON tlm.session_devices TO tlm_user;

ALTER TABLE tlm.schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.session_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.session_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.active_device_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tlm.device_contexts ENABLE ROW LEVEL SECURITY;
CREATE POLICY schools_read ON tlm.schools FOR SELECT TO tlm_user USING (
    tlm.actor_role() IN ('admin', 'manager') OR EXISTS
    (SELECT FROM tlm.user_profiles WHERE user_id = tlm.actor_id() AND status = 'approved' AND school_id = schools.school_id));
CREATE POLICY schools_admin ON tlm.schools FOR ALL TO tlm_user USING (tlm.actor_role() = 'admin') WITH CHECK (tlm.actor_role() = 'admin');
CREATE POLICY profiles_read ON tlm.user_profiles FOR SELECT TO tlm_user USING (
    user_id = tlm.actor_id() OR tlm.actor_role() = 'admin' OR
    (role = 'student' AND tlm.can_manage_school(school_id)));
CREATE POLICY profiles_admin ON tlm.user_profiles FOR UPDATE TO tlm_user USING (tlm.actor_role() = 'admin') WITH CHECK (tlm.actor_role() = 'admin');
CREATE POLICY sessions_read ON tlm.sessions FOR SELECT TO tlm_user USING (tlm.actor_role() IN ('admin', 'manager') OR tlm.can_manage_school(school_id) OR tlm.can_read_session(session_id));
CREATE POLICY sessions_create ON tlm.sessions FOR INSERT TO tlm_user WITH CHECK (created_by = tlm.actor_id() AND tlm.can_manage_school(school_id));
CREATE POLICY sessions_update ON tlm.sessions FOR UPDATE TO tlm_user USING (status = 'draft' AND tlm.can_manage_school(school_id)) WITH CHECK (status = 'draft' AND tlm.can_manage_school(school_id));
CREATE POLICY participants_read ON tlm.session_participants FOR SELECT TO tlm_user USING (tlm.can_read_session(session_id));
CREATE POLICY participants_write ON tlm.session_participants FOR ALL TO tlm_user USING (
    EXISTS (SELECT FROM tlm.sessions s WHERE s.session_id = session_participants.session_id AND tlm.can_manage_school(s.school_id))) WITH CHECK (
    EXISTS (SELECT FROM tlm.sessions s WHERE s.session_id = session_participants.session_id AND tlm.can_manage_school(s.school_id)));
CREATE POLICY assignments_read ON tlm.session_devices FOR SELECT TO tlm_user USING (tlm.can_read_session(session_id));
CREATE POLICY assignments_write ON tlm.session_devices FOR ALL TO tlm_user USING (
    EXISTS (SELECT FROM tlm.sessions s WHERE s.session_id = session_devices.session_id AND tlm.can_manage_school(s.school_id))) WITH CHECK (
    EXISTS (SELECT FROM tlm.sessions s WHERE s.session_id = session_devices.session_id AND tlm.can_manage_school(s.school_id)));
CREATE POLICY devices_user_read ON tlm.devices FOR SELECT TO tlm_user USING (tlm.actor_role() = 'admin' OR tlm.can_manage_school(school_id));
CREATE POLICY devices_admin ON tlm.devices FOR UPDATE TO tlm_user USING (tlm.actor_role() = 'admin') WITH CHECK (tlm.actor_role() = 'admin');
CREATE POLICY contexts_user_read ON tlm.device_contexts FOR SELECT TO tlm_user USING (EXISTS (SELECT FROM tlm.devices d WHERE d.device_id = device_contexts.device_id));
CREATE POLICY contexts_ingest_read ON tlm.device_contexts FOR SELECT TO tlm_ingest USING (true);
CREATE POLICY assignments_ingest_read ON tlm.session_devices FOR SELECT TO tlm_ingest USING (true);
CREATE POLICY telemetry_user_read ON tlm.telemetry_messages FOR SELECT TO tlm_user USING (
    tlm.actor_role() IN ('admin', 'manager') OR (session_id IS NOT NULL AND tlm.can_read_session(session_id)));
