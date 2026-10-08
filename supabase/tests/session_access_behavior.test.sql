BEGIN;
CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;
SET LOCAL search_path = extensions, public;
SELECT no_plan();
GRANT tlm_user TO postgres;
GRANT USAGE ON SCHEMA extensions TO tlm_user;
SELECT is((SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='tlm' AND c.relkind='r' AND c.relrowsecurity),10::bigint,'Every application table uses RLS');
SELECT ok(NOT has_table_privilege('tlm_user','tlm.device_credentials','SELECT'),'User login cannot read device credentials');
SELECT ok(NOT pg_has_role('tlm_user','tlm_ingest','MEMBER'),'User role does not inherit ingestion');
SELECT ok(NOT has_schema_privilege('authenticated','tlm','USAGE'),'Private schema stays unexposed');
SELECT ok(NOT has_function_privilege('authenticated','tlm.start_session(uuid)','EXECUTE'),'Data API cannot start sessions');
INSERT INTO tlm.schools(school_id,name) VALUES
('10000000-0000-0000-0000-000000000001','TEST A'),('10000000-0000-0000-0000-000000000002','TEST B');
INSERT INTO auth.users(id,email,raw_user_meta_data) VALUES
('20000000-0000-0000-0000-000000000001','TEST-admin@example.com','{"role":"admin","status":"approved"}'),
('20000000-0000-0000-0000-000000000002','TEST-teacher@example.com','{}'),
('20000000-0000-0000-0000-000000000003','TEST-student@example.com','{}'),
('20000000-0000-0000-0000-000000000004','TEST-other@example.com','{}'),
('20000000-0000-0000-0000-000000000005','TEST-manager@example.com','{}'),
('20000000-0000-0000-0000-000000000006','TEST-pending@example.com','{}');
SELECT is((SELECT status FROM tlm.user_profiles WHERE user_id='20000000-0000-0000-0000-000000000001'),'pending','Metadata cannot approve registration');
SELECT is((SELECT role FROM tlm.user_profiles WHERE user_id='20000000-0000-0000-0000-000000000001'),NULL::text,'Metadata cannot set a role');
UPDATE tlm.user_profiles SET status='approved',role=CASE user_id
 WHEN '20000000-0000-0000-0000-000000000001' THEN 'admin'
 WHEN '20000000-0000-0000-0000-000000000002' THEN 'teacher'
 WHEN '20000000-0000-0000-0000-000000000005' THEN 'manager' ELSE 'student' END,
 school_id=CASE WHEN user_id IN ('20000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000003') THEN '10000000-0000-0000-0000-000000000001'::uuid
 WHEN user_id='20000000-0000-0000-0000-000000000004' THEN '10000000-0000-0000-0000-000000000002'::uuid END
 WHERE user_id <> '20000000-0000-0000-0000-000000000006';
INSERT INTO tlm.devices(device_id,system_type,school_id) VALUES
('30000000-0000-0000-0000-000000000001','TEST software','10000000-0000-0000-0000-000000000001');
INSERT INTO tlm.sessions(session_id,school_id,name,created_by) VALUES
('40000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','TEST session','20000000-0000-0000-0000-000000000002');
INSERT INTO tlm.session_participants VALUES ('40000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003');
INSERT INTO tlm.session_devices(session_id,device_id) VALUES ('40000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001');
SET LOCAL ROLE tlm_user;
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000002',true);
SELECT lives_ok($$SELECT tlm.start_session('40000000-0000-0000-0000-000000000001')$$,'Teacher starts own school session');
SELECT is((SELECT count(*) FROM tlm.sessions),1::bigint,'Teacher sees own school');
SELECT throws_ok($$DELETE FROM tlm.session_participants WHERE session_id='40000000-0000-0000-0000-000000000001'$$,'23514','Started session roster is immutable','Active roster is immutable');
SELECT throws_ok($$UPDATE tlm.sessions SET status='ended'$$,'42501','permission denied for table sessions','Direct lifecycle rewrite is forbidden');
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000003',true);
SELECT is((SELECT count(*) FROM tlm.sessions),1::bigint,'Student sees own session');
WITH changed AS (UPDATE tlm.user_profiles SET role='admin' WHERE user_id=tlm.actor_id() RETURNING 1)
 SELECT is((SELECT count(*) FROM changed),0::bigint,'Self elevation is denied by RLS');
SELECT throws_ok($$SELECT tlm.finish_session('40000000-0000-0000-0000-000000000001')$$,'42501','Session unavailable','Student cannot manage');
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000004',true);
SELECT is((SELECT count(*) FROM tlm.sessions),0::bigint,'Other student sees no foreign session');
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000006',true);
SELECT is((SELECT count(*) FROM tlm.sessions),0::bigint,'Pending user sees no sessions');
RESET ROLE;
INSERT INTO tlm.telemetry_messages(device_id,message_id,schema_version,stream_id,sequence_no,captured_at,payload)
 VALUES ('30000000-0000-0000-0000-000000000001',gen_random_uuid(),1,gen_random_uuid(),1,NULL,'{"test_sensor":1}');
INSERT INTO tlm.telemetry_messages(device_id,message_id,schema_version,stream_id,sequence_no,captured_at,payload,session_id)
 VALUES ('30000000-0000-0000-0000-000000000001',gen_random_uuid(),2,gen_random_uuid(),1,NULL,'{"test_sensor":2}','40000000-0000-0000-0000-000000000001');
SET LOCAL ROLE tlm_user;
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000003',true);
SELECT is((SELECT count(*) FROM tlm.telemetry_messages),1::bigint,'Student cannot read sessionless v1');
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000005',true);
SELECT is((SELECT count(*) FROM tlm.telemetry_messages),2::bigint,'Manager reads all history');
SELECT throws_ok($$SELECT tlm.finish_session('40000000-0000-0000-0000-000000000001')$$,'42501','Session unavailable','Manager cannot manage');
SELECT set_config('tlm.user_id','20000000-0000-0000-0000-000000000001',true);
SELECT is((SELECT count(*) FROM tlm.telemetry_messages),2::bigint,'Admin reads all history');
SELECT throws_ok($$UPDATE tlm.devices SET school_id='10000000-0000-0000-0000-000000000002'$$,'23514','Active device cannot change school','Active device school binding is fixed');
SELECT lives_ok($$SELECT tlm.finish_session('40000000-0000-0000-0000-000000000001')$$,'Admin finishes session');
RESET ROLE;
SELECT is((SELECT count(*) FROM tlm.active_device_sessions),0::bigint,'Finish releases device');
SELECT is((SELECT count(*) FROM tlm.session_devices),1::bigint,'Historical assignment is retained');
SELECT throws_ok($$DELETE FROM tlm.session_devices$$,'23514','Started session roster is immutable','Ended assignment is immutable even for owner');
SELECT is((SELECT revision FROM tlm.device_contexts WHERE device_id='30000000-0000-0000-0000-000000000001'),2::bigint,'Context revision advances at start and finish');
SELECT * FROM finish();
ROLLBACK;
