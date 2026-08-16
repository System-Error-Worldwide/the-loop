from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_repository", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class RepositoryValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        records = self.root / "docs" / "provenance" / "skill-records.md"
        records.parent.mkdir(parents=True)
        records.write_text("| Candidate | Evidence |\n| --- | --- |\n| `test-skill` | synthetic |\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_skill(self, text: str | None = None, directory: str = "test-skill") -> Path:
        skill = self.root / ".agents" / "skills" / directory / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            text
            or """---
name: test-skill
description: Synthetic test skill.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
---

# Test skill
""",
            encoding="utf-8",
        )
        return skill

    def errors(self, *, release_history: bool = False) -> list[str]:
        return VALIDATOR.validate(self.root, release_history=release_history)

    def write_public(self, value: str) -> Path:
        path = self.root / "public.txt"
        path.write_text(value + "\n", encoding="utf-8")
        return path

    def track(self, *paths: str) -> None:
        if not (self.root / ".git").exists():
            self.git("init", "-q", "-b", "main")
        if paths:
            self.git("add", "-f", "--", *paths)

    def git(self, *args: str, input_data: bytes | None = None) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            input=input_data,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.decode("utf-8").strip()

    def commit(self, message: str = "fixture") -> None:
        self.track()
        self.git("add", "-A")
        self.git(
            "-c", "user.name=Validator Test",
            "-c", "user.email=validator@example.invalid",
            "commit", "-q", "-m", message,
        )

    def test_clean_skill_passes(self) -> None:
        self.write_skill()
        self.assertEqual([], self.errors())

    def test_missing_frontmatter_field_fails(self) -> None:
        self.write_skill(
            """---
name: test-skill
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
---
"""
        )
        self.assertTrue(any("missing frontmatter fields: description" in error for error in self.errors()))

    def test_name_mismatch_fails(self) -> None:
        self.write_skill(directory="different-directory")
        self.assertTrue(any("does not match directory" in error for error in self.errors()))

    def test_unsupported_frontmatter_fails(self) -> None:
        self.write_skill(
            """---
name: test-skill
description: Synthetic test skill.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
permissions: unrestricted
---
"""
        )
        self.assertTrue(any("unsupported frontmatter fields: permissions" in error for error in self.errors()))

    def test_missing_provenance_fails(self) -> None:
        self.write_skill()
        records = self.root / "docs" / "provenance" / "skill-records.md"
        records.write_text("| Candidate | Evidence |\n| --- | --- |\n", encoding="utf-8")
        self.assertTrue(any("no provenance record" in error for error in self.errors()))

    def test_private_path_fails(self) -> None:
        skill = self.write_skill()
        with skill.open("a", encoding="utf-8") as handle:
            handle.write("\nPrivate path: " + "/" + "Users/example/private\n")
        self.assertTrue(any("private absolute path" in error for error in self.errors()))

    def test_secret_fails(self) -> None:
        skill = self.write_skill()
        with skill.open("a", encoding="utf-8") as handle:
            handle.write("\nToken: " + "github_pat_" + ("A" * 24) + "\n")
        self.assertTrue(any("potential credential" in error for error in self.errors()))

    def test_every_secret_pattern_fails(self) -> None:
        examples = (
            "ghp_" + ("A" * 24),
            "github_pat_" + ("A" * 24),
            "AKIA" + ("A" * 16),
            "sk-" + ("A" * 24),
            "xox" + "b-" + ("A" * 20),
            "xox" + "a-" + ("A" * 20),
            "xox" + "p-" + ("A" * 20),
            "xox" + "r-" + ("A" * 20),
            "xox" + "s-" + ("A" * 20),
            "postgres" + "://user:password@database.example/test",
            "postgresql" + "://user:password@database.example/test",
            "postgresql+psycopg" + "://user:password@database.example/test",
            "postgresql" + "://database.example/test?password=secret-value",
            "mysql" + "://user:password@database.example/test",
            "-----BEGIN " + "PRIVATE KEY-----",
        )
        for example in examples:
            with self.subTest(example=example):
                path = self.root / "public.txt"
                path.write_text(f"Value: {example}\n", encoding="utf-8")
                self.assertTrue(any("potential credential" in error for error in self.errors()))
                path.unlink()

    def test_uncredentialed_database_url_passes(self) -> None:
        self.write_skill()
        (self.root / "public.txt").write_text(
            "Example: " + "postgresql" + "://database.example/test\n",
            encoding="utf-8",
        )
        self.assertEqual([], self.errors())

    def test_encoded_private_path_token_and_database_url_fail(self) -> None:
        private_path = "file://" + "/" + "Us" + "ers/example/secret"
        token = "xox" + "b-" + ("A" * 24)
        database_url = "post" + "gresql://user:password@database.example/db"
        examples = (
            quote(private_path, safe=""),
            quote(token, safe=""),
            quote(database_url, safe=""),
            "file" + "".join(f"&#{ord(character)};" for character in private_path[4:]),
            "xox" + "b&" + "#45;" + ("A" * 24),
            "post" + "gresql&" + "#58;&#47;&#47;user&#58;password&#64;database.example&#47;db",
        )
        for example in examples:
            with self.subTest(example=example):
                path = self.write_public(example)
                self.assertTrue(self.errors())
                path.unlink()

    def test_excessive_nested_encoding_fails_closed(self) -> None:
        value = "/" + "Us" + "ers/example/secret"
        for _ in range(VALIDATOR.MAX_DECODE_ROUNDS + 1):
            value = quote(value, safe="")
        self.write_public(value)
        self.assertTrue(any("normalization limit" in error for error in self.errors()))

    def test_repeated_percent_encoding_fails(self) -> None:
        private_path = "/" + "Us" + "ers/example/secret"
        token = "xox" + "b-" + ("A" * 24)
        database_url = "post" + "gresql://user:password@database.example/db"
        examples = (
            quote(quote(private_path, safe=""), safe=""),
            quote(quote(token, safe=""), safe=""),
            quote(quote(database_url, safe=""), safe=""),
        )
        for example in examples:
            with self.subTest(example=example):
                path = self.write_public(example)
                self.assertTrue(self.errors())
                path.unlink()

    def test_every_decode_stage_is_scanned_for_encoded_database_userinfo(self) -> None:
        database_prefix = "post" + "gresql://user:pa"
        examples = (
            database_prefix + "%" + "2Fss@database.example/db",
            database_prefix + "%" + "252Fss@database.example/db",
            database_prefix + "&" + "#47;ss@database.example/db",
        )
        for example in examples:
            with self.subTest(example=example):
                path = self.write_public(example)
                self.assertTrue(any("potential credential" in error for error in self.errors()))
                path.unlink()

    def test_whitespace_split_identifiers_and_secrets_fail(self) -> None:
        examples = (
            "sky " + "\n net",
            "Funding " + "\t Radar",
            "gh" + "p_ " + ("A" * 24),
            "xox" + "b-" + ("A" * 10) + " \n " + ("A" * 10),
            "post" + "gresql : / / user : password @ database.example / db",
        )
        for example in examples:
            with self.subTest(example=example):
                path = self.write_public(example)
                self.assertTrue(self.errors())
                path.unlink()

    def test_every_private_identifier_pattern_fails(self) -> None:
        examples = (
            "/" + "Users/example/private",
            "/" + "users/example/private",
            "/" + "uSeRs/example/private",
            "/" + "home/example/private",
            "C:" + "\\" + "Users\\example\\private",
            "~/" + "private/source",
            "ai-" + "brain",
            "brain-" + "bridge",
            "sky" + "net",
            "remote supervisor, " + "sentinel, mirror or heartbeat implementations",
            "Frozilla" + "mania/private",
            "i" + "1136",
            "I" + "1136",
            "Sun" + "downer",
            "NO" + "SERVICE",
            "EYES " + "ON",
            "cl" + "lb.community",
            "Label" + "OS",
            "Spin" + "tunes",
            "Förder" + "finder",
            "Funding " + "Radar",
            "Hyper" + "normal",
            "AI Persona " + "Factory",
        )
        for example in examples:
            with self.subTest(example=example):
                path = self.root / "public.txt"
                path.write_text(f"Private value: {example}\n", encoding="utf-8")
                self.assertTrue(
                    any(
                        "private implementation or portfolio reference" in error
                        or "private absolute path" in error
                        for error in self.errors()
                    )
                )
                path.unlink()

    def test_public_boundary_private_identifier_has_no_exception(self) -> None:
        self.write_skill()
        boundary = self.root / "docs" / "provenance" / "public-private-boundary.md"
        boundary.write_text(
            "- Funding " + "Radar data, application material or private vertical intelligence.\n",
            encoding="utf-8",
        )
        self.assertTrue(any("private implementation or portfolio reference" in error for error in self.errors()))

    def test_absolute_and_outside_symlink_targets_fail(self) -> None:
        (self.root / "absolute-link").symlink_to("/private/tmp/outside")
        self.assertTrue(any("symlink target is absolute or escapes repository" in error for error in self.errors()))
        (self.root / "absolute-link").unlink()
        (self.root / "windows-link").symlink_to("C:" + "\\" + "Users\\example\\outside")
        self.assertTrue(any("symlink target is absolute or escapes repository" in error for error in self.errors()))
        (self.root / "windows-link").unlink()
        (self.root / "outside-link").symlink_to("../outside")
        self.assertTrue(any("symlink target is absolute or escapes repository" in error for error in self.errors()))

    def test_encoded_private_symlink_target_fails_without_following_it(self) -> None:
        private_path = "/" + "Us" + "ers/example/secret"
        (self.root / "private-link").symlink_to(quote(private_path, safe=""))
        errors = self.errors()
        self.assertTrue(any("private absolute path" in error for error in errors))
        self.assertTrue(any("symlink target is absolute or escapes repository" in error for error in errors))
        (self.root / "private-link").unlink()
        token = "xox" + "b-" + ("A" * 24)
        (self.root / "secret-link").symlink_to(quote(token, safe=""))
        self.assertTrue(any("potential credential" in error for error in self.errors()))

    def test_internal_symlink_and_symlink_loop_are_not_followed(self) -> None:
        target = self.root / "docs" / "target.txt"
        target.write_text("Public target.\n", encoding="utf-8")
        (self.root / "internal-link").symlink_to("docs/target.txt")
        (self.root / "loop-a").symlink_to("loop-b")
        (self.root / "loop-b").symlink_to("loop-a")
        self.assertEqual([], self.errors())

    def test_untracked_generated_content_remains_excluded(self) -> None:
        generated = self.root / "node_modules"
        generated.mkdir()
        (generated / "public.txt").write_text("xox" + "b-" + ("A" * 24) + "\n", encoding="utf-8")
        (generated / "public-link").symlink_to("/" + "Users/example/private")
        self.track()
        self.assertEqual([], self.errors())

    def test_tracked_generated_text_and_symlink_are_validated(self) -> None:
        generated = self.root / "node_modules"
        generated.mkdir()
        (generated / "public.txt").write_text("xox" + "b-" + ("A" * 24) + "\n", encoding="utf-8")
        (generated / "public-link").symlink_to("/" + "Users/example/private")
        self.track("node_modules/public.txt", "node_modules/public-link")
        errors = self.errors()
        self.assertTrue(any("node_modules/public.txt: potential credential" in error for error in errors))
        self.assertTrue(any("node_modules/public-link: private absolute path" in error for error in errors))
        self.assertTrue(any("node_modules/public-link: symlink target is absolute" in error for error in errors))

    def test_tracked_internal_symlink_in_generated_directory_passes(self) -> None:
        generated = self.root / "node_modules"
        generated.mkdir()
        (generated / "target.txt").write_text("Public generated fixture.\n", encoding="utf-8")
        (generated / "public-link").symlink_to("target.txt")
        self.track("node_modules/target.txt", "node_modules/public-link")
        self.assertEqual([], self.errors())

    def test_canonical_index_bytes_win_over_safe_worktree_replacement(self) -> None:
        tracked = self.root / "tracked.txt"
        tracked.write_text("xox" + "b-" + ("A" * 24) + "\n", encoding="utf-8")
        self.track("tracked.txt")
        tracked.write_text("Safe worktree replacement.\n", encoding="utf-8")

        self.assertTrue(any("tracked.txt: potential credential" in error for error in self.errors()))

    def test_canonical_index_symlink_target_wins_over_worktree_replacement(self) -> None:
        link = self.root / "tracked-link"
        link.symlink_to("/" + "Users/example/private")
        self.track("tracked-link")
        link.unlink()
        (self.root / "safe.txt").write_text("Safe target.\n", encoding="utf-8")
        link.symlink_to("safe.txt")

        errors = self.errors()
        self.assertTrue(any("tracked-link: private absolute path" in error for error in errors))
        self.assertTrue(any("tracked-link: symlink target is absolute" in error for error in errors))

    def test_symlinked_parent_component_is_rejected_without_following_it(self) -> None:
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "tracked.txt").write_text("Safe staged content.\n", encoding="utf-8")
        self.track("nested/tracked.txt")
        nested.rename(self.root / "staged-parent")
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            (outside / "tracked.txt").write_text(
                "xox" + "b-" + ("A" * 24) + "\n",
                encoding="utf-8",
            )
            nested.symlink_to(outside, target_is_directory=True)
            errors = self.errors()

        self.assertTrue(any("nested/tracked.txt: tracked path has a symlinked parent component" in error for error in errors))

    def test_clean_reachable_history_passes(self) -> None:
        self.write_skill()
        boundary = self.root / "docs" / "provenance" / "public-private-boundary.md"
        boundary.write_text(
            "- Private orchestration, monitoring, mirroring or liveness implementations.\n"
            "- Private funding-source data, application material or vertical intelligence.\n",
            encoding="utf-8",
        )
        self.commit("clean fixture")

        self.assertEqual([], self.errors(release_history=True))

    def test_deleted_secret_remains_blocked_by_release_history(self) -> None:
        secret = self.root / "deleted.txt"
        secret.write_text("ghp_" + ("A" * 24) + "\n", encoding="utf-8")
        self.commit("add historical value")
        secret.unlink()
        self.commit("remove historical value")

        self.assertFalse(any("deleted.txt" in error for error in self.errors()))
        self.assertTrue(any("git history deleted.txt" in error and "potential credential" in error for error in self.errors(release_history=True)))

    def test_secret_on_side_branch_is_blocked_by_release_history(self) -> None:
        self.commit("safe main")
        self.git("switch", "-q", "-c", "private-side")
        (self.root / "branch.txt").write_text("sk-" + ("A" * 24) + "\n", encoding="utf-8")
        self.commit("side value")
        self.git("switch", "-q", "main")

        self.assertTrue(any("git history branch.txt" in error and "potential credential" in error for error in self.errors(release_history=True)))

    def test_secret_reachable_only_from_tag_is_blocked(self) -> None:
        self.commit("safe main")
        self.git("switch", "-q", "-c", "tag-source")
        (self.root / "tagged.txt").write_text("github_pat_" + ("A" * 24) + "\n", encoding="utf-8")
        self.commit("tagged value")
        self.git("tag", "publication-candidate")
        self.git("switch", "-q", "main")
        self.git("update-ref", "-d", "refs/heads/tag-source")

        self.assertTrue(any("git history tagged.txt" in error and "potential credential" in error for error in self.errors(release_history=True)))

    def test_secret_in_merged_and_later_sanitized_history_is_blocked(self) -> None:
        self.commit("safe base")
        self.git("switch", "-q", "-c", "feature")
        feature = self.root / "feature.txt"
        feature.write_text("mysql" + "://user:password@database.example/db\n", encoding="utf-8")
        self.commit("feature value")
        feature.write_text("Safe feature.\n", encoding="utf-8")
        self.commit("sanitize feature")
        self.git("switch", "-q", "main")
        self.git(
            "-c", "user.name=Validator Test",
            "-c", "user.email=validator@example.invalid",
            "merge", "-q", "--no-ff", "feature", "-m", "merge feature",
        )

        self.assertTrue(any("git history feature.txt" in error and "potential credential" in error for error in self.errors(release_history=True)))

    def test_secret_at_renamed_historical_path_is_blocked(self) -> None:
        old = self.root / "old-name.txt"
        old.write_text("AKIA" + ("A" * 16) + "\n", encoding="utf-8")
        self.commit("old name")
        self.git("mv", "old-name.txt", "new-name.txt")
        (self.root / "new-name.txt").write_text("Safe renamed file.\n", encoding="utf-8")
        self.commit("safe rename")

        self.assertTrue(any("git history old-name.txt" in error and "potential credential" in error for error in self.errors(release_history=True)))

    def test_non_utf8_and_binary_objects_are_lossily_scanned(self) -> None:
        binary = self.root / "fixture.bin"
        binary.write_bytes(b"\x00\xffpublic fixture\xfe")
        self.commit("clean binary")
        self.assertEqual([], self.errors(release_history=True))

        binary.write_bytes(b"\x00\xff" + b"xox" + b"b-" + (b"A" * 24) + b"\xfe")
        self.commit("binary value")
        self.assertTrue(any("potential credential" in error for error in self.errors(release_history=True)))

    def test_tree_object_scans_names_but_not_binary_object_ids(self) -> None:
        object_id = "a" * 40
        binary_child_id = b"i" + b"113" + (b"\xff" * 16)
        safe_tree = b"100644 safe.txt\0" + binary_child_id
        text, error = VALIDATOR._release_object_text(object_id, "tree", safe_tree)
        self.assertIsNone(error)
        self.assertEqual("safe.txt", text)
        self.assertEqual([], VALIDATOR._scan_public_text("git history tree fixture", text))

        private_tree = b"100644 Funding " + b"Radar.txt\0" + (b"\x00" * 20)
        text, error = VALIDATOR._release_object_text(object_id, "tree", private_tree)
        self.assertIsNone(error)
        self.assertTrue(any("private implementation" in item for item in VALIDATOR._scan_public_text("git history tree fixture", text)))

    def test_git_command_failure_fails_closed(self) -> None:
        self.track("LICENSE")
        with mock.patch.object(VALIDATOR.subprocess, "run", side_effect=OSError):
            errors = self.errors(release_history=True)

        self.assertTrue(any(error.startswith("git index:") for error in errors))
        self.assertTrue(any(error.startswith("git history:") for error in errors))

    def test_historical_private_policy_reference_survives_current_cleanup(self) -> None:
        boundary = self.root / "docs" / "provenance" / "public-private-boundary.md"
        boundary.write_text("Customer: Funding " + "Radar\n", encoding="utf-8")
        self.commit("disallowed historical policy")
        boundary.write_text(
            "- Private funding-source data, application material or vertical intelligence.\n",
            encoding="utf-8",
        )
        self.commit("sanitized current policy")

        errors = self.errors(release_history=True)
        self.assertTrue(any("git history docs/provenance/public-private-boundary.md" in error and "private implementation" in error for error in errors))

    def test_historical_private_policy_reference_at_other_path_fails(self) -> None:
        private_line = "- Funding " + "Radar data, application material or private vertical intelligence.\n"
        boundary = self.root / "docs" / "provenance" / "public-private-boundary.md"
        copied = self.root / "docs" / "copied-policy.md"
        boundary.write_text(
            "- Private funding-source data, application material or vertical intelligence.\n",
            encoding="utf-8",
        )
        copied.write_text(private_line, encoding="utf-8")
        self.commit("copied policy")
        copied.unlink()
        self.commit("remove copied policy")

        errors = self.errors(release_history=True)
        self.assertTrue(any("git history docs/copied-policy.md" in error and "private implementation" in error for error in errors))

    def test_historical_symlink_target_is_validated_without_following_it(self) -> None:
        link = self.root / "historical-link"
        link.symlink_to("/" + "Users/example/private")
        self.commit("historical link")
        link.unlink()
        self.commit("remove historical link")

        errors = self.errors(release_history=True)
        self.assertTrue(any("git history historical-link" in error and "private absolute path" in error for error in errors))
        self.assertTrue(any("git history historical-link" in error and "absolute or escapes" in error for error in errors))

    def test_current_public_repository_validates(self) -> None:
        self.assertEqual([], VALIDATOR.validate(MODULE_PATH.parents[1]))

    def test_broken_relative_link_fails(self) -> None:
        self.write_skill()
        (self.root / "README.md").write_text("[missing](docs/missing.md)\n", encoding="utf-8")
        self.assertTrue(any("broken relative link" in error for error in self.errors()))

    def test_relative_link_cannot_escape_repository(self) -> None:
        self.write_skill()
        (self.root / "README.md").write_text("[outside](../outside.md)\n", encoding="utf-8")
        self.assertTrue(any("relative link escapes repository" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
