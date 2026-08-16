#!/usr/bin/env python3
"""Validate the ten public protocol contracts for THE LOOP."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


PROTOCOLS = {
    "stage-contracts.md": "STG",
    "skill-routing.md": "RTE",
    "code-non-code-tracks.md": "TRK",
    "workflow-dispatch.md": "DSP",
    "autonomy-policy.md": "AUT",
    "run-state-leases.md": "RUN",
    "issue-ledger.md": "ISS",
    "evidence-contract.md": "EVD",
    "watcher-contract.md": "WAT",
    "harness-capability-map.md": "CAP",
}

REQUIRED_HEADINGS = (
    "## Purpose",
    "## Normative requirements",
    "## Failure and halt behavior",
    "## Evidence",
    "## Cross-references",
)

TITLE_PATTERN = re.compile(r"^# [^#\s].+$")
MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
REQUIREMENT_PATTERN = re.compile(r"^- \*\*\[([A-Z]{3}-[0-9]{3})\]\*\*\s+(.+)$")
NORMATIVE_PATTERN = re.compile(r"\b(?:MUST NOT|SHALL NOT|MUST|SHALL)\b")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
REQUIREMENT_ANCHOR_PATTERN = re.compile(r"^[a-z]{3}-[0-9]{3}$")

SECRET_PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\b(?:postgres|postgresql|mysql)://[^\s]+", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
)

PRIVATE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9:])/(?:Users|home)/[^\s`]+"),
    re.compile(r"~/(?:[^\s`]+)"),
)


def _target_from_link(raw_target: str) -> tuple[str, str | None]:
    target = raw_target.strip().strip("<>").split(" ", 1)[0]
    path_part, separator, fragment = target.partition("#")
    return unquote(path_part), unquote(fragment).lower() if separator else None


def _heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = MARKDOWN_HEADING_PATTERN.fullmatch(line)
        if match is None:
            continue
        heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", match.group(1))
        heading = re.sub(r"[`*_~]", "", heading).lower()
        heading = re.sub(r"[^\w\s-]", "", heading)
        base = re.sub(r"\s+", "-", heading.strip())
        count = counts.get(base, 0)
        anchor = base if count == 0 else f"{base}-{count}"
        counts[base] = count + 1
        if anchor:
            anchors.add(anchor)
    return anchors


def _validate_links(
    path: Path,
    text: str,
    root: Path,
    declarations: dict[Path, set[str]],
    heading_anchors: dict[Path, set[str]],
) -> list[str]:
    errors: list[str] = []
    for raw_target in MARKDOWN_LINK_PATTERN.findall(text):
        target = raw_target.strip().strip("<>").split(" ", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        path_part, fragment = _target_from_link(raw_target)
        if path_part.startswith("/"):
            errors.append(f"{path.relative_to(root)}: local link must be repository-relative {raw_target!r}")
            continue
        resolved = (path.parent / path_part).resolve() if path_part else path.resolve()
        if not resolved.is_relative_to(root):
            errors.append(f"{path.relative_to(root)}: local link escapes repository {raw_target!r}")
            continue
        if not resolved.is_file():
            errors.append(f"{path.relative_to(root)}: unresolved local reference {raw_target!r}")
            continue
        if resolved in declarations and fragment:
            requirement_resolves = (
                REQUIREMENT_ANCHOR_PATTERN.fullmatch(fragment) is not None
                and fragment.upper() in declarations[resolved]
            )
            if not requirement_resolves and fragment not in heading_anchors[resolved]:
                errors.append(f"{path.relative_to(root)}: unresolved protocol requirement {raw_target!r}")
    return errors


def validate(root: Path) -> list[str]:
    """Return sorted contract errors without changing the repository."""

    root = root.resolve()
    protocols_root = root / "protocols"
    errors: list[str] = []
    documents: dict[Path, tuple[str, str]] = {}

    if not protocols_root.is_dir():
        return ["protocols: missing protocol directory"]

    expected_names = set(PROTOCOLS)
    actual_names = {
        path.name
        for path in protocols_root.glob("*.md")
        if path.is_file() and path.name != "README.md"
    }
    for missing in sorted(expected_names - actual_names):
        errors.append(f"protocols/{missing}: missing required protocol")
    for unexpected in sorted(actual_names - expected_names):
        errors.append(f"protocols/{unexpected}: unexpected protocol; exactly ten are allowed")

    for filename, prefix in PROTOCOLS.items():
        path = protocols_root / filename
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"protocols/{filename}: cannot read UTF-8 protocol: {exc}")
            continue
        documents[path.resolve()] = (prefix, text)

    declarations: dict[Path, set[str]] = {}
    heading_anchors = {path: _heading_anchors(text) for path, (_, text) in documents.items()}
    global_ids: dict[str, str] = {}
    for path, (prefix, text) in documents.items():
        relative = path.relative_to(root).as_posix()
        lines = text.splitlines()
        titles = [line for line in lines if line.startswith("# ")]
        if len(titles) != 1 or not TITLE_PATTERN.fullmatch(titles[0]):
            errors.append(f"{relative}: requires exactly one non-empty '# <title>' heading")

        for heading in REQUIRED_HEADINGS:
            occurrences = sum(line == heading for line in lines)
            if occurrences != 1:
                errors.append(f"{relative}: requires exactly one {heading!r} section")

        ids: set[str] = set()
        for index, line in enumerate(lines, start=1):
            requirement = REQUIREMENT_PATTERN.fullmatch(line)
            if NORMATIVE_PATTERN.search(line) and requirement is None:
                errors.append(
                    f"{relative}:{index}: normative MUST/SHALL line must begin '- **[{prefix}-NNN]**'"
                )
            if requirement is None:
                continue
            requirement_id, _body = requirement.groups()
            if requirement_id[:3] != prefix:
                errors.append(
                    f"{relative}:{index}: requirement {requirement_id} must use {prefix}-NNN prefix"
                )
            if requirement_id in ids:
                errors.append(f"{relative}:{index}: duplicate requirement ID {requirement_id}")
            ids.add(requirement_id)
            prior = global_ids.get(requirement_id)
            if prior is not None:
                errors.append(f"{relative}:{index}: requirement ID {requirement_id} already declared in {prior}")
            else:
                global_ids[requirement_id] = relative
        if not ids:
            errors.append(f"{relative}: no normative requirement IDs declared")
        declarations[path] = ids

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{relative}: potential credential or private key")
                break
        for pattern in PRIVATE_PATTERNS:
            match = pattern.search(text)
            if match:
                errors.append(f"{relative}: private implementation or portfolio reference {match.group(0)!r}")
                break

    for path, (_, text) in documents.items():
        errors.extend(_validate_links(path, text, root, declarations, heading_anchors))
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        print("Protocol validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Protocol validation passed ({len(PROTOCOLS)} contracts checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
