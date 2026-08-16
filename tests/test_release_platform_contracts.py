from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePlatformContracts(unittest.TestCase):
    def test_ci_runs_the_contract_suite_on_linux_and_macos(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("macos-latest", workflow)
        self.assertIn("matrix.os", workflow)
        self.assertIn("python3 -m unittest discover", workflow)

    def test_public_runtime_has_no_network_client_imports(self) -> None:
        forbidden = {"http", "requests", "socket", "urllib", "websocket"}
        findings: list[str] = []
        for path in sorted((ROOT / "src" / "the_loop").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".", 1)[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".", 1)[0]]
                else:
                    continue
                for name in names:
                    if name in forbidden:
                        findings.append(f"{path.relative_to(ROOT)} imports {name}")
        self.assertEqual([], findings, "default runtime must not include a network or telemetry client")


if __name__ == "__main__":
    unittest.main()
