"""Start the laboratory API with explicit private configuration and TLS options."""
import argparse
import logging
import os
from pathlib import Path

from urllib.parse import urlsplit

import uvicorn

from .ingestion import create_app
from .postgres_ingestion import PostgresTelemetryRepository
from .private_config import load_private_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--ssl-certfile")
    parser.add_argument("--ssl-keyfile")
    parser.add_argument("--allow-insecure-lan", action="store_true")
    args = parser.parse_args()
    if bool(args.ssl_certfile) != bool(args.ssl_keyfile):
        parser.error("Both TLS certificate and private key are required")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.ssl_certfile and not args.allow_insecure_lan:
        parser.error("Non-loopback listeners require TLS or explicit --allow-insecure-lan")
    try:
        keys = {'TLM_DATABASE_DSN','TLM_USER_DATABASE_DSN','TLM_SUPABASE_URL','TLM_SUPABASE_KEY','TLM_PUBLIC_ORIGIN'}
        config = load_private_config(args.config, keys) if args.config else {}
        for key in keys:
            if key not in config and os.environ.get(key):
                config[key] = os.environ[key]
        dsn = config.get("TLM_DATABASE_DSN") or os.environ.get("TLM_DATABASE_DSN")
        if not dsn:
            raise ValueError("TLM_DATABASE_DSN is required")
        user_keys = keys - {'TLM_DATABASE_DSN'}
        if any(config.get(key) for key in user_keys):
            if not all(config.get(key) for key in user_keys):
                raise ValueError('Complete user runtime, Auth and public origin configuration is required')
            from .user_access import UserRepository, SupabaseAuth
            origin = urlsplit(config['TLM_PUBLIC_ORIGIN'])
            if (origin.scheme not in ('http','https') or not origin.hostname or origin.path or
                    origin.username or origin.password or origin.query or origin.fragment or
                    (origin.scheme == 'http' and origin.hostname not in {'127.0.0.1','localhost','::1'} and not args.allow_insecure_lan)):
                raise ValueError('Public origin requires HTTPS or the explicit isolated-lab HTTP option')
            app = create_app(PostgresTelemetryRepository(dsn),
                user_repository=UserRepository(config['TLM_USER_DATABASE_DSN']),
                auth_provider=SupabaseAuth(config['TLM_SUPABASE_URL'],config['TLM_SUPABASE_KEY'],allow_insecure_local=True),
                cookie_secure=origin.scheme == 'https',public_origin=config['TLM_PUBLIC_ORIGIN'])
        else:
            app = create_app(PostgresTelemetryRepository(dsn))
        uvicorn.run(app, host=args.host, port=args.port, ssl_certfile=args.ssl_certfile,
                    ssl_keyfile=args.ssl_keyfile, access_log=False, proxy_headers=False,
                    limit_concurrency=32, timeout_keep_alive=5)
        return 0
    except Exception as error:
        logging.error("API startup failed (%s); configuration not printed", type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
