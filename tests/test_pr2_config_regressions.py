"""Linux durability barriers and fail-closed recovery-file handling."""
import errno
import json
import os
from pathlib import Path
import stat

import pytest

from tlm_device_data_platform import private_config


@pytest.mark.parametrize("depth", [0, 1, 3])
@pytest.mark.parametrize("relative", [False, True], ids=["absolute", "relative"])
def test_file_then_new_directory_chain_are_synced(tmp_path, monkeypatch, depth, relative):
    monkeypatch.chdir(tmp_path)
    root = Path(".") if relative else tmp_path
    parent = root.joinpath(*[f"level{i}" for i in range(depth)])
    output = parent / "device.secret.json"
    expected_directories = [parent]
    for _ in range(depth):
        expected_directories.append(expected_directories[-1].parent)
    events, streams = [], []
    real_fsync, real_fdopen = os.fsync, os.fdopen

    def record_fdopen(*args, **kwargs):
        stream = real_fdopen(*args, **kwargs)
        streams.append(stream)
        return stream

    def record_fsync(descriptor):
        info = os.fstat(descriptor)
        if stat.S_ISDIR(info.st_mode):
            assert streams[0].closed, "File must be closed before the directory barrier"
            events.append(("directory", info.st_dev, info.st_ino))
        else:
            assert stat.S_ISREG(info.st_mode)
            assert json.loads(output.read_text()) == {"TLM_DEVICE_TOKEN": "test-only"}
            events.append(("file", info.st_dev, info.st_ino))
        real_fsync(descriptor)

    monkeypatch.setattr(private_config.os, "fdopen", record_fdopen)
    monkeypatch.setattr(private_config.os, "fsync", record_fsync)
    private_config.write_private_config(output, {"TLM_DEVICE_TOKEN": "test-only"})
    expected = [("file", output.stat().st_dev, output.stat().st_ino)]
    expected += [("directory", p.stat().st_dev, p.stat().st_ino) for p in expected_directories]
    assert events == expected
    assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("fault", ["file_sync", "directory_open", "directory_sync"])
def test_durability_failure_propagates_retains_file_and_closes_descriptors(tmp_path, monkeypatch, fault):
    output = tmp_path / "device.secret.json"
    real_open, real_fsync, real_fdopen = os.open, os.fsync, os.fdopen
    directory_descriptors, streams = [], []
    failure = OSError(errno.EIO, "test durability failure")

    def checked_open(path, flags, *args, **kwargs):
        is_directory = bool(flags & os.O_DIRECTORY)
        if is_directory and fault == "directory_open":
            raise failure
        descriptor = real_open(path, flags, *args, **kwargs)
        if is_directory:
            directory_descriptors.append(descriptor)
        return descriptor

    def checked_fsync(descriptor):
        is_directory = stat.S_ISDIR(os.fstat(descriptor).st_mode)
        if (is_directory and fault == "directory_sync") or (not is_directory and fault == "file_sync"):
            raise failure
        real_fsync(descriptor)

    def record_fdopen(*args, **kwargs):
        stream = real_fdopen(*args, **kwargs)
        streams.append(stream)
        return stream

    monkeypatch.setattr(private_config.os, "open", checked_open)
    monkeypatch.setattr(private_config.os, "fsync", checked_fsync)
    monkeypatch.setattr(private_config.os, "fdopen", record_fdopen)
    with pytest.raises(OSError) as caught:
        private_config.write_private_config(output, {"TLM_DEVICE_TOKEN": "test-only"})
    assert caught.value is failure
    assert json.loads(output.read_text()) == {"TLM_DEVICE_TOKEN": "test-only"}
    assert all(stream.closed for stream in streams)
    for descriptor in directory_descriptors:
        with pytest.raises(OSError) as closed:
            os.fstat(descriptor)
        assert closed.value.errno == errno.EBADF
    with pytest.raises(FileExistsError):
        private_config.write_private_config(output, {"TLM_DEVICE_TOKEN": "replacement"})
