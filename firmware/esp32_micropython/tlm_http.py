"""Small bounded HTTP/1.1 client for MicroPython asyncio, with mandatory TLS by default."""
import asyncio
import ssl

MAX_HEADERS = 8192
MAX_RESPONSE = 2048
_TOKEN_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"


def _ipv4_octets(host):
    if not isinstance(host, str):
        return None
    pieces = host.split(".")
    if len(pieces) != 4 or any(
            not 1 <= len(p) <= 3 or (len(p) > 1 and p[0] == "0")
            or any(c not in "0123456789" for c in p) for p in pieces):
        return None
    numbers = [int(p) for p in pieces]
    return numbers if all(n <= 255 for n in numbers) else None


def _private_ipv4(host):
    numbers = _ipv4_octets(host)
    if numbers is None:
        return False
    return (numbers[0] in (10, 127) or numbers[:2] == [192, 168]
            or (numbers[0] == 172 and 16 <= numbers[1] <= 31))


def _endpoint(url, allow_http):
    if not isinstance(url, str) or len(url) > 512 or any(ord(c) <= 32 or ord(c) > 126 for c in url):
        raise ValueError("Invalid API URL")
    if url.startswith("https://"):
        secure, authority = True, url[8:]
    elif allow_http and url.startswith("http://"):
        secure, authority = False, url[7:]
    else:
        raise ValueError("HTTPS is required")
    parts = authority.split("/", 1)
    if len(parts) != 2 or parts[1] != "v1/telemetry":
        raise ValueError("Expected /v1/telemetry without query or fragment")
    authority = parts[0]
    pieces = authority.split(":")
    if len(pieces) > 2:
        raise ValueError("This pilot supports DNS names and IPv4 only")
    host = pieces[0]
    if (not host or len(host) > 253
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in host)):
        raise ValueError("Invalid API host")
    port = 443 if secure else 80
    if len(pieces) == 2:
        if not pieces[1] or any(c not in "0123456789" for c in pieces[1]):
            raise ValueError("Invalid port")
        port = int(pieces[1])
    if not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    if not secure and not _private_ipv4(host):
        raise ValueError("Opt-in HTTP is restricted to private/loopback IPv4")
    return secure, host, port, authority


async def _line(reader, remaining):
    result = bytearray()
    while len(result) < remaining:
        char = await reader.read(1)
        if not char:
            raise EOFError("Incomplete HTTP headers")
        result.extend(char)
        if result[-2:] == b"\r\n":
            return bytes(result)
    raise ValueError("HTTP headers too large")


async def _response(reader):
    first = await _line(reader, 256)
    parts = first.decode("ascii").strip().split(" ", 2)
    if len(parts) < 2 or parts[0] not in ("HTTP/1.0", "HTTP/1.1"):
        raise ValueError("Invalid HTTP status")
    status = int(parts[1])
    if not 100 <= status <= 599:
        raise ValueError("Invalid HTTP status")
    total, headers = len(first), {}
    while True:
        line = await _line(reader, MAX_HEADERS - total)
        total += len(line)
        if line == b"\r\n":
            break
        key, sep, value = line.decode("ascii").partition(":")
        key = key.lower()
        if not sep or not key or key in headers or key.strip() != key:
            raise ValueError("Invalid or duplicate HTTP header")
        headers[key] = value.strip()
    if "transfer-encoding" in headers:
        if "content-length" in headers or headers["transfer-encoding"].lower() != "chunked":
            raise ValueError("Ambiguous HTTP framing")
        body = bytearray()
        while True:
            line = await _line(reader, 128)
            size = int(line.strip().split(b";", 1)[0], 16)
            if size < 0 or len(body) + size > MAX_RESPONSE:
                raise ValueError("Response too large")
            if size == 0:
                total = 0
                while True:
                    trailer = await _line(reader, MAX_HEADERS - total)
                    total += len(trailer)
                    if trailer == b"\r\n":
                        return status, headers, bytes(body)
            body.extend(await reader.readexactly(size))
            if await reader.readexactly(2) != b"\r\n":
                raise ValueError("Invalid chunk terminator")
    if "content-length" in headers:
        length = headers["content-length"]
        if not length or len(length) > 6 or any(c not in "0123456789" for c in length):
            raise ValueError("Invalid response length")
        size = int(length)
        if size > MAX_RESPONSE:
            raise ValueError("Response too large")
        body = await reader.readexactly(size)
    else:
        body = bytearray()
        while True:
            chunk = await reader.read(min(256, MAX_RESPONSE + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_RESPONSE:
                raise ValueError("Response too large")
        body = bytes(body)
    return status, headers, body


class HTTPTransport:
    def __init__(self, url, token, ca_file=None, allow_insecure_http=False,
                 ssl_module=ssl, connector=None, resolver=None):
        self.secure, self.host, self.port, self.authority = _endpoint(url, allow_insecure_http)
        if (not isinstance(token, str) or not 43 <= len(token) <= 128
                or any(c not in _TOKEN_CHARS for c in token)):
            raise ValueError("Invalid device token")
        self.token = token
        self.connector = connector or asyncio.open_connection
        self.resolver = resolver
        self.context = None
        if self.secure:
            if not ca_file:
                raise ValueError("A trusted CA file is required")
            self.context = ssl_module.SSLContext(ssl_module.PROTOCOL_TLS_CLIENT)
            self.context.verify_mode = ssl_module.CERT_REQUIRED
            self.context.load_verify_locations(cafile=ca_file)

    async def post(self, body):
        if not isinstance(body, bytes) or not 0 < len(body) <= 8192:
            raise ValueError("Invalid request body")
        return await asyncio.wait_for(self._post(body), 10)

    async def _post(self, body):
        writer = None
        try:
            options = {}
            if self.secure:
                options = {"ssl": self.context, "server_hostname": self.host}
            connect_host = self.host
            if self.resolver is not None and _ipv4_octets(connect_host) is None:
                connect_host = await self.resolver(self.host, self.port)
                if _ipv4_octets(connect_host) is None:
                    raise ValueError("Resolver must return canonical IPv4")
            # On ESP32, the injected worker does DNS. A numeric address here
            # avoids a second network lookup while preserving TLS SNI and Host.
            reader, writer = await self.connector(connect_host, self.port, **options)
            headers = (
                "POST /v1/telemetry HTTP/1.1\r\nHost: %s\r\n"
                "Authorization: Bearer %s\r\nContent-Type: application/json\r\n"
                "Accept: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
            ) % (self.authority, self.token, len(body))
            writer.write(headers.encode("ascii") + body)
            await writer.drain()
            return await _response(reader)
        finally:
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), 1)
                except (OSError, asyncio.TimeoutError):
                    pass
