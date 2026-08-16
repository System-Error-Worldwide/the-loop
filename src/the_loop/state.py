"""Atomic projection and digest-chained append-only event utilities."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from .validation import (
    ContractError,
    LEASE_OPTIONAL_EVENT_TYPES,
    parse_timestamp,
    validate_configured_path,
    validate_record,
    validate_relative_path,
)

try:  # Linux and macOS are the required v0.1 hosts.
    import fcntl
except ImportError:  # pragma: no cover - Windows remains explicitly unverified.
    fcntl = None  # type: ignore[assignment]


_ROLLBACK_REPLACE = os.replace


class PathPresence(str, Enum):
    """Fail-closed result of probing a configured kill-switch path."""

    ABSENT = "absent"
    PRESENT = "present"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class PathProbe:
    configured_path: str
    presence: PathPresence
    detail: str | None = None


@dataclass(frozen=True)
class StateLockHandle:
    """Identity retained for a serialized runtime boundary."""

    path: Path
    root: Path
    relative_parent: Path
    root_identity: tuple[int, int]
    parent_identity: tuple[int, int]
    target_identity: tuple[int, int]
    descriptor: int

    def assert_current(self) -> None:
        info = os.fstat(self.descriptor)
        _check_projection_descriptor(info, self.path)
        if _identity(info) != self.target_identity:
            raise ContractError(str(self.path), "lock", "runtime lock descriptor identity changed")
        if not _target_namespace_matches(
            self.root,
            self.relative_parent,
            self.path.name,
            self.root_identity,
            self.parent_identity,
            self.target_identity,
        ):
            raise ContractError(str(self.path), "lock", "canonical runtime lock changed during the boundary")


def canonical_json(value: Mapping[str, Any]) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractError("$", "json", f"record is not canonical JSON: {exc}") from exc


@dataclass(frozen=True)
class _StatePathSnapshot:
    path: Path
    root: Path
    relative: Path
    root_info: os.stat_result
    components: tuple[os.stat_result | None, ...]

    @property
    def target_info(self) -> os.stat_result | None:
        return self.components[-1]


def _state_path(path_value: Path | str, project_root: Path | str) -> _StatePathSnapshot:
    path = Path(path_value)
    root = Path(project_root).resolve(strict=True)
    if path.is_absolute():
        if ".." in path.parts:
            raise ContractError(str(path), "unsafe_path", "parent traversal is not allowed")
        lexical_root = Path(os.path.abspath(project_root))
        lexical_candidate = Path(os.path.abspath(path))
        try:
            relative = lexical_candidate.relative_to(lexical_root)
        except ValueError as exc:
            raise ContractError(str(path), "unsafe_path", "state path escapes the project root") from exc
        candidate = root / relative
    else:
        relative = Path(validate_relative_path(path.as_posix(), path=str(path)))
        candidate = root / relative
    if not relative.parts or relative == Path("."):
        raise ContractError(str(path), "unsafe_path", "state path must name a file inside the project root")

    root_info = os.stat(root, follow_symlinks=False)
    components: list[os.stat_result | None] = []
    current = root
    for part in relative.parts:
        current = current / part
        try:
            info = os.stat(current, follow_symlinks=False)
        except FileNotFoundError:
            info = None
        if info is not None and stat.S_ISLNK(info.st_mode):
            raise ContractError(str(current), "unsafe_path", "state path cannot contain a symlink")
        components.append(info)
    return _StatePathSnapshot(candidate, root, relative, root_info, tuple(components))


def _directory_flags() -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise ContractError("$", "platform", "descriptor-relative state writes require O_DIRECTORY and O_NOFOLLOW")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _check_private_directory_info(info: os.stat_result, path: str) -> None:
    if not stat.S_ISDIR(info.st_mode):
        raise ContractError(path, "unsafe_path", "state parent must be a directory")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ContractError(path, "owner", "state directory must be owned by the current user")
    if info.st_mode & 0o077:
        raise ContractError(path, "permissions", "state directory must be owner-only")


def _check_private_directory_descriptor(descriptor: int, path: str) -> None:
    _check_private_directory_info(os.fstat(descriptor), path)


def _open_directory_child(
    parent_descriptor: int,
    name: str,
    path: str,
    expected: os.stat_result | None,
    *,
    create: bool,
) -> int:
    """Open one private child while preserving its observed namespace identity."""

    created = False
    if expected is None:
        if not create:
            try:
                child = os.open(name, _directory_flags(), dir_fd=parent_descriptor)
            except FileNotFoundError:
                raise
            else:
                os.close(child)
                raise ContractError(path, "unsafe_path", "state directory appeared during traversal")
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
        except FileExistsError as exc:
            raise ContractError(path, "unsafe_path", "state directory appeared before creation") from exc
        created = True
        try:
            expected = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise ContractError(path, "unsafe_path", "state directory disappeared after creation") from exc

    _check_private_directory_info(expected, path)
    try:
        child = os.open(name, _directory_flags(), dir_fd=parent_descriptor)
    except FileNotFoundError as exc:
        raise ContractError(path, "unsafe_path", "state directory disappeared before open") from exc
    try:
        if created:
            os.fchmod(child, 0o700)
        _check_private_directory_descriptor(child, path)
        if _identity(os.fstat(child)) != _identity(expected):
            raise ContractError(path, "unsafe_path", "state directory changed before open")
        return child
    except BaseException:
        os.close(child)
        raise


def _open_state_parent(
    snapshot: _StatePathSnapshot,
    *,
    create: bool = True,
) -> tuple[int, Path, Path, Path, tuple[int, int], tuple[int, int], os.stat_result | None]:
    """Open/create a private parent by walking from an anchored project root."""

    path = snapshot.path
    root = snapshot.root
    relative = snapshot.relative
    flags = _directory_flags()
    try:
        current = os.open(root, flags)
    except FileNotFoundError as exc:
        raise ContractError(str(root), "unsafe_path", "project root disappeared before open") from exc
    root_identity = _identity(os.fstat(current))
    if root_identity != _identity(snapshot.root_info):
        os.close(current)
        raise ContractError(str(root), "unsafe_path", "project root changed while opening state path")

    try:
        for index, part in enumerate(relative.parts[:-1]):
            child_path = str(root / Path(*relative.parts[: index + 1]))
            child = _open_directory_child(
                current,
                part,
                child_path,
                snapshot.components[index],
                create=create,
            )
            os.close(current)
            current = child
        parent_identity = _identity(os.fstat(current))
        return (
            current,
            path,
            root,
            relative.parent,
            root_identity,
            parent_identity,
            snapshot.target_info,
        )
    except BaseException:
        os.close(current)
        raise


def _namespace_matches(
    root: Path,
    relative_parent: Path,
    root_identity: tuple[int, int],
    parent_identity: tuple[int, int],
) -> bool:
    """Return whether the lexical state parent still maps to the retained inode."""

    try:
        current = os.open(root, _directory_flags())
    except OSError:
        return False
    try:
        if _identity(os.fstat(current)) != root_identity:
            return False
        for part in relative_parent.parts:
            child = os.open(part, _directory_flags(), dir_fd=current)
            os.close(current)
            current = child
        return _identity(os.fstat(current)) == parent_identity
    except OSError:
        return False
    finally:
        os.close(current)


def _target_namespace_matches(
    root: Path,
    relative_parent: Path,
    name: str,
    root_identity: tuple[int, int],
    parent_identity: tuple[int, int],
    target_identity: tuple[int, int],
) -> bool:
    """Return whether the canonical path still names the retained target inode."""

    try:
        current = os.open(root, _directory_flags())
    except OSError:
        return False
    target: int | None = None
    try:
        if _identity(os.fstat(current)) != root_identity:
            return False
        for part in relative_parent.parts:
            child = os.open(part, _directory_flags(), dir_fd=current)
            os.close(current)
            current = child
        if _identity(os.fstat(current)) != parent_identity:
            return False
        target = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
        return _identity(os.fstat(target)) == target_identity
    except OSError:
        return False
    finally:
        if target is not None:
            os.close(target)
        os.close(current)


def _validate_target_snapshot(
    parent_descriptor: int,
    name: str,
    path: Path,
    expected: os.stat_result | None,
    *,
    event_log: bool,
) -> os.stat_result | None:
    if expected is not None:
        if event_log:
            _check_event_descriptor(expected, path)
        else:
            _check_projection_descriptor(expected, path)
    try:
        info = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError as exc:
        if expected is not None:
            raise ContractError(str(path), "unsafe_path", "state target disappeared after path preparation") from exc
        return None
    if expected is None:
        raise ContractError(str(path), "unsafe_path", "state target appeared after path preparation")
    if _identity(info) != _identity(expected):
        raise ContractError(str(path), "unsafe_path", "state target changed after path preparation")
    if stat.S_ISLNK(info.st_mode):
        kind = "event log" if event_log else "projection target"
        raise ContractError(str(path), "unsafe_path", f"{kind} cannot be a symlink")
    if not stat.S_ISREG(info.st_mode):
        kind = "event log" if event_log else "projection target"
        raise ContractError(str(path), "unsafe_path", f"{kind} must be a regular file")
    if event_log:
        _check_event_descriptor(info, path)
    else:
        _check_projection_descriptor(info, path)
    return info


def _check_event_descriptor(info: os.stat_result, path: Path) -> None:
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(str(path), "unsafe_path", "event log must be a regular file")
    if info.st_nlink != 1:
        raise ContractError(str(path), "unsafe_path", "event log cannot be a hard-linked file")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ContractError(str(path), "owner", "event log must be owned by the current user")
    if info.st_mode & 0o077:
        raise ContractError(str(path), "permissions", "event log must be owner-only")


def _check_projection_descriptor(info: os.stat_result, path: Path) -> None:
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(str(path), "unsafe_path", "projection must be a regular file")
    if info.st_nlink != 1:
        raise ContractError(str(path), "unsafe_path", "projection cannot be a hard-linked file")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ContractError(str(path), "owner", "projection must be owned by the current user")
    if info.st_mode & 0o077:
        raise ContractError(str(path), "permissions", "projection must be owner-only")


def _read_all(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _write_all(descriptor: int, payload: bytes, *, operation: str) -> None:
    written = 0
    while written < len(payload):
        count = os.write(descriptor, payload[written:])
        if count <= 0:
            raise OSError(f"{operation} made no progress")
        written += count


def _read_projection_bytes(
    parent_descriptor: int,
    name: str,
    path: Path,
    expected: os.stat_result | None,
) -> bytes | None:
    if expected is None:
        return None
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_descriptor,
    )
    try:
        info = os.fstat(descriptor)
        _check_projection_descriptor(info, path)
        if _identity(info) != _identity(expected):
            raise ContractError(str(path), "unsafe_path", "projection changed before rollback snapshot")
        return _read_all(descriptor)
    finally:
        os.close(descriptor)


def _restore_projection(
    parent_descriptor: int,
    name: str,
    path: Path,
    prior_bytes: bytes | None,
    replaced_identity: tuple[int, int],
) -> None:
    try:
        current = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise ContractError(str(path), "rollback", "replaced projection disappeared before rollback") from exc
    if _identity(current) != replaced_identity:
        raise ContractError(str(path), "rollback", "replaced projection changed before rollback")

    if prior_bytes is None:
        os.unlink(name, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
        return

    rollback_name = f".{name}.{secrets.token_hex(8)}.rollback"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            rollback_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_descriptor,
        )
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, prior_bytes, operation="projection rollback write")
        os.fsync(descriptor)
        _ROLLBACK_REPLACE(
            rollback_name,
            name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        rollback_name = ""
        os.fsync(parent_descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if rollback_name:
            try:
                os.unlink(rollback_name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass


def atomic_write_json(
    path_value: Path | str,
    record: Mapping[str, Any],
    *,
    record_type: str | None = None,
    previous: Mapping[str, Any] | None = None,
    expected_owner: Mapping[str, Any] | None = None,
    expected_authority_grant: Mapping[str, Any] | None = None,
    project_root: Path | str,
    _before_replace: Callable[[], None] | None = None,
) -> Path:
    """Validate and atomically replace a JSON projection.

    The temporary file is a private sibling created relative to a retained parent
    descriptor. Any failure before replacement removes only that temporary file
    and leaves the prior projection untouched. The private callback exists solely
    for deterministic fault tests at the final replacement boundary.
    """

    if record_type is not None:
        validate_record(
            record_type,
            record,
            previous=previous,
            expected_owner=expected_owner,
            expected_authority_grant=expected_authority_grant,
        )
    serialized = canonical_json(record) + "\n"
    snapshot = _state_path(path_value, project_root)
    (
        parent_descriptor,
        path,
        root,
        relative_parent,
        root_identity,
        parent_identity,
        expected_target,
    ) = _open_state_parent(snapshot)
    temporary_name: str | None = None
    descriptor: int | None = None
    prior_bytes: bytes | None = None
    replaced_identity: tuple[int, int] | None = None
    try:
        _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=False,
        )
        prior_bytes = _read_projection_bytes(
            parent_descriptor,
            path.name,
            path,
            expected_target,
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        for _ in range(128):
            temporary_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
            try:
                descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent_descriptor)
                break
            except FileExistsError:
                continue
        if descriptor is None:
            raise ContractError(str(path), "atomic_write", "could not allocate a unique sibling temporary file")
        os.fchmod(descriptor, 0o600)
        encoded = serialized.encode("utf-8")
        _write_all(descriptor, encoded, operation="projection write")
        os.fsync(descriptor)
        if _before_replace is not None:
            _before_replace()
        _check_projection_descriptor(os.fstat(descriptor), path)
        if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
            raise ContractError(str(path.parent), "unsafe_path", "state parent changed before atomic replacement")
        _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=False,
        )
        try:
            os.replace(
                temporary_name,
                path.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
        except TypeError as exc:  # pragma: no cover - required hosts support dir_fd.
            raise ContractError(str(path), "platform", "descriptor-relative atomic replacement is unavailable") from exc
        temporary_name = None
        target_info = os.fstat(descriptor)
        replaced_identity = _identity(target_info)
        _check_projection_descriptor(target_info, path)
        os.fsync(parent_descriptor)
        if not _target_namespace_matches(
            root,
            relative_parent,
            path.name,
            root_identity,
            parent_identity,
            replaced_identity,
        ):
            raise ContractError(str(path), "unsafe_path", "canonical projection changed during atomic replacement")
        _check_projection_descriptor(os.fstat(descriptor), path)
    except BaseException as write_error:
        if replaced_identity is not None:
            try:
                _restore_projection(
                    parent_descriptor,
                    path.name,
                    path,
                    prior_bytes,
                    replaced_identity,
                )
            except BaseException as rollback_error:
                raise ContractError(
                    str(path),
                    "rollback",
                    f"projection replacement failed and rollback could not restore prior state: {rollback_error}",
                ) from write_error
        elif temporary_name is not None:
            try:
                os.unlink(temporary_name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)
    return path


def read_json(
    path_value: Path | str,
    *,
    project_root: Path | str,
    record_type: str | None = None,
    expected_owner: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Read one private JSON projection through an anchored descriptor.

    A missing target returns ``None``. Every other inability to establish the
    target's identity, ownership, permissions or JSON shape fails closed.
    """

    snapshot = _state_path(path_value, project_root)
    try:
        (
            parent_descriptor,
            path,
            root,
            relative_parent,
            root_identity,
            parent_identity,
            expected_target,
        ) = _open_state_parent(snapshot, create=False)
    except FileNotFoundError:
        return None
    descriptor: int | None = None
    try:
        if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
            raise ContractError(str(path.parent), "unsafe_path", "state parent changed before projection read")
        expected_target = _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=False,
        )
        if expected_target is None:
            return None
        descriptor = os.open(
            path.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_descriptor,
        )
        descriptor_info = os.fstat(descriptor)
        _check_projection_descriptor(descriptor_info, path)
        if _identity(descriptor_info) != _identity(expected_target):
            raise ContractError(str(path), "unsafe_path", "canonical projection changed before read")
        payload = _read_all(descriptor)
        descriptor_info = os.fstat(descriptor)
        _check_projection_descriptor(descriptor_info, path)
        if not _target_namespace_matches(
            root,
            relative_parent,
            path.name,
            root_identity,
            parent_identity,
            _identity(descriptor_info),
        ):
            raise ContractError(str(path), "unsafe_path", "canonical projection changed during read")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError(str(path), "json", f"invalid projection JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ContractError(str(path), "type", "projection must be a JSON object")
        if record_type is not None:
            validate_record(record_type, value, expected_owner=expected_owner)
        return value
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def create_json_exclusive(
    path_value: Path | str,
    record: Mapping[str, Any],
    *,
    project_root: Path | str,
    record_type: str | None = None,
    expected_owner: Mapping[str, Any] | None = None,
) -> Path:
    """Create one private projection without ever replacing an existing name."""

    if record_type is not None:
        validate_record(record_type, record, expected_owner=expected_owner)
    encoded = (canonical_json(record) + "\n").encode("utf-8")
    snapshot = _state_path(path_value, project_root)
    (
        parent_descriptor,
        path,
        root,
        relative_parent,
        root_identity,
        parent_identity,
        expected_target,
    ) = _open_state_parent(snapshot)
    descriptor: int | None = None
    created_identity: tuple[int, int] | None = None
    try:
        _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=False,
        )
        if expected_target is not None:
            raise ContractError(str(path), "exists", "projection already exists")
        if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
            raise ContractError(str(path.parent), "unsafe_path", "state parent changed before exclusive creation")
        try:
            descriptor = os.open(
                path.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_descriptor,
            )
        except FileExistsError as exc:
            raise ContractError(str(path), "exists", "projection appeared before exclusive creation") from exc
        os.fchmod(descriptor, 0o600)
        created_identity = _identity(os.fstat(descriptor))
        _write_all(descriptor, encoded, operation="exclusive projection write")
        os.fsync(descriptor)
        os.fsync(parent_descriptor)
        info = os.fstat(descriptor)
        _check_projection_descriptor(info, path)
        if not _target_namespace_matches(
            root,
            relative_parent,
            path.name,
            root_identity,
            parent_identity,
            created_identity,
        ):
            raise ContractError(str(path), "unsafe_path", "canonical projection changed during exclusive creation")
        created_identity = None
        return path
    except BaseException:
        if created_identity is not None:
            try:
                current = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
                if _identity(current) == created_identity:
                    os.unlink(path.name, dir_fd=parent_descriptor)
                    os.fsync(parent_descriptor)
            except FileNotFoundError:
                pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


@contextmanager
def state_lock(
    path_value: Path | str,
    *,
    project_root: Path | str,
    exclusive: bool = True,
    _root_already_locked: bool = False,
) -> Iterator[StateLockHandle]:
    """Hold a stable private lock file for one serialized runtime boundary.

    ``_root_already_locked`` is an internal nesting escape hatch for a second
    cooperative lock acquired while the caller already holds a state lock for
    the same project. It deliberately skips only the non-reentrant root flock;
    all descriptor and namespace identity checks remain active.
    """

    if fcntl is None:
        raise ContractError(str(path_value), "platform", "OS-level state locking is unavailable")
    for _ in range(16):
        snapshot = _state_path(path_value, project_root)
        (
            parent_descriptor,
            path,
            root,
            relative_parent,
            root_identity,
            parent_identity,
            expected_target,
        ) = _open_state_parent(snapshot)
        descriptor: int | None = None
        root_lock_descriptor: int | None = None
        retry = False
        try:
            if not _root_already_locked:
                root_lock_descriptor = os.open(root, _directory_flags())
                if _identity(os.fstat(root_lock_descriptor)) != root_identity:
                    raise ContractError(str(root), "lock", "project root changed before runtime lock acquisition")
                fcntl.flock(root_lock_descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
                raise ContractError(str(path.parent), "lock", "runtime lock parent changed during acquisition")
            if expected_target is None:
                try:
                    descriptor = os.open(
                        path.name,
                        os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                        dir_fd=parent_descriptor,
                    )
                    os.fchmod(descriptor, 0o600)
                    os.fsync(parent_descriptor)
                except FileExistsError:
                    retry = True
                    continue
            else:
                _validate_target_snapshot(
                    parent_descriptor,
                    path.name,
                    path,
                    expected_target,
                    event_log=False,
                )
                descriptor = os.open(
                    path.name,
                    os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent_descriptor,
                )
            descriptor_info = os.fstat(descriptor)
            _check_projection_descriptor(descriptor_info, path)
            fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            descriptor_info = os.fstat(descriptor)
            _check_projection_descriptor(descriptor_info, path)
            if not _target_namespace_matches(
                root,
                relative_parent,
                path.name,
                root_identity,
                parent_identity,
                _identity(descriptor_info),
            ):
                raise ContractError(str(path), "unsafe_path", "canonical lock changed during acquisition")
            handle = StateLockHandle(
                path=path,
                root=root,
                relative_parent=relative_parent,
                root_identity=root_identity,
                parent_identity=parent_identity,
                target_identity=_identity(descriptor_info),
                descriptor=descriptor,
            )
            handle.assert_current()
            yield handle
            handle.assert_current()
            return
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if root_lock_descriptor is not None:
                os.close(root_lock_descriptor)
            os.close(parent_descriptor)
        if retry:  # pragma: no cover - loop continuation occurs in the try block.
            continue
    raise ContractError(str(path_value), "lock", "could not acquire a stable runtime lock")


def remove_state_file(path_value: Path | str, *, project_root: Path | str) -> bool:
    """Remove exactly the observed private file, using an identity-checked quarantine."""

    snapshot = _state_path(path_value, project_root)
    try:
        (
            parent_descriptor,
            path,
            root,
            relative_parent,
            root_identity,
            parent_identity,
            expected_target,
        ) = _open_state_parent(snapshot, create=False)
    except FileNotFoundError:
        return False
    descriptor: int | None = None
    quarantine_name: str | None = None
    prior_bytes: bytes | None = None
    removed = False
    try:
        expected_target = _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=False,
        )
        if expected_target is None:
            return False
        descriptor = os.open(
            path.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_descriptor,
        )
        descriptor_info = os.fstat(descriptor)
        _check_projection_descriptor(descriptor_info, path)
        expected_identity = _identity(descriptor_info)
        if expected_identity != _identity(expected_target):
            raise ContractError(str(path), "unsafe_path", "canonical projection changed before removal")
        prior_bytes = _read_all(descriptor)
        if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
            raise ContractError(str(path.parent), "unsafe_path", "state parent changed before removal")
        quarantine_name = f".{path.name}.{secrets.token_hex(8)}.remove"
        os.replace(
            path.name,
            quarantine_name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        quarantined = os.stat(quarantine_name, dir_fd=parent_descriptor, follow_symlinks=False)
        if _identity(quarantined) != expected_identity:
            try:
                os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                os.replace(
                    quarantine_name,
                    path.name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                quarantine_name = None
            raise ContractError(str(path), "unsafe_path", "projection changed during identity-safe removal")
        _check_projection_descriptor(quarantined, path)
        os.fsync(parent_descriptor)
        os.unlink(quarantine_name, dir_fd=parent_descriptor)
        quarantine_name = None
        removed = True
        os.fsync(parent_descriptor)
        return True
    except BaseException as remove_error:
        try:
            if quarantine_name is not None:
                try:
                    os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    os.replace(
                        quarantine_name,
                        path.name,
                        src_dir_fd=parent_descriptor,
                        dst_dir_fd=parent_descriptor,
                    )
                    quarantine_name = None
                    os.fsync(parent_descriptor)
                else:
                    raise ContractError(
                        str(path),
                        "rollback",
                        "removal failed after quarantine and the canonical name is now occupied",
                    )
            elif removed and prior_bytes is not None:
                try:
                    os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    restored = os.open(
                        path.name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                        dir_fd=parent_descriptor,
                    )
                    try:
                        os.fchmod(restored, 0o600)
                        _write_all(restored, prior_bytes, operation="projection removal rollback")
                        os.fsync(restored)
                    finally:
                        os.close(restored)
                    os.fsync(parent_descriptor)
        except BaseException as rollback_error:
            raise ContractError(
                str(path),
                "rollback",
                f"state removal failed and rollback could not restore the prior projection: {rollback_error}",
            ) from remove_error
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def probe_kill_switch(
    configured_path: str,
    *,
    project_root: Path | str,
) -> PathProbe:
    """Probe one configured stop path without following its final component."""

    try:
        validate_configured_path(configured_path, path="$.kill_switch")
        candidate = Path(configured_path)
        if candidate.is_absolute():
            try:
                os.stat(candidate, follow_symlinks=False)
            except FileNotFoundError:
                return PathProbe(configured_path, PathPresence.ABSENT)
            except OSError as exc:
                return PathProbe(configured_path, PathPresence.INDETERMINATE, exc.__class__.__name__)
            return PathProbe(configured_path, PathPresence.PRESENT)

        relative = Path(validate_relative_path(configured_path, path="$.kill_switch"))
        root = Path(project_root).resolve(strict=True)
        root_info = os.stat(root, follow_symlinks=False)
        current = os.open(root, _directory_flags())
        try:
            if _identity(os.fstat(current)) != _identity(root_info):
                return PathProbe(configured_path, PathPresence.INDETERMINATE, "project root changed")
            for index, part in enumerate(relative.parts[:-1]):
                try:
                    info = os.stat(part, dir_fd=current, follow_symlinks=False)
                except FileNotFoundError:
                    return PathProbe(configured_path, PathPresence.ABSENT)
                except OSError as exc:
                    return PathProbe(configured_path, PathPresence.INDETERMINATE, exc.__class__.__name__)
                if stat.S_ISLNK(info.st_mode):
                    return PathProbe(configured_path, PathPresence.INDETERMINATE, "intermediate symlink")
                if not stat.S_ISDIR(info.st_mode):
                    return PathProbe(configured_path, PathPresence.ABSENT)
                try:
                    child = os.open(part, _directory_flags(), dir_fd=current)
                except OSError as exc:
                    return PathProbe(configured_path, PathPresence.INDETERMINATE, exc.__class__.__name__)
                if _identity(os.fstat(child)) != _identity(info):
                    os.close(child)
                    return PathProbe(configured_path, PathPresence.INDETERMINATE, "intermediate changed")
                os.close(current)
                current = child
                del index
            try:
                os.stat(relative.name, dir_fd=current, follow_symlinks=False)
            except FileNotFoundError:
                return PathProbe(configured_path, PathPresence.ABSENT)
            except OSError as exc:
                return PathProbe(configured_path, PathPresence.INDETERMINATE, exc.__class__.__name__)
            return PathProbe(configured_path, PathPresence.PRESENT)
        finally:
            os.close(current)
    except (ContractError, OSError) as exc:
        return PathProbe(configured_path, PathPresence.INDETERMINATE, str(exc))


def compute_event_digest(event: Mapping[str, Any]) -> str:
    payload = dict(event)
    payload.pop("event_digest", None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _parse_event_bytes(data: bytes, source: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(data.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError(f"{source}:{line_number}", "event_log", f"invalid event JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ContractError(f"{source}:{line_number}", "event_log", "event line must be a JSON object")
        events.append(value)
    return events


def _complete_event(
    event: Mapping[str, Any],
    existing: Sequence[Mapping[str, Any]],
    *,
    expected_owner: Mapping[str, Any] | None,
    expected_lease_id: str | None,
    expected_generation: int | None,
) -> dict[str, Any]:
    previous = existing[-1] if existing else None
    completed = dict(event)
    event_type = completed.get("type")
    if event_type not in LEASE_OPTIONAL_EVENT_TYPES:
        missing_expectations = [
            name
            for name, value in (
                ("expected_owner", expected_owner),
                ("expected_lease_id", expected_lease_id),
                ("expected_generation", expected_generation),
            )
            if value is None
        ]
        if missing_expectations:
            raise ContractError(
                "$",
                "lease_context",
                "lease-required event is missing caller expectations: " + ", ".join(missing_expectations),
            )

    expected_sequence = 1 if previous is None else int(previous["sequence"]) + 1
    supplied_sequence = completed.get("sequence")
    if supplied_sequence is not None and supplied_sequence != expected_sequence:
        message = (
            "the first audit event sequence must be one"
            if previous is None
            else "must increment the current event-log sequence by one"
        )
        raise ContractError("$.sequence", "event_chain", message)

    expected_previous = None if previous is None else previous["event_digest"]
    supplied_previous = completed.get("previous_event_digest")
    if supplied_previous is not None and supplied_previous != expected_previous:
        raise ContractError("$.previous_event_digest", "digest_chain", "does not match current event-log head")
    completed["previous_event_digest"] = expected_previous
    completed["sequence"] = expected_sequence
    completed["event_digest"] = compute_event_digest(completed)

    verify_event_chain([*existing, completed])
    validate_record("audit_event", completed, previous=previous, expected_owner=expected_owner)
    if expected_lease_id is not None and completed["lease_id"] != expected_lease_id:
        raise ContractError("$.lease_id", "owner", "event lease_id does not match the active lease")
    if expected_generation is not None and completed["lease_generation"] != expected_generation:
        raise ContractError("$.lease_generation", "owner", "event lease generation does not match the active lease")
    return completed


def _is_prelease_recovery(
    event: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> bool:
    """Recognize the sole recovery event allowed to establish generation zero."""

    if previous is None or event.get("type") != "recovery_started":
        return False
    data = event.get("data")
    prior_projection = previous.get("projection")
    if not isinstance(data, Mapping) or not isinstance(prior_projection, Mapping):
        return False
    prior_run = prior_projection.get("run")
    return (
        event.get("lease_generation") == 0
        and data.get("previous_generation") is None
        and data.get("new_generation") == 0
        and isinstance(prior_run, Mapping)
        and prior_run.get("status") == "halted_kill_switch"
        and prior_projection.get("lease") is None
    )


def _preflight_event_chain(events: Sequence[Mapping[str, Any]]) -> None:
    """Reject lifecycle corruption before projection semantics obscure its cause."""

    required = {
        "event_id",
        "sequence",
        "run_id",
        "lease_id",
        "lease_generation",
        "type",
        "previous_event_digest",
        "event_digest",
    }
    previous: Mapping[str, Any] | None = None
    event_ids: set[str] = set()
    lease_contexts: dict[int, tuple[str, int]] = {}
    highest_generation = -1
    recovery_required = False
    for index, event in enumerate(events):
        if not required.issubset(event):
            return
        event_path = f"$[{index}]"
        if index == 0 and event["type"] != "run_created":
            raise ContractError(f"{event_path}.type", "event_chain", "the first audit event must be run_created")
        if index > 0 and event["type"] == "run_created":
            raise ContractError(f"{event_path}.type", "event_chain", "run_created may appear only as the first event")
        if index == 0 and event["sequence"] != 1:
            raise ContractError(f"{event_path}.sequence", "event_chain", "the first audit event sequence must be one")
        if event["event_id"] in event_ids:
            raise ContractError(f"{event_path}.event_id", "event_chain", "event_id must be unique within a log")
        event_ids.add(str(event["event_id"]))
        if event["event_digest"] != compute_event_digest(event):
            raise ContractError(f"{event_path}.event_digest", "digest", "event digest does not match content")
        expected_previous = None if previous is None else previous["event_digest"]
        if event["previous_event_digest"] != expected_previous:
            raise ContractError(
                f"{event_path}.previous_event_digest",
                "digest_chain",
                "does not match the previous event digest",
            )
        if previous is not None:
            if event["run_id"] != previous["run_id"]:
                raise ContractError(f"{event_path}.run_id", "event_chain", "run_id changed inside one event log")
            if event["sequence"] != previous["sequence"] + 1:
                raise ContractError(
                    f"{event_path}.sequence",
                    "event_chain",
                    "must increment the previous event sequence by one",
                )
            if previous["type"] in {"run_completed", "run_cancelled"}:
                raise ContractError(f"{event_path}.type", "event_chain", "events cannot follow a terminal run event")

        current_generation = event["lease_generation"]
        if recovery_required and current_generation is not None and event["type"] not in {
            "recovery_started",
            "run_cancelled",
            "budget_reached",
        }:
            raise ContractError(
                f"{event_path}.type",
                "event_chain",
                "failed or kill-switched work requires recovery_started on a fresh generation",
            )
        if current_generation is not None:
            if event["type"] == "recovery_started" and current_generation in lease_contexts:
                raise ContractError(f"{event_path}.type", "event_chain", "recovery_started cannot repeat a lease generation")
            if event["type"] == "lease_acquired" and current_generation in lease_contexts:
                raise ContractError(
                    f"{event_path}.type",
                    "event_chain",
                    "lease_acquired cannot repeat an established lease generation; use lease_renewed",
                )
            if current_generation < highest_generation:
                raise ContractError(f"{event_path}.lease_generation", "event_chain", "lease generation cannot decrease")
            if highest_generation == -1 and current_generation != 0:
                raise ContractError(f"{event_path}.lease_generation", "event_chain", "initial lease generation must be zero")
            if (
                highest_generation == -1
                and event["type"] != "lease_acquired"
                and not _is_prelease_recovery(event, previous)
            ):
                raise ContractError(f"{event_path}.type", "event_chain", "the first lease event must be lease_acquired")
            if current_generation > highest_generation:
                if highest_generation >= 0 and current_generation != highest_generation + 1:
                    raise ContractError(f"{event_path}.lease_generation", "event_chain", "lease generation must increment by one")
                if highest_generation >= 0 and event["type"] != "recovery_started":
                    raise ContractError(f"{event_path}.type", "event_chain", "new lease generation requires recovery_started")
            prior_context = lease_contexts.get(current_generation)
            if prior_context is not None:
                prior_lease_id, prior_sequence = prior_context
                if event["lease_id"] != prior_lease_id:
                    raise ContractError(f"{event_path}.lease_id", "event_chain", "lease_id changed within one generation")
                if event["sequence"] <= prior_sequence:
                    raise ContractError(
                        f"{event_path}.sequence",
                        "event_chain",
                        "sequence must strictly increase within a lease generation",
                    )
            lease_contexts[int(current_generation)] = (str(event["lease_id"]), int(event["sequence"]))
            highest_generation = max(highest_generation, int(current_generation))
        if event["type"] in {"run_failed", "kill_switch_detected", "budget_reached"} or (
            event["type"] == "operation_reconciled" and event.get("data", {}).get("outcome") == "unknown"
        ):
            recovery_required = True
        elif event["type"] == "recovery_started":
            recovery_required = False
        previous = event


def verify_event_chain(events: Sequence[Mapping[str, Any]]) -> None:
    _preflight_event_chain(events)
    previous: Mapping[str, Any] | None = None
    event_ids: set[str] = set()
    lease_contexts: dict[int, tuple[str, int]] = {}
    highest_generation = -1
    recovery_required = False
    previous_at = None
    for index, event in enumerate(events):
        event_path = f"$[{index}]"
        validate_record("audit_event", event, previous=previous)
        event_at = parse_timestamp(event["at"], f"{event_path}.at")
        if previous_at is not None and event_at < previous_at:
            raise ContractError(f"{event_path}.at", "event_chain", "event time cannot move backwards")
        if event["type"] in {"lease_acquired", "lease_renewed"}:
            expires_at = parse_timestamp(event["data"]["expires_at"], f"{event_path}.data.expires_at")
            if expires_at <= event_at:
                raise ContractError(
                    f"{event_path}.data.expires_at",
                    "event_chain",
                    "lease expiry must be later than the event time",
                )
        if index == 0 and event["type"] != "run_created":
            raise ContractError(f"{event_path}.type", "event_chain", "the first audit event must be run_created")
        if index > 0 and event["type"] == "run_created":
            raise ContractError(f"{event_path}.type", "event_chain", "run_created may appear only as the first event")
        if index == 0 and event["sequence"] != 1:
            raise ContractError(f"{event_path}.sequence", "event_chain", "the first audit event sequence must be one")
        if event["event_id"] in event_ids:
            raise ContractError(f"{event_path}.event_id", "event_chain", "event_id must be unique within a log")
        event_ids.add(event["event_id"])
        computed = compute_event_digest(event)
        if event["event_digest"] != computed:
            raise ContractError(f"{event_path}.event_digest", "digest", "event digest does not match content")
        expected_previous = None if previous is None else previous["event_digest"]
        if event["previous_event_digest"] != expected_previous:
            raise ContractError(
                f"{event_path}.previous_event_digest",
                "digest_chain",
                "does not match the previous event digest",
            )
        if previous is not None:
            if event["run_id"] != previous["run_id"]:
                raise ContractError(f"{event_path}.run_id", "event_chain", "run_id changed inside one event log")
            if event["sequence"] != previous["sequence"] + 1:
                raise ContractError(
                    f"{event_path}.sequence",
                    "event_chain",
                    "must increment the previous event sequence by one",
                )
            if previous["type"] in {"run_completed", "run_cancelled"}:
                raise ContractError(f"{event_path}.type", "event_chain", "events cannot follow a terminal run event")
        current_generation = event["lease_generation"]
        if recovery_required and current_generation is not None and event["type"] not in {
            "recovery_started",
            "run_cancelled",
            "budget_reached",
        }:
            raise ContractError(
                f"{event_path}.type",
                "event_chain",
                "failed or kill-switched work requires recovery_started on a fresh generation",
            )
        if current_generation is not None:
            if event["type"] == "recovery_started" and current_generation in lease_contexts:
                raise ContractError(f"{event_path}.type", "event_chain", "recovery_started cannot repeat a lease generation")
            if event["type"] == "lease_acquired" and current_generation in lease_contexts:
                raise ContractError(
                    f"{event_path}.type",
                    "event_chain",
                    "lease_acquired cannot repeat an established lease generation; use lease_renewed",
                )
            if current_generation < highest_generation:
                raise ContractError(f"{event_path}.lease_generation", "event_chain", "lease generation cannot decrease")
            if highest_generation == -1 and current_generation != 0:
                raise ContractError(f"{event_path}.lease_generation", "event_chain", "initial lease generation must be zero")
            if (
                highest_generation == -1
                and event["type"] != "lease_acquired"
                and not _is_prelease_recovery(event, previous)
            ):
                raise ContractError(f"{event_path}.type", "event_chain", "the first lease event must be lease_acquired")
            if current_generation > highest_generation:
                if highest_generation >= 0 and current_generation != highest_generation + 1:
                    raise ContractError(f"{event_path}.lease_generation", "event_chain", "lease generation must increment by one")
                if highest_generation >= 0 and event["type"] != "recovery_started":
                    raise ContractError(f"{event_path}.type", "event_chain", "new lease generation requires recovery_started")
            prior_context = lease_contexts.get(current_generation)
            if prior_context is not None:
                prior_lease_id, prior_sequence = prior_context
                if event["lease_id"] != prior_lease_id:
                    raise ContractError(f"{event_path}.lease_id", "event_chain", "lease_id changed within one generation")
                if event["sequence"] <= prior_sequence:
                    raise ContractError(f"{event_path}.sequence", "event_chain", "sequence must strictly increase within a lease generation")
            lease_contexts[current_generation] = (event["lease_id"], event["sequence"])
            highest_generation = max(highest_generation, current_generation)
        if event["type"] in {"run_failed", "kill_switch_detected", "budget_reached"} or (
            event["type"] == "operation_reconciled" and event.get("data", {}).get("outcome") == "unknown"
        ):
            recovery_required = True
        elif event["type"] == "recovery_started":
            recovery_required = False
        previous = event
        previous_at = event_at


def read_events(
    path_value: Path | str,
    *,
    project_root: Path | str,
    verify: bool = True,
) -> list[dict[str, Any]]:
    """Read one event log through a descriptor-anchored shared lock."""

    snapshot = _state_path(path_value, project_root)
    try:
        (
            parent_descriptor,
            path,
            root,
            relative_parent,
            root_identity,
            parent_identity,
            expected_target,
        ) = _open_state_parent(
            snapshot,
            create=False,
        )
    except FileNotFoundError:
        return []
    descriptor: int | None = None
    try:
        if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
            raise ContractError(str(path.parent), "unsafe_path", "state parent changed before event-log read")
        expected_target = _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=True,
        )
        try:
            descriptor = os.open(
                path.name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_descriptor,
            )
        except FileNotFoundError as exc:
            if expected_target is not None:
                raise ContractError(str(path), "unsafe_path", "canonical event log disappeared before read") from exc
            return []
        descriptor_info = os.fstat(descriptor)
        _check_event_descriptor(descriptor_info, path)
        if expected_target is None or _identity(descriptor_info) != _identity(expected_target):
            raise ContractError(str(path), "unsafe_path", "canonical event log changed before read")
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
        descriptor_info = os.fstat(descriptor)
        _check_event_descriptor(descriptor_info, path)
        data = _read_all(descriptor)
        descriptor_info = os.fstat(descriptor)
        _check_event_descriptor(descriptor_info, path)
        if not _target_namespace_matches(
            root,
            relative_parent,
            path.name,
            root_identity,
            parent_identity,
            _identity(descriptor_info),
        ):
            raise ContractError(str(path), "unsafe_path", "canonical event log changed during read")
        events = _parse_event_bytes(data, str(path))
        if verify:
            verify_event_chain(events)
        return events
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
        finally:
            os.close(parent_descriptor)


def append_event(
    path_value: Path | str,
    event: Mapping[str, Any],
    *,
    project_root: Path | str,
    expected_owner: Mapping[str, Any] | None = None,
    expected_lease_id: str | None = None,
    expected_generation: int | None = None,
    _before_open: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Append one validated event while holding an OS-level append lock."""

    snapshot = _state_path(path_value, project_root)
    (
        parent_descriptor,
        path,
        root,
        relative_parent,
        root_identity,
        parent_identity,
        expected_target,
    ) = _open_state_parent(snapshot)
    descriptor: int | None = None
    try:
        if _before_open is not None:
            _before_open()
        if not _namespace_matches(root, relative_parent, root_identity, parent_identity):
            raise ContractError(str(path.parent), "unsafe_path", "state parent changed before event-log open")
        expected_target = _validate_target_snapshot(
            parent_descriptor,
            path.name,
            path,
            expected_target,
            event_log=True,
        )
        flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        if expected_target is None:
            try:
                descriptor = os.open(
                    path.name,
                    flags | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=parent_descriptor,
                )
            except FileExistsError as exc:
                raise ContractError(str(path), "unsafe_path", "canonical event log appeared before creation") from exc
        else:
            try:
                descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
            except FileNotFoundError as exc:
                raise ContractError(str(path), "unsafe_path", "canonical event log disappeared before append") from exc
        descriptor_info = os.fstat(descriptor)
        _check_event_descriptor(descriptor_info, path)
        if expected_target is not None and _identity(descriptor_info) != _identity(expected_target):
            raise ContractError(str(path), "unsafe_path", "canonical event log changed before append")
        os.fchmod(descriptor, 0o600)
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        _check_event_descriptor(os.fstat(descriptor), path)
        os.lseek(descriptor, 0, os.SEEK_SET)
        existing_bytes = _read_all(descriptor)
        existing = _parse_event_bytes(existing_bytes, str(path))
        verify_event_chain(existing)
        completed = _complete_event(
            event,
            existing,
            expected_owner=expected_owner,
            expected_lease_id=expected_lease_id,
            expected_generation=expected_generation,
        )

        separator = b"" if not existing_bytes or existing_bytes.endswith((b"\n", b"\r")) else b"\n"
        encoded = separator + (canonical_json(completed) + "\n").encode("utf-8")
        pre_append_size = len(existing_bytes)
        os.lseek(descriptor, 0, os.SEEK_END)
        try:
            _write_all(descriptor, encoded, operation="event append")
            os.fsync(descriptor)
            post_write_info = os.fstat(descriptor)
            _check_event_descriptor(post_write_info, path)
            if not _target_namespace_matches(
                root,
                relative_parent,
                path.name,
                root_identity,
                parent_identity,
                _identity(post_write_info),
            ):
                raise ContractError(str(path), "unsafe_path", "canonical event log changed during append")
            _check_event_descriptor(os.fstat(descriptor), path)
        except BaseException as append_error:
            try:
                os.ftruncate(descriptor, pre_append_size)
                os.fsync(descriptor)
            except BaseException as rollback_error:
                raise ContractError(
                    str(path),
                    "event_log",
                    f"append failed and rollback could not restore the prior log: {rollback_error}",
                ) from append_error
            raise
        return completed
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
        finally:
            os.close(parent_descriptor)
