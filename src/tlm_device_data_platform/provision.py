"""Operator-only provisioning; credentials go to exclusive mode-0600 files."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from .postgres_ingestion import validate_dsn
from .private_config import load_private_config, write_private_config


def provision_runtime(admin_dsn: str, output: Path, *, role: str = "tlm_api",
                      pooler_project_ref: str | None = None) -> None:
    validate_dsn(admin_dsn)
    if not re.fullmatch(r"tlm_api(?:_[a-z0-9_]{1,40})?", role):
        raise ValueError("Runtime role must be tlm_api or a tlm_api_ prefixed name")
    if pooler_project_ref is not None and not re.fullmatch(r"[a-z0-9]{1,64}", pooler_project_ref):
        raise ValueError("Invalid pooler project reference")
    password = secrets.token_urlsafe(32)
    wire_user = f"{role}.{pooler_project_ref}" if pooler_project_ref else role
    runtime_dsn = make_conninfo(admin_dsn, user=wire_user, password=password, options="")
    # Persist recovery material before any remote mutation. Never delete on ambiguous commit.
    write_private_config(output, {"TLM_DATABASE_DSN": runtime_dsn})
    with psycopg.connect(admin_dsn, connect_timeout=5) as db:
        db.execute(sql.SQL("CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOCREATEDB "
                           "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}")
                   .format(sql.Identifier(role), sql.Literal(password)))
        db.execute(sql.SQL("GRANT tlm_ingest TO {}").format(sql.Identifier(role)))


def provision_user_runtime(admin_dsn: str, output: Path, *, role='tlm_user_api',
                           pooler_project_ref=None):
    validate_dsn(admin_dsn)
    if not re.fullmatch(r'tlm_user_api(?:_[a-z0-9_]{1,40})?',role):
        raise ValueError('User runtime must use a tlm_user_api prefixed role')
    if pooler_project_ref is not None and not re.fullmatch(r'[a-z0-9]{1,64}',pooler_project_ref):
        raise ValueError('Invalid pooler project reference')
    password=secrets.token_urlsafe(32)
    wire_user=f'{role}.{pooler_project_ref}' if pooler_project_ref else role
    dsn=make_conninfo(admin_dsn,user=wire_user,password=password,options='')
    write_private_config(output,{'TLM_USER_DATABASE_DSN':dsn})
    with psycopg.connect(admin_dsn,connect_timeout=5) as db:
        db.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
        db.execute(sql.SQL('GRANT tlm_user TO {}').format(sql.Identifier(role)))


def bootstrap_admin(admin_dsn: str, user_id: UUID):
    validate_dsn(admin_dsn)
    with psycopg.connect(admin_dsn,connect_timeout=5) as db:
        db.execute('LOCK TABLE tlm.user_profiles IN SHARE ROW EXCLUSIVE MODE')
        if db.execute("SELECT 1 FROM tlm.user_profiles WHERE role='admin' AND status='approved'").fetchone():
            raise ValueError('An approved admin already exists; use the admin API')
        row=db.execute("UPDATE tlm.user_profiles SET role='admin',school_id=NULL,status='approved' WHERE user_id=%s AND status='pending' RETURNING user_id",(user_id,)).fetchone()
        if not row:
            raise ValueError('Bootstrap requires an explicitly identified pending Auth user')


def provision_device(admin_dsn: str, output: Path, *, system_type: str,
                     device_id: UUID | None = None) -> UUID:
    validate_dsn(admin_dsn)
    if not system_type.strip():
        raise ValueError("system_type must not be empty")
    device_id = device_id or uuid4()
    token = secrets.token_urlsafe(32)
    write_private_config(output, {"TLM_DEVICE_ID": str(device_id), "TLM_DEVICE_TOKEN": token})
    with psycopg.connect(admin_dsn, connect_timeout=5) as db:
        db.execute("INSERT INTO tlm.devices (device_id, system_type) VALUES (%s, %s)",
                   (device_id, system_type))
        db.execute("INSERT INTO tlm.device_credentials (device_id, token_sha256) VALUES (%s, %s)",
                   (device_id, hashlib.sha256(token.encode("ascii")).digest()))
    return device_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-config", type=Path, help="Private JSON with TLM_ADMIN_DSN")
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize this provisioning write")
    subparsers = parser.add_subparsers(dest="command", required=True)
    runtime = subparsers.add_parser("runtime")
    runtime.add_argument("--output", type=Path, required=True)
    runtime.add_argument("--role", default="tlm_api")
    runtime.add_argument("--pooler-project-ref")
    user_runtime = subparsers.add_parser('user-runtime')
    user_runtime.add_argument('--output',type=Path,required=True)
    user_runtime.add_argument('--role',default='tlm_user_api')
    user_runtime.add_argument('--pooler-project-ref')
    bootstrap = subparsers.add_parser('bootstrap-admin')
    bootstrap.add_argument('--user-id',type=UUID,required=True)
    device = subparsers.add_parser("device")
    device.add_argument("--output", type=Path, required=True)
    device.add_argument("--system-type", required=True)
    device.add_argument("--device-id", type=UUID)
    args = parser.parse_args()
    if not args.apply:
        parser.error("Provisioning changes the selected database; pass --apply explicitly")
    try:
        config = (load_private_config(args.admin_config, {"TLM_ADMIN_DSN"})
                  if args.admin_config else {})
        dsn = config.get("TLM_ADMIN_DSN") or os.environ.get("TLM_ADMIN_DSN")
        if not dsn:
            raise ValueError("TLM_ADMIN_DSN is required")
        if args.command == "runtime":
            provision_runtime(dsn, args.output, role=args.role,
                              pooler_project_ref=args.pooler_project_ref)
        elif args.command == 'user-runtime':
            provision_user_runtime(dsn,args.output,role=args.role,pooler_project_ref=args.pooler_project_ref)
        elif args.command == 'bootstrap-admin':
            bootstrap_admin(dsn,args.user_id)
        else:
            provision_device(dsn, args.output, system_type=args.system_type,
                             device_id=args.device_id)
        print("Provisioning committed. No credentials printed.")
        return 0
    except Exception as error:
        print(f"Provisioning failed ({type(error).__name__}). Any created configuration was retained. "
              "Inspect database state before retrying; do not overwrite existing credentials.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
