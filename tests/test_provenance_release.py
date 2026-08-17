from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs" / "provenance" / "skill-records.md"
ROW = re.compile(
    r"^\| `(?P<skill>[a-z0-9-]+)` \| `(?P<path>\.agents/skills/[^`]+/SKILL\.md)` "
    r"\| `(?P<digest>[0-9a-f]{64})` \| MIT \| `(?P<commit>[0-9a-f]{7,40})` "
    r"\| (?P<evidence>[^|]+) \|$"
)
EXPECTED = {
    path.parent.name for path in (ROOT / ".agents" / "skills").glob("*/SKILL.md")
}


class ProvenanceReleaseContracts(unittest.TestCase):
    def records(self) -> list[dict[str, str]]:
        rows = []
        for line in RECORDS.read_text(encoding="utf-8").splitlines():
            match = ROW.match(line)
            if match:
                rows.append(match.groupdict())
        return rows

    def test_all_public_skill_hashes_match_the_shipping_files(self) -> None:
        rows = self.records()
        self.assertEqual(31, len(rows))
        self.assertEqual(EXPECTED, {row["skill"] for row in rows})
        for row in rows:
            with self.subTest(skill=row["skill"]):
                path = ROOT / row["path"]
                self.assertEqual(row["skill"], path.parent.name)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["digest"])

    def test_nonpassing_live_evidence_keeps_launch_manifest_pre_release(self) -> None:
        nonpassing = [
            row
            for row in self.records()
            if not row["evidence"].strip().startswith("passed:")
        ]
        manifest = json.loads((ROOT / "docs" / "release" / "launch-manifest.json").read_text(encoding="utf-8"))
        if nonpassing:
            self.assertEqual("pre_release", manifest["release"]["status"])
            self.assertEqual("private", manifest["release"]["repository_visibility"])
            self.assertIsNone(manifest["release"]["tag"])

    def test_installed_skills_name_their_offline_execution_surface(self) -> None:
        statement = "Core execution does not require network access or the source checkout."
        management = {
            "the-loop-setup": ".the-loop/toolkit/scripts/the_loop_setup.py",
            "the-loop-doctor": ".the-loop/toolkit/scripts/the_loop_doctor.py",
        }
        for skill, executable in management.items():
            with self.subTest(skill=skill):
                text = (ROOT / ".agents" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(executable, text)
        for skill in sorted(EXPECTED - set(management) - {"the-loop-parallel"}):
            with self.subTest(skill=skill):
                text = (ROOT / ".agents" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(statement, text)
        parallel = (ROOT / ".agents" / "skills" / "the-loop-parallel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("bounded", parallel.casefold())
        self.assertIn("fallback", parallel.casefold())


if __name__ == "__main__":
    unittest.main()
