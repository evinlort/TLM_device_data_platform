"""Operator provisioning creates a separate runtime and bootstraps an existing user."""
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
import pytest

from .test_session_access import access
from tlm_device_data_platform.provision import provision_user_runtime, bootstrap_admin
from tlm_device_data_platform.private_config import load_private_config

pytestmark = pytest.mark.database


def test_separate_login_and_explicit_admin_bootstrap(access):
    a = access
    _, uid, _ = a['register']()
    dsn = __import__('os').environ['TLM_TEST_ADMIN_DSN']
    bootstrap_admin(dsn, uid)
    assert a['admin'].execute(
        'SELECT role,status FROM tlm.user_profiles WHERE user_id=%s', (uid,)).fetchone() == ('admin', 'approved')
    with pytest.raises(ValueError):
        bootstrap_admin(dsn, uid)
    output = a['tmp_path']/'user.secret.json'
    role = 'tlm_user_api_'+uuid4().hex
    try:
        provision_user_runtime(dsn, output, role=role)
        config = load_private_config(output, {'TLM_USER_DATABASE_DSN'})
        with psycopg.connect(config['TLM_USER_DATABASE_DSN']) as db:
            assert db.execute(
                "SELECT pg_has_role(current_user,'tlm_user','MEMBER'),pg_has_role(current_user,'tlm_ingest','MEMBER')").fetchone() == (True, False)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute('SELECT * FROM tlm.device_credentials')
    finally:
        a['admin'].execute(
            sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))
