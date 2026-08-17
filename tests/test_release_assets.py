from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseAssetContracts(unittest.TestCase):
    def load_json(self, relative: str) -> dict:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_code_and_noncode_examples_are_complete_and_synthetic(self) -> None:
        required = {
            "code": "tests/fixtures/conformance/assets/code.json",
            "noncode": "tests/fixtures/conformance/assets/noncode.json",
        }
        for track, fixture_path in required.items():
            with self.subTest(track=track):
                fixture = self.load_json(fixture_path)
                self.assertEqual(track, fixture["track"])
                self.assertEqual(
                    {
                        "schema_version",
                        "asset_id",
                        "track",
                        "objective",
                        "live_state",
                        "approved_slice",
                        "done_gate",
                        "evidence",
                        "halt_condition",
                    },
                    set(fixture),
                )
                self.assertTrue(fixture["evidence"])
                readme = (ROOT / "examples" / track / "README.md").read_text(encoding="utf-8")
                self.assertIn(fixture["objective"], readme)
                self.assertIn("synthetic", readme.lower())

    def test_conformance_matrix_has_twelve_unique_required_scenarios(self) -> None:
        matrix = self.load_json("tests/fixtures/conformance/scenarios.json")
        scenarios = matrix["scenarios"]
        expected = {
            "setup",
            "doctor",
            "explicit-loop",
            "verified-provider-route",
            "permission-denial",
            "provider-failure-fallback",
            "attended-code-lifecycle",
            "attended-noncode-lifecycle",
            "health-check-feeder",
            "audit-feeder",
            "auto-green",
            "auto-halt-recover-close",
        }
        identifiers = [scenario["id"] for scenario in scenarios]
        self.assertEqual(12, len(identifiers))
        self.assertEqual(12, len(set(identifiers)))
        self.assertEqual(expected, set(identifiers))
        for scenario in scenarios:
            self.assertEqual(
                {"id", "capability", "track", "expected_artifacts", "safety_assertions"},
                set(scenario),
            )
            self.assertTrue(scenario["expected_artifacts"])
            self.assertTrue(scenario["safety_assertions"])

    def test_launch_manifest_describes_the_complete_v0_1_release(self) -> None:
        manifest = self.load_json("docs/release/launch-manifest.json")
        self.assertEqual("SYSTEM ERROR'S THE LOOP", manifest["product"]["name"])
        self.assertEqual("MIT", manifest["product"]["license"])
        self.assertEqual(
            "https://github.com/System-Error-Worldwide/the-loop",
            manifest["product"]["repository_url"],
        )
        self.assertEqual("https://systemerror.app/services/", manifest["ctas"]["secondary"])
        self.assertEqual("release_ready", manifest["release"]["status"])
        self.assertNotIn("repository_visibility", manifest["release"])
        self.assertNotIn("tag", manifest["release"])
        self.assertNotIn("code_baseline_commit", manifest["release"])
        self.assertNotIn("latest_compatibility_evidence_commit", manifest["release"])
        inventory = manifest["package_inventory"]
        self.assertEqual(31, inventory["total"])
        self.assertEqual(31, len(inventory["skills"]))
        self.assertEqual(31, len(set(inventory["skills"])))
        self.assertEqual(
            {path.parent.name for path in (ROOT / ".agents" / "skills").glob("*/SKILL.md")},
            set(inventory["skills"]),
        )
        self.assertEqual(
            {"codex", "claude_code", "kimi_code", "opencode", "deepseek_harness"},
            set(manifest["compatibility"]),
        )
        self.assertTrue(all(entry["adapter_status"] == "included" for entry in manifest["compatibility"].values()))
        self.assertTrue(all(entry["installation_status"] == "verified" for entry in manifest["compatibility"].values()))
        self.assertTrue(all(entry["discovery_status"] == "verified" for entry in manifest["compatibility"].values()))
        self.assertTrue(all("behavior_status" not in entry for entry in manifest["compatibility"].values()))
        dsh = manifest["compatibility"]["deepseek_harness"]
        self.assertEqual("0.1.0-rc.6", dsh["version"])
        self.assertEqual("included", dsh["adapter_status"])
        self.assertEqual("verified", dsh["installation_status"])
        self.assertEqual("verified", dsh["discovery_status"])
        self.assertNotIn("evaluated_harnesses", manifest)
        self.assertNotIn("limitations", manifest)

        launch_text = json.dumps(manifest).lower()
        for stale in (
            "pre_release",
            "repository_visibility",
            "blocked_auth",
            "blocked_runtime",
            "blocked_isolation",
            "runtime_preview",
            "contract_unverified",
            "adapter_pending",
            "not_implemented",
        ):
            self.assertNotIn(stale, launch_text)

    def test_release_asset_links_are_repository_relative_or_locked_https(self) -> None:
        manifest = self.load_json("docs/release/launch-manifest.json")
        for relative in manifest["examples"].values():
            self.assertFalse(relative.startswith("/"))
            self.assertTrue((ROOT / relative).is_file())
        for key, value in manifest["ctas"].items():
            with self.subTest(cta=key):
                self.assertTrue(value.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
