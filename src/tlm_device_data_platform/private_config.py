"""Read and create owner-only JSON configuration without printing credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Mapping


def load_private_config(path: Path, allowed_keys: set[str]) -> dict[str, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            raise ValueError("Configuration must be a small regular file")
        if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise PermissionError("Configuration must be owned by this user with mode 0600")
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Configuration is too large")
    try:
        values = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError("Invalid JSON configuration") from None
    if (not isinstance(values, dict) or not set(values) <= allowed_keys
            or any(not isinstance(value, str) or not value for value in values.values())):
        raise ValueError("Unexpected or empty configuration values")
    return values


def write_private_config(path: Path, values: Mapping[str, str]) -> None:
    """Refuse overwrites; preserve recovery material if later DB commit is uncertain."""
    path = Path(path)
    # Persist new ancestor entries too when mkdir creates a directory chain.
    directories = [path.parent]
    while not directories[-1].exists():
        directories.append(directories[-1].parent)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(dict(values), stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    for directory in directories:
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
