from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_protocols.py"
SPEC = importlib.util.spec_from_file_location("validate_protocols", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def protocol_text(title: str, prefix: str, links: str = "No local dependencies.") -> str:
    return f"""# {title}

## Purpose

Define one synthetic public contract.

## Normative requirements

- **[{prefix}-001]** Implementations MUST preserve this synthetic invariant.

## Failure and halt behavior

Validation failure halts the synthetic operation.

## Evidence

A validator result is required.

## Cross-references

{links}
"""


class ProtocolContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        protocols = self.root / "protocols"
        protocols.mkdir()
        for filename, prefix in VALIDATOR.PROTOCOLS.items():
            title = filename.removesuffix(".md").replace("-", " ").title()
            (protocols / filename).write_text(protocol_text(title, prefix), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def errors(self) -> list[str]:
        return VALIDATOR.validate(self.root)

    def protocol(self, filename: str) -> Path:
        return self.root / "protocols" / filename

    def test_clean_protocol_set_passes(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            protocol_text(
                "Stage contracts",
                "STG",
                "See [routing requirement](skill-routing.md#rte-001).",
            ),
            encoding="utf-8",
        )
        self.assertEqual([], self.errors())

    def test_protocol_heading_reference_passes(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            protocol_text("Stage contracts", "STG", "See [routing purpose](skill-routing.md#purpose)."),
            encoding="utf-8",
        )
        self.assertEqual([], self.errors())

    def test_missing_protocol_fails(self) -> None:
        self.protocol("watcher-contract.md").unlink()
        self.assertTrue(any("watcher-contract.md: missing required protocol" in error for error in self.errors()))

    def test_unexpected_eleventh_protocol_fails(self) -> None:
        self.protocol("extra.md").write_text(protocol_text("Extra", "EXT"), encoding="utf-8")
        self.assertTrue(any("unexpected protocol" in error for error in self.errors()))

    def test_protocol_index_readme_is_not_an_eleventh_contract(self) -> None:
        self.protocol("README.md").write_text("# Shared protocols\n", encoding="utf-8")
        self.assertEqual([], self.errors())

    def test_duplicate_requirement_id_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        text = stage.read_text(encoding="utf-8").replace(
            "- **[STG-001]** Implementations MUST preserve this synthetic invariant.",
            "- **[STG-001]** Implementations MUST preserve this synthetic invariant.\n"
            "- **[STG-001]** Implementations SHALL reject duplicates.",
        )
        stage.write_text(text, encoding="utf-8")
        self.assertTrue(any("duplicate requirement ID STG-001" in error for error in self.errors()))

    def test_wrong_requirement_prefix_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(stage.read_text(encoding="utf-8").replace("STG-001", "RTE-002"), encoding="utf-8")
        self.assertTrue(any("must use STG-NNN prefix" in error for error in self.errors()))

    def test_untagged_normative_line_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            stage.read_text(encoding="utf-8").replace(
                "- **[STG-001]** Implementations MUST preserve this synthetic invariant.",
                "Implementations MUST preserve this synthetic invariant.",
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("normative MUST/SHALL line must begin" in error for error in self.errors()))

    def test_missing_required_section_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(stage.read_text(encoding="utf-8").replace("## Evidence", "## Proof"), encoding="utf-8")
        self.assertTrue(any("'## Evidence'" in error for error in self.errors()))

    def test_missing_local_file_reference_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            protocol_text("Stage contracts", "STG", "See [missing](missing-protocol.md)."),
            encoding="utf-8",
        )
        self.assertTrue(any("unresolved local reference" in error for error in self.errors()))

    def test_missing_protocol_requirement_reference_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            protocol_text("Stage contracts", "STG", "See [missing ID](skill-routing.md#rte-999)."),
            encoding="utf-8",
        )
        self.assertTrue(any("unresolved protocol requirement" in error for error in self.errors()))

    def test_missing_protocol_heading_reference_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            protocol_text("Stage contracts", "STG", "See [missing heading](skill-routing.md#not-a-heading)."),
            encoding="utf-8",
        )
        self.assertTrue(any("unresolved protocol requirement" in error for error in self.errors()))

    def test_non_protocol_anchor_is_not_interpreted_as_protocol_id(self) -> None:
        prd = self.root / "docs" / "specs" / "prd.md"
        prd.parent.mkdir(parents=True)
        prd.write_text("# PRD\n\n- **FR-037** Example.\n", encoding="utf-8")
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            protocol_text("Stage contracts", "STG", "See [PRD](../docs/specs/prd.md#fr-037)."),
            encoding="utf-8",
        )
        self.assertEqual([], self.errors())

    def test_private_path_leakage_fails(self) -> None:
        examples = (
            "/" + "Users/example/private",
            "/" + "home/example/private",
            "~" + "/private",
        )
        for example in examples:
            with self.subTest(example=example):
                stage = self.protocol("stage-contracts.md")
                original = stage.read_text(encoding="utf-8")
                stage.write_text(original + f"\n{example}\n", encoding="utf-8")
                self.assertTrue(any("private implementation or portfolio reference" in error for error in self.errors()))
                stage.write_text(original, encoding="utf-8")

    def test_secret_pattern_fails(self) -> None:
        stage = self.protocol("stage-contracts.md")
        stage.write_text(
            stage.read_text(encoding="utf-8") + "\nToken: " + "github_pat_" + ("A" * 24) + "\n",
            encoding="utf-8",
        )
        self.assertTrue(any("potential credential" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
