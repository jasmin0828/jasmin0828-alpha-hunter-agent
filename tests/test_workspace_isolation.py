from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MUTABLE_DIRS = ("data", "logs", "memory", "content", "labs", "reports")
APPLICATION_PYTHON = ROOT / "venv" / "bin" / "python"


def snapshot(paths: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class WorkspaceIsolationTests(unittest.TestCase):
    def run_python(self, code: str, *, workspace: Path | None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if workspace is None:
            environment.pop("ALPHA_HUNTER_WORKSPACE", None)
            environment.pop("ALPHA_HUNTER_NETWORK_POLICY", None)
        else:
            environment["ALPHA_HUNTER_WORKSPACE"] = str(workspace)
            environment["ALPHA_HUNTER_NETWORK_POLICY"] = str(ROOT / "config/daily_scan_network_policy.json")
        environment.update({
            "TELEGRAM_ENABLED": "false",
            "TELEGRAM_HEALTHCHECK_ENABLED": "false",
            "TELEGRAM_REPORTS_ENABLED": "false",
        })
        return subprocess.run(
            [str(APPLICATION_PYTHON if APPLICATION_PYTHON.exists() else Path(sys.executable)), "-c", code],
            cwd=ROOT, env=environment,
            check=True, capture_output=True, text=True,
        )

    def test_default_paths_remain_repository_paths(self):
        completed = self.run_python(
            "import json; from src.utils.paths import DATA_DIR, MEMORY_DIR, CONTENT_DIR; "
            "print(json.dumps([str(DATA_DIR), str(MEMORY_DIR), str(CONTENT_DIR)]))",
            workspace=None,
        )
        data_dir, memory_dir, content_dir = json.loads(completed.stdout)
        self.assertEqual(Path(data_dir), ROOT / "data")
        self.assertEqual(Path(memory_dir), ROOT / "memory")
        self.assertEqual(Path(content_dir), ROOT / "content")

    def test_real_run_agent_path_stays_inside_workspace_without_network_or_delivery(self):
        production_paths = [ROOT / name for name in MUTABLE_DIRS]
        before = snapshot(production_paths)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            completed = self.run_python(
                "from src.api.dexscreener_client import DexScreenerClient; "
                "DexScreenerClient._get_json=lambda self, endpoint: ({'pairs': []} if 'search' in endpoint else []); "
                "import json, main; print(json.dumps(main.run_agent()))",
                workspace=workspace,
            )
            result = json.loads(completed.stdout.splitlines()[-1])
            files = [path.resolve() for path in workspace.rglob("*") if path.is_file()]
            self.assertTrue(files)
            self.assertTrue(all(path.is_relative_to(workspace) for path in files))
            self.assertTrue((workspace / "data/alpha_hunter.db").is_file())
            self.assertTrue((workspace / "data/alpha_tokens.csv").is_file())
            self.assertTrue((workspace / "data/market_system_manifest.json").is_file())
            self.assertTrue((workspace / "data/aios_execution_summary.json").is_file())
            self.assertTrue((workspace / "memory/daily").is_dir())
            self.assertTrue((workspace / "memory/signals/signal-quality.md").is_file())
            self.assertTrue((workspace / "content/x").is_dir())
            self.assertTrue((workspace / "content/notes").is_dir())
            self.assertTrue(result["delivery_results"])
            self.assertTrue(all(not item["attempted"] for item in result["delivery_results"]))
        self.assertEqual(snapshot(production_paths), before)


if __name__ == "__main__":
    unittest.main()
