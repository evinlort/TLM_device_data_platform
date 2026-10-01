"""Host TLS handshake test for the exact firmware HTTP client, not MCU hardware."""
import asyncio
import importlib.util
import ssl
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "firmware" / "esp32_micropython"


def test_real_tls_validates_ca_and_hostname(tmp_path):
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=localhost",
        "-addext", "subjectAltName=DNS:localhost",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    spec = importlib.util.spec_from_file_location("esp32_tls_client", ROOT / "tlm_http.py")
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)

    async def scenario():
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        async def handler(reader, writer):
            try:
                headers = await reader.readuntil(b"\r\n\r\n")
                size = int(headers.split(b"Content-Length: ")[1].split(b"\r\n")[0])
                await reader.readexactly(size)
                writer.write(b"HTTP/1.1 201 Created\r\nContent-Length: 2\r\n"
                             b"Content-Type: application/json\r\n\r\n{}")
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
        server = await asyncio.start_server(handler, "127.0.0.1", 0, ssl=context)
        port = server.sockets[0].getsockname()[1]
        try:
            trusted = client.HTTPTransport("https://localhost:%d/v1/telemetry" % port,
                                           "x" * 43, ca_file=str(cert))
            assert (await trusted.post(b"{}"))[0] == 201
            wrong_host = client.HTTPTransport("https://127.0.0.1:%d/v1/telemetry" % port,
                                              "x" * 43, ca_file=str(cert))
            with pytest.raises(ssl.SSLCertVerificationError):
                await wrong_host.post(b"{}")
            untrusted = client.HTTPTransport("https://localhost:%d/v1/telemetry" % port,
                                             "x" * 43, ca_file=str(cert))
            untrusted.context = ssl.create_default_context()
            with pytest.raises(ssl.SSLCertVerificationError):
                await untrusted.post(b"{}")
        finally:
            server.close()
            await server.wait_closed()
    asyncio.run(scenario())
