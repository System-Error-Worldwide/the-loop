from __future__ import annotations

import unittest

from the_loop.parallel import ParallelMerge, ParallelLaneResult, merge_parallel_lanes, normalize_parallel_lanes
from the_loop.validation import ContractError


class ParallelContracts(unittest.TestCase):
    def _lane(
        self,
        *,
        lane_id: str,
        status: str,
        output_paths: list[str],
        evidence: list[str],
    ) -> dict:
        return {
            "lane_id": lane_id,
            "status": status,
            "output_paths": output_paths,
            "evidence": evidence,
        }

    def test_parallel_normalization(self) -> None:
        lanes = [
            self._lane(
                lane_id="lane-a",
                status="complete",
                output_paths=["artifacts/build.json"],
                evidence=["route=ok"],
            ),
            self._lane(
                lane_id="lane-b",
                status="ready",
                output_paths=["artifacts/notes.json", "docs/readme.md"],
                evidence=["validated"],
            ),
        ]
        normalized = normalize_parallel_lanes(lanes)
        self.assertEqual(2, len(normalized))
        self.assertTrue(all(isinstance(item, ParallelLaneResult) for item in normalized))

    def test_parallel_merge_complete(self) -> None:
        lanes = normalize_parallel_lanes(
            [
                self._lane(
                    lane_id="lane-a",
                    status="complete",
                    output_paths=["artifacts/build.json"],
                    evidence=["route=ok"],
                ),
                self._lane(
                    lane_id="lane-b",
                    status="ready",
                    output_paths=["notes/summary.md"],
                    evidence=["verified"],
                ),
            ]
        )
        merged = merge_parallel_lanes(lanes)
        self.assertEqual("complete", merged.status)
        self.assertEqual(("lane-a", "lane-b"), merged.winning_lanes)
        self.assertEqual(("artifacts/build.json", "notes/summary.md"), merged.merged_output)
        self.assertIsNone(merged.blocked_reason)

    def test_parallel_overlap_conflict(self) -> None:
        with self.assertRaises(ContractError):
            normalize_parallel_lanes(
                [
                    self._lane(
                        lane_id="lane-a",
                        status="complete",
                        output_paths=["artifacts"],
                        evidence=["route=ok"],
                    ),
                    self._lane(
                        lane_id="lane-b",
                        status="complete",
                        output_paths=["artifacts/build.json"],
                        evidence=["route=ok"],
                    ),
                ]
            )

    def test_parallel_blocked_on_unknown(self) -> None:
        lanes = normalize_parallel_lanes(
            [
                self._lane(
                    lane_id="lane-a",
                    status="complete",
                    output_paths=["artifacts/build.json"],
                    evidence=["route=ok"],
                ),
                self._lane(
                    lane_id="lane-b",
                    status="unknown",
                    output_paths=["notes/summary.md"],
                    evidence=["needs-retry"],
                ),
            ]
        )
        merged = merge_parallel_lanes(lanes)
        self.assertEqual("blocked", merged.status)
        self.assertIsInstance(merged, ParallelMerge)
        self.assertEqual("blocked_by_unknown", merged.blocked_reason)


if __name__ == "__main__":
    unittest.main()

