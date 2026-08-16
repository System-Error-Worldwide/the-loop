"""Approved public-release file inventory and digest verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .setup import (
    CANONICAL_DOCUMENTATION_ROOT,
    SetupError,
    _rewrite_documentation_links,
    _toolkit_files,
)


SCHEMA_VERSION = "1.0"
RELEASE_INTEGRITY_PATH = "docs/provenance/release-integrity.json"


def canonical_file_digest(path: Path, relative: str) -> str:
    content = path.read_bytes()
    if relative.startswith(".agents/skills/") and relative.endswith("/SKILL.md"):
        text = content.decode("utf-8")
        content = _rewrite_documentation_links(text, CANONICAL_DOCUMENTATION_ROOT).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def load_release_integrity(repository: Path) -> tuple[dict[str, str] | None, list[str]]:
    path = repository / RELEASE_INTEGRITY_PATH
    try:
        record: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"release integrity manifest is unreadable: {exc.__class__.__name__}"]
    if set(record) != {"schema_version", "files"} or record.get("schema_version") != SCHEMA_VERSION:
        return None, ["release integrity manifest shape or schema version is invalid"]
    files = record.get("files")
    if not isinstance(files, dict) or not files:
        return None, ["release integrity manifest has no file inventory"]
    if any(
        not isinstance(relative, str)
        or relative.startswith(("/", "../"))
        or "//" in relative
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        for relative, digest in files.items()
    ):
        return None, ["release integrity manifest contains an invalid path or digest"]
    return dict(files), []


def release_integrity_errors(repository: Path) -> list[str]:
    files, errors = load_release_integrity(repository)
    if files is None:
        return errors
    try:
        shipping = set(_toolkit_files(repository))
    except (OSError, SetupError) as exc:
        return [f"release toolkit inventory is invalid: {exc}"]
    expected = set(files) | {RELEASE_INTEGRITY_PATH}
    if shipping != expected:
        missing = sorted(expected - shipping)
        unexpected = sorted(shipping - expected)
        if missing:
            errors.append("release toolkit is missing manifest files: " + ", ".join(missing))
        if unexpected:
            errors.append("release integrity manifest omits toolkit files: " + ", ".join(unexpected))
    for relative, expected_digest in sorted(files.items()):
        candidate = repository / relative
        if not candidate.is_file() or candidate.is_symlink():
            errors.append(f"release file is missing or unsafe: {relative}")
            continue
        try:
            actual = canonical_file_digest(candidate, relative)
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"release file is unreadable: {relative}: {exc.__class__.__name__}")
            continue
        if actual != expected_digest:
            errors.append(f"release file digest does not match approved content: {relative}")
    return errors
