"""Start the laboratory API with explicit private configuration and TLS options."""
import argparse
import logging
import os
from pathlib import Path

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
        config = load_private_config(args.config, {"TLM_DATABASE_DSN"}) if args.config else {}
        dsn = config.get("TLM_DATABASE_DSN") or os.environ.get("TLM_DATABASE_DSN")
        if not dsn:
            raise ValueError("TLM_DATABASE_DSN is required")
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
