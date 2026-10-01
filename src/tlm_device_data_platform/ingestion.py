"""Bounded HTTP entry point for the laboratory ingestion service."""
from __future__ import annotations

import asyncio
import os
import re
from typing import Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from .telemetry_v1 import (
    MAX_BODY_BYTES, AuthenticationFailed, DeviceMismatch, IngestReceipt,
    InvalidTelemetry, MessageConflict, StorageUnavailable, TelemetryV1,
)

_TOKEN = re.compile(r"[A-Za-z0-9_-]{43,128}\Z")


class TelemetryRepository(Protocol):
    def accept(self, token: str, message: TelemetryV1) -> IngestReceipt:
        """Return only after commit, or raise without acknowledging delivery."""


async def _read_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "Message too large")
        body.extend(chunk)
    return bytes(body)


def create_app(repository: TelemetryRepository | None = None) -> FastAPI:
    if repository is None:
        from .postgres_ingestion import PostgresTelemetryRepository
        dsn = os.environ.get("TLM_DATABASE_DSN")
        if not dsn:
            raise RuntimeError("TLM_DATABASE_DSN is required")
        repository = PostgresTelemetryRepository(dsn)
    app = FastAPI(title="TLM laboratory ingestion v1")

    @app.get("/health/live")
    def live():
        # Liveness deliberately does not claim database readiness.
        return {"status": "alive"}

    @app.post("/v1/telemetry")
    async def ingest(request: Request):
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not _TOKEN.fullmatch(token):
            raise HTTPException(401, "Invalid device credential",
                                headers={"WWW-Authenticate": "Bearer"})
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            raise HTTPException(415, "Content-Type must be application/json")
        raw_length = request.headers.get("content-length")
        if raw_length is not None:
            if not raw_length.isascii() or not raw_length.isdigit() or len(raw_length) > 10:
                raise HTTPException(400, "Invalid Content-Length")
            if int(raw_length) > MAX_BODY_BYTES:
                raise HTTPException(413, "Message too large")
        try:
            body = await asyncio.wait_for(_read_body(request), timeout=10)
            message = TelemetryV1.parse(body)
            receipt = await run_in_threadpool(repository.accept, token, message)
        except (TimeoutError, ClientDisconnect):
            raise HTTPException(408, "Incomplete request") from None
        except InvalidTelemetry as error:
            raise HTTPException(422, str(error)) from None
        except AuthenticationFailed:
            raise HTTPException(401, "Invalid device credential",
                                headers={"WWW-Authenticate": "Bearer"}) from None
        except DeviceMismatch:
            raise HTTPException(403, "Credential does not authorize this device") from None
        except MessageConflict:
            raise HTTPException(409, "Message identity or stream position conflict") from None
        except StorageUnavailable:
            raise HTTPException(503, "Storage unavailable; retain and retry",
                                headers={"Retry-After": "5"}) from None
        return JSONResponse(status_code=200 if receipt.duplicate else 201, content={
            "status": "duplicate" if receipt.duplicate else "stored",
            "device_id": str(receipt.device_id), "message_id": str(receipt.message_id),
            "received_at": receipt.received_at.isoformat(),
        })

    return app
