from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
FIXTURE = ROOT / "tests" / "fixtures" / "skills" / "bounded-missions.json"
SHIPPING_SKILLS = {
    "audit",
    "bootstrap-agent-context",
    "build",
    "close",
    "decision-log",
    "feature-tracker",
    "handoff",
    "health-check",
    "idea-to-brief",
    "live-state-preflight",
    "portfolio-review",
    "pre-commit-review",
    "resolve",
    "retrospective",
    "session-summary",
    "spec-pack",
    "stack-summary",
    "strategize",
    "test",
    "the-loop",
    "the-loop-auto",
    "the-loop-autonomy",
    "the-loop-cloud",
    "the-loop-control",
    "the-loop-doctor",
    "the-loop-endless",
    "the-loop-parallel",
    "the-loop-setup",
    "the-loop-skill-creator",
    "the-loop-skill-planner",
    "the-loop-watch",
}

SKILLS = {
    "the-loop": "orchestration.attended",
    "the-loop-auto": "orchestration.bounded_auto",
    "strategize": "lifecycle.strategize",
    "spec-pack": "lifecycle.spec_pack",
    "build": "lifecycle.build",
    "test": "lifecycle.test",
    "resolve": "lifecycle.resolve",
    "health-check": "feeder.health_check",
    "audit": "feeder.audit",
    "close": "lifecycle.close",
}

REQUIRED_HEADINGS = {
    "## Purpose",
    "## Use when",
    "## Required inputs",
    "## Procedure",
    "## Output contract",
    "## Evidence gate",
    "## Track requirements",
    "## Safety and authority",
    "## Self-refutation",
    "## Halt conditions",
    "## References",
}

REQUIRED_PROTOCOL_LINKS = {
    "stage-contracts.md",
    "skill-routing.md",
    "code-non-code-tracks.md",
    "autonomy-policy.md",
    "run-state-leases.md",
    "issue-ledger.md",
    "evidence-contract.md",
}

ORCHESTRATOR_PROTOCOL_LINKS = REQUIRED_PROTOCOL_LINKS | {
    "workflow-dispatch.md",
    "watcher-contract.md",
    "harness-capability-map.md",
}


def frontmatter(text: str) -> tuple[dict[str, str], dict[str, str]]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}, {}
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return {}, {}

    top: dict[str, str] = {}
    metadata: dict[str, str] = {}
    in_metadata = False
    for line in lines[1:closing]:
        if line == "metadata:":
            top["metadata"] = ""
            in_metadata = True
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if line.startswith("  ") and in_metadata:
            metadata[key.strip()] = value.strip().strip("\"'")
        elif not line.startswith((" ", "\t")):
            top[key.strip()] = value.strip().strip("\"'")
            in_metadata = False
    return top, metadata


class BundledFallbackPackageTests(unittest.TestCase):
    def test_all_thirty_one_shipping_packages_exist(self) -> None:
        missing = [
            name for name in SHIPPING_SKILLS if not (SKILLS_ROOT / name / "SKILL.md").is_file()
        ]
        self.assertEqual([], missing, f"missing bundled fallback packages: {missing}")
        self.assertEqual(
            SHIPPING_SKILLS,
            {path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")},
        )

    def test_all_shipping_frontmatter_is_portable(self) -> None:
        for name in SHIPPING_SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                top, metadata = frontmatter(text)
                self.assertEqual(
                    {"name", "description", "license", "compatibility", "metadata"},
                    set(top),
                )
                self.assertEqual(name, top["name"])
                self.assertTrue(top["description"])
                self.assertEqual("MIT", top["license"])
                self.assertEqual("Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness", top["compatibility"])
                self.assertTrue(metadata.get("the-loop-capability"))
                self.assertEqual("0.1", metadata.get("the-loop-version"))

    def test_frontmatter_is_portable_and_complete(self) -> None:
        for name, capability in SKILLS.items():
            with self.subTest(skill=name):
                text = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                top, metadata = frontmatter(text)
                self.assertEqual(
                    {"name", "description", "license", "compatibility", "metadata"},
                    set(top),
                )
                self.assertEqual(name, top["name"])
                self.assertTrue(top["description"])
                self.assertEqual("MIT", top["license"])
                self.assertEqual("Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness", top["compatibility"])
                self.assertEqual(
                    {"the-loop-capability": capability, "the-loop-version": "0.1"},
                    metadata,
                )

    def test_each_package_has_complete_fallback_contract(self) -> None:
        for name in SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                headings = {line for line in text.splitlines() if line.startswith("## ")}
                self.assertTrue(REQUIRED_HEADINGS.issubset(headings))
                for field in (
                    "run ID",
                    "declared asset",
                    "track",
                    "done gate",
                    "authority",
                    "evidence",
                    "halt",
                ):
                    self.assertIn(field, text)
                self.assertIn("bundled fallback", text.lower())
                self.assertIn("code track", text.lower())
                self.assertIn("non-code track", text.lower())

    def test_protocol_references_are_complete_and_resolve(self) -> None:
        link_pattern = re.compile(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")
        for name in SKILLS:
            with self.subTest(skill=name):
                path = SKILLS_ROOT / name / "SKILL.md"
                text = path.read_text(encoding="utf-8")
                targets = link_pattern.findall(text)
                protocol_names = {Path(target).name for target in targets if "protocols/" in target}
                self.assertTrue(REQUIRED_PROTOCOL_LINKS.issubset(protocol_names))
                if name in {"the-loop", "the-loop-auto"}:
                    self.assertTrue(ORCHESTRATOR_PROTOCOL_LINKS.issubset(protocol_names))
                for target in targets:
                    if target.startswith(("https://", "http://", "mailto:")):
                        continue
                    self.assertTrue((path.parent / target).resolve().exists(), target)

    def test_packages_are_harness_neutral_and_public(self) -> None:
        forbidden = (
            re.compile(
                r"(?:/" + r"(?:Users|home)/|" + "~" + r"/|[A-Za-z]:\\\\" + r"Users\\\\)"
            ),
            re.compile(r"\.(?:claude|kimi-code|opencode)/skills"),
            re.compile(r"\b(?:subagent|agent swarm) API\b", re.IGNORECASE),
        )
        for name in SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                for pattern in forbidden:
                    self.assertIsNone(pattern.search(text), pattern.pattern)

    def test_attended_and_auto_are_bounded_without_third_party_providers(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual({"loop", "auto"}, {mission["mode"] for mission in fixture["missions"]})
        for mission in fixture["missions"]:
            self.assertEqual([], mission["installed_providers"])
            self.assertEqual("bundled", mission["expected_provider_source"])
            self.assertEqual("complete", mission["expected_status"])
            self.assertEqual("strategize", mission["stages"][0])
            self.assertEqual("close", mission["stages"][-1])
            for stage in mission["stages"]:
                self.assertTrue((SKILLS_ROOT / stage / "SKILL.md").is_file(), stage)

        loop_text = (SKILLS_ROOT / "the-loop" / "SKILL.md").read_text(encoding="utf-8")
        auto_text = (SKILLS_ROOT / "the-loop-auto" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("strategize -> spec_pack -> build -> test -> close", loop_text)
        self.assertIn("test -> resolve -> test", loop_text)
        self.assertIn("one declared asset", auto_text)
        self.assertIn("must not select unrelated work", auto_text.lower())
        self.assertIn("must not enter an unbounded monitor", auto_text.lower())

    def test_specialized_stage_contracts_are_present(self) -> None:
        required_phrases = {
            "strategize": ("problem statement", "success measures", "strategic fork"),
            "spec-pack": ("six documents", "requirement-to-slice", "implementation-ready"),
            "build": ("one approved slice", "unrelated changes", "smallest relevant checks"),
            "test": ("attempt to falsify", "reproducible evidence", "surviving defect"),
            "resolve": ("verification_pending", "regression procedure", "reopens"),
            "health-check": ("observed symptom", "without silently fixing", "entry packet"),
            "audit": ("declared contracts", "sampled", "without silently fixing"),
            "close": ("open blocking issue", "portable handoff", "authoritative evidence"),
        }
        for name, phrases in required_phrases.items():
            with self.subTest(skill=name):
                text = (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                for phrase in phrases:
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
