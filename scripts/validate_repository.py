#!/usr/bin/env python3
"""Read-only repository policy checks for SYSTEM ERROR'S THE LOOP."""

from __future__ import annotations

import hashlib
import html
import os
import re
import subprocess
import sys
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote


REQUIRED_FRONTMATTER = {"name", "description", "license", "compatibility"}
ALLOWED_FRONTMATTER = REQUIRED_FRONTMATTER | {"metadata"}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(
        r"\b(?:postgres|postgresql|mysql)(?:\+[A-Za-z0-9_.-]+)?://[^/\s:@]+:[^@\s/]+@[^\s]+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:postgres|postgresql|mysql)(?:\+[A-Za-z0-9_.-]+)?://[^\s?#]+"
        r"\?[^\s#]*(?:password|passwd|pwd)=[^&\s#]+",
        re.IGNORECASE,
    ),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
)
PRIVATE_PATTERNS = (
    ("private absolute path", re.compile(r"/" + r"(?:Users|home)/[^\s`]+", re.IGNORECASE)),
    ("private absolute path", re.compile(r"(?:[A-Za-z]:)?\\(?:Users|home)\\[^\s`]+", re.IGNORECASE)),
    ("private absolute path", re.compile(r"~/[A-Za-z0-9._-][^\s`]*")),
    (
        "private implementation or portfolio reference",
        re.compile(r"\b(?:" + "ai-" + "brain|brain-" + "bridge" + r")\b", re.IGNORECASE),
    ),
    (
        "private implementation or portfolio reference",
        re.compile(r"\b" + "sky" + "net" + r"\b", re.IGNORECASE),
    ),
    (
        "private implementation or portfolio reference",
        re.compile(
            r"\bremote supervisor,\s*sentinel,\s*mirror\s+or\s+heartbeat implementations\b",
            re.IGNORECASE,
        ),
    ),
    (
        "private implementation or portfolio reference",
        re.compile(r"\b" + "Frozilla" + "mania" + r"(?:/|\b)", re.IGNORECASE),
    ),
    ("private implementation or portfolio reference", re.compile(r"\bi[0-9]{3,}\b", re.IGNORECASE)),
    (
        "private implementation or portfolio reference",
        re.compile(
            r"\b(?:"
            + "Sun"
            + "downer"
            + r"(?: Berlin)?|NO"
            + "SERVICE|EYES "
            + r"ON|cl"
            + r"lb(?:\.community)?|Label"
            + "OS|Spin"
            + "tunes|Förder"
            + "finder|Funding "
            + "Radar|Hyper"
            + "normal|AI Persona "
            + r"Factory)\b",
            re.IGNORECASE,
        ),
    ),
)

# Exact-line digests avoid embedding forbidden identifiers in this global scanner.
# A path or content change invalidates the exception instead of widening it.
PRIVATE_LINE_ALLOWLIST_DIGESTS = {
    (
        "scripts/validate_protocols.py",
        "private implementation or portfolio reference",
    ): {
        "dfc3e91bba3c20f3503e7514cb2fd5b0b9be9568ecf2e88db038bed4b82f97d0",
        "3445258c3adf9fbccc4f22904ac7be7bfea20049a65427f1e114e5c98c692b42",
        "9a433b45bd3f07c08aca36fd2af526809cd3d38f123338ad38bcdad9a1cd330e",
    },
    (
        "scripts/validate_repository.py",
        "private implementation or portfolio reference",
    ): {
        "cc2dc95a71045fed9b80c4a481bc01e7ea59f1087d94e903f19ba97994488a2a",
        "d7b4a342f1cb9666e75d9e7c61e673b1c50b29459832d53fc29f1b87bc0d0858",
    },
}
EXCLUDED_PARTS = {".git", ".the-loop", "__pycache__", "node_modules", ".venv"}
MAX_DECODE_ROUNDS = 8
MAX_GIT_OBJECTS = 100_000
MAX_GIT_OBJECT_BYTES = 16 * 1024 * 1024
MAX_GIT_TOTAL_BYTES = 64 * 1024 * 1024
MAX_GIT_COMMAND_BYTES = 16 * 1024 * 1024
MAX_GIT_PATH_OCCURRENCES = 500_000
HISTORY_CURRENT_ALLOWLIST_PATHS: set[str] = set()


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _has_symlink_component(path: Path, root: Path) -> bool:
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _iter_repository_entries(root: Path):
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name, reverse=True)
        except OSError:
            continue

        for entry in entries:
            if entry.name in EXCLUDED_PARTS:
                continue
            path = Path(entry.path)
            try:
                if entry.is_symlink():
                    yield "symlink", path
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    yield "file", path
            except OSError:
                continue


def _git_command(
    root: Path,
    args: list[str],
    *,
    input_data: bytes | None = None,
    output_limit: int = MAX_GIT_COMMAND_BYTES,
) -> tuple[bytes | None, str | None]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_GRAFT_FILE": os.devnull},
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "Git command could not complete"
    if result.returncode != 0:
        return None, "Git command failed"
    if len(result.stdout) > output_limit:
        return None, "Git command output exceeds the bounded scan limit"
    return result.stdout, None


def _git_repository_root(root: Path) -> tuple[bool, list[str]]:
    output, error = _git_command(root, ["rev-parse", "--show-toplevel"])
    if error is not None:
        return False, ([f"git index: {error}"] if (root / ".git").exists() else [])
    assert output is not None
    try:
        discovered_root = Path(os.fsdecode(output).strip()).resolve()
    except (OSError, ValueError):
        return False, ["git index: invalid repository root"]
    if discovered_root != root:
        return False, []
    return True, []


def _load_git_objects(
    root: Path,
    object_ids: list[str],
    *,
    context: str,
) -> tuple[dict[str, tuple[str, bytes]], list[str]]:
    unique_ids = list(dict.fromkeys(object_ids))
    if len(unique_ids) > MAX_GIT_OBJECTS:
        return {}, [f"{context}: object count exceeds the bounded scan limit"]
    if not unique_ids:
        return {}, []
    request = ("\n".join(unique_ids) + "\n").encode("ascii")
    metadata_output, metadata_error = _git_command(
        root,
        ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input_data=request,
    )
    if metadata_error is not None:
        return {}, [f"{context}: {metadata_error} while reading object metadata"]
    assert metadata_output is not None

    metadata: dict[str, tuple[str, int]] = {}
    for line in metadata_output.splitlines():
        fields = line.split()
        if len(fields) != 3:
            return {}, [f"{context}: malformed Git object metadata"]
        try:
            object_id = fields[0].decode("ascii")
            object_type = fields[1].decode("ascii")
            size = int(fields[2])
        except (UnicodeError, ValueError):
            return {}, [f"{context}: malformed Git object metadata"]
        if size < 0 or size > MAX_GIT_OBJECT_BYTES:
            return {}, [f"{context}: object {object_id} exceeds the bounded scan limit"]
        metadata[object_id] = (object_type, size)
    if set(metadata) != set(unique_ids):
        return {}, [f"{context}: Git object metadata is incomplete"]
    total_size = sum(size for _, size in metadata.values())
    if total_size > MAX_GIT_TOTAL_BYTES:
        return {}, [f"{context}: aggregate object bytes exceed the bounded scan limit"]

    batch_output, batch_error = _git_command(
        root,
        ["cat-file", "--batch"],
        input_data=request,
        output_limit=total_size + len(unique_ids) * 256,
    )
    if batch_error is not None:
        return {}, [f"{context}: {batch_error} while reading canonical object bytes"]
    assert batch_output is not None

    objects: dict[str, tuple[str, bytes]] = {}
    cursor = 0
    for expected_id in unique_ids:
        header_end = batch_output.find(b"\n", cursor)
        if header_end < 0:
            return {}, [f"{context}: truncated Git object header"]
        fields = batch_output[cursor:header_end].split()
        if len(fields) != 3:
            return {}, [f"{context}: malformed Git object header"]
        try:
            object_id = fields[0].decode("ascii")
            object_type = fields[1].decode("ascii")
            size = int(fields[2])
        except (UnicodeError, ValueError):
            return {}, [f"{context}: malformed Git object header"]
        if object_id != expected_id or metadata.get(object_id) != (object_type, size):
            return {}, [f"{context}: Git object metadata changed during scan"]
        payload_start = header_end + 1
        payload_end = payload_start + size
        if payload_end >= len(batch_output) or batch_output[payload_end:payload_end + 1] != b"\n":
            return {}, [f"{context}: truncated Git object payload"]
        objects[object_id] = (object_type, batch_output[payload_start:payload_end])
        cursor = payload_end + 1
    if cursor != len(batch_output):
        return {}, [f"{context}: unexpected trailing Git object bytes"]
    return objects, []


def _tracked_repository_entries(
    root: Path,
) -> tuple[list[tuple[str, Path]], list[tuple[str, str, str]], list[str]]:
    is_repository, root_errors = _git_repository_root(root)
    if not is_repository:
        return [], [], root_errors

    listing, listing_error = _git_command(root, ["ls-files", "--stage", "-z", "--full-name"])
    if listing_error is not None:
        return [], [], [f"git index: {listing_error} while enumerating tracked entries"]
    assert listing is not None

    entries: list[tuple[str, Path]] = []
    index_records: list[tuple[str, str, str]] = []
    errors: list[str] = []
    for record in listing.split(b"\0"):
        if not record:
            continue
        try:
            header, encoded_path = record.split(b"\t", 1)
            mode_bytes, object_id_bytes, stage_bytes = header.split()
            mode = mode_bytes.decode("ascii")
            object_id = object_id_bytes.decode("ascii")
            stage = stage_bytes.decode("ascii")
            relative = Path(os.fsdecode(encoded_path))
        except (ValueError, UnicodeError):
            errors.append("git index: malformed tracked entry")
            continue
        if relative.is_absolute() or ".." in relative.parts:
            errors.append("git index: tracked entry escapes repository")
            continue
        if stage != "0":
            errors.append(f"{relative.as_posix()}: unresolved Git index stage")
            continue
        relative_text = relative.as_posix()
        path = root / relative
        index_records.append((relative_text, mode, object_id))
        if _has_symlink_component(path.parent, root):
            errors.append(f"{relative_text}: tracked path has a symlinked parent component")
            continue
        if mode == "120000":
            if not path.is_symlink():
                errors.append(f"{relative_text}: tracked symlink is missing or has the wrong type")
                continue
            entries.append(("symlink", path))
        elif mode in {"100644", "100755"}:
            if path.is_symlink() or not path.is_file():
                errors.append(f"{relative_text}: tracked file is missing or has the wrong type")
                continue
            entries.append(("file", path))
        else:
            errors.append(f"{relative_text}: unsupported tracked entry mode {mode}")
    return entries, index_records, errors


def _iter_text_files(entries):
    for kind, path in entries:
        if kind != "file":
            continue
        try:
            data = path.read_bytes()
        except OSError:
            yield path, None
            continue
        yield path, data.decode("utf-8", errors="replace")


def _decode_stages(value: str) -> tuple[tuple[str, ...], bool]:
    current = value
    stages = [current]
    for _ in range(MAX_DECODE_ROUNDS):
        decoded = html.unescape(unquote(current))
        if decoded == current:
            return tuple(dict.fromkeys(stages)), True
        stages.append(decoded)
        current = decoded
    return tuple(dict.fromkeys(stages)), html.unescape(unquote(current)) == current


def _decode_bounded(value: str) -> tuple[str, bool]:
    stages, complete = _decode_stages(value)
    return stages[-1], complete


def _scan_views(value: str, *, strip_whitespace: bool) -> tuple[tuple[str, ...], bool]:
    stages, complete = _decode_stages(value)
    views: list[str] = []
    for stage in stages:
        views.extend((stage, re.sub(r"\s+", " ", stage)))
        if strip_whitespace:
            views.append(re.sub(r"\s+", "", stage))
    return tuple(dict.fromkeys(views)), complete


def _private_match_allowed(relative: str, category: str, line: str) -> bool:
    allowed = PRIVATE_LINE_ALLOWLIST_DIGESTS.get((relative, category), set())
    if not allowed:
        return False
    digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
    return digest in allowed


def _scan_public_text(
    relative: str,
    text: str,
    *,
    allow_private_allowlist: bool = True,
    allowlist_relative: str | None = None,
) -> list[str]:
    errors: list[str] = []
    secret_views, secret_complete = _scan_views(text, strip_whitespace=True)
    if not secret_complete:
        errors.append(f"{relative}: encoding exceeds public-boundary normalization limit")
    if any(pattern.search(view) for pattern in SECRET_PATTERNS for view in secret_views):
        errors.append(f"{relative}: potential credential or private key")

    lines = text.splitlines()
    allowlist_path = relative if allowlist_relative is None else allowlist_relative
    for category, pattern in PRIVATE_PATTERNS:
        filtered = "\n".join(
            "" if allow_private_allowlist and _private_match_allowed(allowlist_path, category, line) else line
            for line in lines
        )
        private_views, private_complete = _scan_views(filtered, strip_whitespace=True)
        if not private_complete:
            errors.append(f"{relative}: encoding exceeds public-boundary normalization limit")
        if any(pattern.search(view) for view in private_views):
            errors.append(f"{relative}: {category}")
    return errors


def _lexically_within_root(path: Path, root: Path, target: str) -> bool:
    if Path(target).is_absolute() or PureWindowsPath(target).is_absolute():
        return False
    parts = list(path.parent.relative_to(root).parts)
    for part in Path(target).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return False
            parts.pop()
        else:
            parts.append(part)
    return True


def _validate_symlink(path: Path, root: Path) -> list[str]:
    relative = _relative(path, root)
    try:
        target = os.readlink(path)
    except OSError:
        return [f"{relative}: symlink target is unreadable"]

    return _validate_symlink_target(relative, path, root, target)


def _validate_symlink_target(relative: str, path: Path, root: Path, target: str) -> list[str]:
    if "\0" in target:
        return [f"{relative}: symlink target contains a null byte"]

    decoded_target, complete = _decode_bounded(target)
    errors = _scan_public_text(relative, target)
    if not complete:
        errors.append(f"{relative}: encoding exceeds symlink-target normalization limit")
    if not _lexically_within_root(path, root, decoded_target):
        errors.append(f"{relative}: symlink target is absolute or escapes repository")
    return errors


def _validate_index_objects(
    root: Path,
    index_records: list[tuple[str, str, str]],
) -> tuple[dict[str, tuple[str, bytes]], list[str]]:
    objects, errors = _load_git_objects(
        root,
        [object_id for _, _, object_id in index_records],
        context="git index",
    )
    for relative, mode, object_id in index_records:
        loaded = objects.get(object_id)
        if loaded is None:
            continue
        object_type, data = loaded
        if object_type != "blob":
            errors.append(f"{relative}: tracked index entry is not a blob")
            continue
        if mode == "120000":
            target = os.fsdecode(data)
            errors.extend(_validate_symlink_target(relative, root / Path(relative), root, target))
        elif mode in {"100644", "100755"}:
            errors.extend(_scan_public_text(relative, data.decode("utf-8", errors="replace")))
    return objects, errors


def _release_ref_tips(root: Path) -> tuple[list[str], list[str]]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show-ref", "--head"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_GRAFT_FILE": os.devnull},
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return [], ["git history: Git ref enumeration could not complete"]
    if result.returncode not in {0, 1}:
        return [], ["git history: Git ref enumeration failed"]
    if len(result.stdout) > MAX_GIT_COMMAND_BYTES:
        return [], ["git history: Git ref output exceeds the bounded scan limit"]

    tips: list[str] = []
    for line in result.stdout.splitlines():
        fields = line.split(b" ", 1)
        if len(fields) != 2:
            return [], ["git history: malformed Git ref output"]
        try:
            object_id = fields[0].decode("ascii")
            refname = fields[1].decode("utf-8")
        except UnicodeError:
            return [], ["git history: malformed Git ref output"]
        if refname == "HEAD" or refname.startswith(("refs/heads/", "refs/tags/", "refs/remotes/")):
            tips.append(object_id)
    return list(dict.fromkeys(tips)), []


def _parse_tree_entries(
    object_id: str,
    data: bytes,
) -> tuple[list[tuple[str, str, str]], str | None]:
    if len(object_id) not in {40, 64}:
        return [], "git history: unsupported Git object identifier width"
    raw_object_id_size = len(object_id) // 2
    entries: list[tuple[str, str, str]] = []
    cursor = 0
    while cursor < len(data):
        mode_end = data.find(b" ", cursor)
        name_end = data.find(b"\0", mode_end + 1)
        if mode_end <= cursor or name_end < 0:
            return [], f"git history tree {object_id[:12]}: malformed tree entry"
        try:
            mode = data[cursor:mode_end].decode("ascii")
        except UnicodeError:
            return [], f"git history tree {object_id[:12]}: malformed tree mode"
        if mode not in {"40000", "100644", "100755", "120000", "160000"}:
            return [], f"git history tree {object_id[:12]}: unsupported tree mode {mode!r}"
        object_end = name_end + 1 + raw_object_id_size
        if object_end > len(data):
            return [], f"git history tree {object_id[:12]}: truncated tree object identifier"
        name = data[mode_end + 1:name_end].decode("utf-8", errors="replace")
        child_id = data[name_end + 1:object_end].hex()
        entries.append((mode, name, child_id))
        cursor = object_end
    return entries, None


def _release_object_text(
    object_id: str,
    object_type: str,
    data: bytes,
) -> tuple[str | None, str | None]:
    if object_type in {"blob", "commit", "tag"}:
        return data.decode("utf-8", errors="replace"), None
    if object_type != "tree":
        return None, f"git history: unsupported reachable object type {object_type!r}"

    entries, parse_error = _parse_tree_entries(object_id, data)
    if parse_error is not None:
        return None, parse_error
    return "\n".join(name for _, name, _ in entries), None


def _history_blob_occurrences(
    objects: dict[str, tuple[str, bytes]],
) -> tuple[dict[str, set[tuple[str, str]]], list[str]]:
    root_trees: list[str] = []
    errors: list[str] = []
    for object_id, (object_type, data) in objects.items():
        if object_type != "commit":
            continue
        first_line = data.split(b"\n", 1)[0]
        fields = first_line.split()
        if len(fields) != 2 or fields[0] != b"tree":
            errors.append(f"git history commit {object_id[:12]}: malformed root tree")
            continue
        try:
            tree_id = fields[1].decode("ascii")
        except UnicodeError:
            errors.append(f"git history commit {object_id[:12]}: malformed root tree")
            continue
        root_trees.append(tree_id)

    memo: dict[str, list[tuple[str, str, str]]] = {}
    visiting: set[str] = set()
    occurrence_count = 0

    def blob_paths(tree_id: str) -> list[tuple[str, str, str]]:
        nonlocal occurrence_count
        if tree_id in memo:
            return memo[tree_id]
        if tree_id in visiting:
            errors.append(f"git history tree {tree_id[:12]}: recursive tree reference")
            return []
        loaded = objects.get(tree_id)
        if loaded is None or loaded[0] != "tree":
            errors.append(f"git history tree {tree_id[:12]}: referenced tree is unavailable")
            return []
        visiting.add(tree_id)
        entries, parse_error = _parse_tree_entries(tree_id, loaded[1])
        if parse_error is not None:
            errors.append(parse_error)
            visiting.remove(tree_id)
            return []
        matches: list[tuple[str, str, str]] = []
        for mode, name, child_id in entries:
            if mode == "40000":
                for blob_id, blob_mode, suffix in blob_paths(child_id):
                    matches.append((blob_id, blob_mode, f"{name}/{suffix}"))
                    occurrence_count += 1
            elif mode != "160000":
                matches.append((child_id, mode, name))
                occurrence_count += 1
            if occurrence_count > MAX_GIT_PATH_OCCURRENCES:
                errors.append("git history: path occurrences exceed the bounded scan limit")
                visiting.remove(tree_id)
                return []
        visiting.remove(tree_id)
        memo[tree_id] = matches
        return matches

    occurrences: dict[str, set[tuple[str, str]]] = {}
    for tree_id in dict.fromkeys(root_trees):
        for object_id, mode, path in blob_paths(tree_id):
            occurrences.setdefault(object_id, set()).add((path, mode))
    return occurrences, errors


def _validate_release_history(
    root: Path,
) -> list[str]:
    tips, errors = _release_ref_tips(root)
    if errors or not tips:
        return errors
    reachable_output, reachable_error = _git_command(
        root,
        ["rev-list", "--objects", "--no-object-names", "--stdin"],
        input_data=("\n".join(tips) + "\n").encode("ascii"),
    )
    if reachable_error is not None:
        return [f"git history: {reachable_error} while enumerating reachable objects"]
    assert reachable_output is not None
    try:
        object_ids = [line.decode("ascii") for line in reachable_output.splitlines() if line]
    except UnicodeError:
        return ["git history: malformed reachable-object identifier"]
    objects, object_errors = _load_git_objects(root, object_ids, context="git history")
    errors.extend(object_errors)

    blob_occurrences, occurrence_errors = _history_blob_occurrences(objects)
    errors.extend(occurrence_errors)
    for object_id, (object_type, data) in objects.items():
        if object_type == "blob" and object_id in blob_occurrences:
            for relative, mode in sorted(blob_occurrences[object_id]):
                history_label = f"git history {relative} ({object_id[:12]})"
                if mode == "120000":
                    errors.extend(
                        _validate_symlink_target(
                            history_label,
                            root / Path(relative),
                            root,
                            os.fsdecode(data),
                        )
                    )
                else:
                    errors.extend(
                        _scan_public_text(
                            history_label,
                            data.decode("utf-8", errors="replace"),
                            allow_private_allowlist=relative in HISTORY_CURRENT_ALLOWLIST_PATHS,
                            allowlist_relative=relative,
                        )
                    )
            continue
        text, parse_error = _release_object_text(object_id, object_type, data)
        if parse_error is not None:
            errors.append(parse_error)
            continue
        assert text is not None
        relative = f"git history {object_type} {object_id[:12]}"
        errors.extend(_scan_public_text(relative, text, allow_private_allowlist=False))
    return errors


def _frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None

    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def _validate_skill(path: Path, root: Path, provenance: str) -> list[str]:
    errors: list[str] = []
    rel = _relative(path, root)
    fields = _frontmatter(path.read_text(encoding="utf-8"))
    if fields is None:
        return [f"{rel}: missing or unclosed YAML frontmatter"]

    missing = sorted(REQUIRED_FRONTMATTER - fields.keys())
    if missing:
        errors.append(f"{rel}: missing frontmatter fields: {', '.join(missing)}")
    unexpected = sorted(fields.keys() - ALLOWED_FRONTMATTER)
    if unexpected:
        errors.append(f"{rel}: unsupported frontmatter fields: {', '.join(unexpected)}")

    name = fields.get("name", "")
    directory_name = path.parent.name
    if not NAME_PATTERN.fullmatch(name):
        errors.append(f"{rel}: invalid skill name {name!r}")
    elif name != directory_name:
        errors.append(f"{rel}: name {name!r} does not match directory {directory_name!r}")

    if fields.get("license") != "MIT":
        errors.append(f"{rel}: license must be MIT for original repository skills")

    compatibility = fields.get("compatibility", "")
    for harness in ("Codex", "Claude Code", "Kimi Code", "OpenCode"):
        if harness not in compatibility:
            errors.append(f"{rel}: compatibility does not name {harness}")

    if name and not re.search(rf"\|\s*`{re.escape(name)}`\s*\|", provenance):
        errors.append(f"{rel}: no provenance record for {name!r}")
    return errors


def _validate_markdown_links(path: Path, text: str, root: Path) -> list[str]:
    errors: list[str] = []
    for raw_target in MARKDOWN_LINK_PATTERN.findall(text):
        target = raw_target.strip().strip("<>").split(" ", 1)[0]
        if not target or target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        path_part = unquote(target.split("#", 1)[0])
        if not path_part:
            continue
        resolved = ((root / path_part.lstrip("/")) if path_part.startswith("/") else (path.parent / path_part)).resolve()
        if not resolved.is_relative_to(root):
            errors.append(f"{_relative(path, root)}: relative link escapes repository {raw_target!r}")
            continue
        if not resolved.exists():
            errors.append(f"{_relative(path, root)}: broken relative link {raw_target!r}")
    return errors


def validate(root: Path, *, release_history: bool = False) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    entries = list(_iter_repository_entries(root))
    tracked_entries, index_records, tracked_errors = _tracked_repository_entries(root)
    errors.extend(tracked_errors)
    _, index_errors = _validate_index_objects(root, index_records)
    errors.extend(index_errors)
    if release_history:
        errors.extend(_validate_release_history(root))
    by_path = {path: kind for kind, path in entries}
    for kind, path in tracked_entries:
        by_path[path] = kind
    entries = [(kind, path) for path, kind in sorted(by_path.items(), key=lambda item: item[0].as_posix())]

    for kind, path in entries:
        if kind == "symlink":
            errors.extend(_validate_symlink(path, root))

    license_path = root / "LICENSE"
    if (
        license_path.is_symlink()
        or not license_path.is_file()
        or "MIT License" not in license_path.read_text(encoding="utf-8")
    ):
        errors.append("LICENSE: missing MIT licence text")

    provenance_path = root / "docs" / "provenance" / "skill-records.md"
    provenance = (
        provenance_path.read_text(encoding="utf-8")
        if not _has_symlink_component(provenance_path, root) and provenance_path.is_file()
        else ""
    )
    if not provenance:
        errors.append("docs/provenance/skill-records.md: missing provenance records")

    skills_root = root / ".agents" / "skills"
    if skills_root.exists() and not skills_root.is_symlink() and not skills_root.parent.is_symlink():
        directories = sorted(
            path for path in skills_root.iterdir()
            if not path.is_symlink() and path.is_dir()
        )
        for directory in directories:
            if not (directory / "SKILL.md").is_file():
                errors.append(f"{_relative(directory, root)}: skill directory has no SKILL.md")
        for directory in directories:
            skill_path = directory / "SKILL.md"
            if skill_path.is_file() and not skill_path.is_symlink():
                errors.extend(_validate_skill(skill_path, root, provenance))

    for path, text in _iter_text_files(entries):
        rel = _relative(path, root)
        if text is None:
            errors.append(f"{rel}: public file is unreadable")
            continue
        errors.extend(_scan_public_text(rel, text))
        if path.suffix.lower() == ".md":
            errors.extend(_validate_markdown_links(path, text, root))

    return sorted(set(errors))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate(root, release_history=True)
    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    skill_count = len(list((root / ".agents" / "skills").glob("*/SKILL.md")))
    print(f"Repository validation passed ({skill_count} public skills checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
