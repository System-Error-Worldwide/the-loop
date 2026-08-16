"""Parallel-lane orchestration helpers for bounded merge decisions.

This module is a clean-room, minimal implementation for the Loop Parallel skill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .validation import ContractError, validate_relative_path


@dataclass(frozen=True)
class ParallelLaneResult:
    """Normalized parallel worker result used for merge decision checks."""

    lane_id: str
    status: str
    output_paths: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ParallelMerge:
    """Merge outcome for a parallel run."""

    status: str
    winning_lanes: tuple[str, ...]
    merged_output: tuple[str, ...]
    blocked_reason: str | None = None


def _normalized_output_paths(paths: Iterable[str]) -> tuple[str, ...]:
    normalized = []
    for value in paths:
        normalized_value = validate_relative_path(value, path="$.output_paths[]")
        normalized.append(normalized_value)
    return tuple(sorted(set(normalized)))


def _validate_evidence(evidence: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, item in enumerate(evidence):
        if not isinstance(item, str) or not item:
            raise ContractError(
                f"$.evidence[{index}]",
                "type",
                "evidence entries must be non-empty strings",
            )
        normalized.append(item)
    return tuple(normalized)


def normalize_parallel_lanes(raw_lanes: list[dict[str, Any]]) -> tuple[ParallelLaneResult, ...]:
    """Validate and normalize worker result envelopes.

    Args:
        raw_lanes: Per-lane worker results.

    Raises:
        ContractError: malformed lane envelope or overlapping output boundaries.
    """

    if not raw_lanes:
        raise ContractError("$.parallel", "required", "parallel requires at least one worker lane")

    seen_lane: set[str] = set()
    seen_paths: set[str] = set()
    normalized: list[ParallelLaneResult] = []

    for lane in raw_lanes:
        if not isinstance(lane, dict):
            raise ContractError("parallel lane must be a JSON object")

        lane_id = lane.get("lane_id")
        status = lane.get("status")
        output_paths = lane.get("output_paths")
        evidence = lane.get("evidence")

        if not isinstance(lane_id, str) or not lane_id:
            raise ContractError("$.lane_id", "type", "lane_id must be a non-empty string")
        if lane_id in seen_lane:
            raise ContractError("$.lane_id", "parallel", f"duplicate lane_id in parallel plan: {lane_id}")
        if status not in {"ready", "complete", "blocked", "failed", "unknown"}:
            raise ContractError("$.status", "parallel", "lane status must be ready, complete, blocked, failed, or unknown")
        if not isinstance(output_paths, list):
            raise ContractError("$.output_paths", "parallel", "output_paths must be a list of relative paths")
        if not isinstance(evidence, list):
            raise ContractError("$.evidence", "parallel", "evidence must be a list of strings")

        normalized_paths = _normalized_output_paths(output_paths)
        normalized_evidence = _validate_evidence(evidence)

        for value in normalized_paths:
            for existing in seen_paths:
                if value == existing or value.startswith(existing + "/") or existing.startswith(value + "/"):
                    raise ContractError(
                        "$.output_paths",
                        "parallel",
                        f"parallel lanes overlap output path: {value} and {existing}",
                    )

        normalized.append(
            ParallelLaneResult(
                lane_id=lane_id,
                status=status,
                output_paths=normalized_paths,
                evidence=normalized_evidence,
            )
        )
        seen_lane.add(lane_id)
        seen_paths.update(normalized_paths)

    return tuple(normalized)


def merge_parallel_lanes(lanes: Iterable[ParallelLaneResult]) -> ParallelMerge:
    """Merge validated lane results and return the final parent decision envelope."""

    lanes_by_status = list(lanes)
    if not lanes_by_status:
        raise ContractError("$.lanes", "required", "no lanes to merge")

    blocked = [lane for lane in lanes_by_status if lane.status in {"blocked", "failed", "unknown"}]
    if blocked:
        reasons = ",".join(sorted({lane.status for lane in blocked}))
        return ParallelMerge(
            status="blocked",
            winning_lanes=tuple(lane.lane_id for lane in lanes_by_status if lane.status in {"ready", "complete"}),
            merged_output=tuple(sorted({path for lane in lanes_by_status for path in lane.output_paths})),
            blocked_reason=f"blocked_by_{reasons}",
        )

    completed = [lane for lane in lanes_by_status if lane.status in {"ready", "complete"}]
    if not completed:
        return ParallelMerge(
            status="blocked",
            winning_lanes=tuple(),
            merged_output=tuple(),
            blocked_reason="no_completed_lanes",
        )

    merged_output = tuple(sorted({path for lane in completed for path in lane.output_paths}))
    return ParallelMerge(
        status="complete",
        winning_lanes=tuple(lane.lane_id for lane in completed),
        merged_output=merged_output,
        blocked_reason=None,
    )
