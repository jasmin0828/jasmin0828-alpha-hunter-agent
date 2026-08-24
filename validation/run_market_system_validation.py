"""Run deterministic Alpha Hunter architecture contract scenarios."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from validation.market_system_validator import (
    ContractValidationError,
    ScanOutcome,
    validate_workspace,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/market_tokens.json"
NETWORK_POLICY_PATH = ROOT / "config/daily_scan_network_policy.json"


def load_fixture() -> pd.DataFrame:
    """Load the checked-in normalized market fixture."""
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return pd.DataFrame(rows)


def run_application_case(case: str, workspace: Path) -> None:
    """Run the real run_agent pipeline with deterministic input behavior."""
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        {
            "ALPHA_HUNTER_WORKSPACE": str(workspace),
            "ALPHA_HUNTER_NETWORK_POLICY": str(NETWORK_POLICY_PATH),
            "GITHUB_ACTIONS": "true",
            "TELEGRAM_ENABLED": "false",
            "TELEGRAM_HEALTHCHECK_ENABLED": "false",
            "TELEGRAM_REPORTS_ENABLED": "false",
        }
    )

    fixture = load_fixture()
    if case == "fallback":
        data_dir = workspace / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        fixture.to_csv(data_dir / "alpha_tokens.csv", index=False)

    import main

    if case == "normal":
        behavior = {"return_value": fixture}
    elif case == "empty":
        behavior = {"return_value": pd.DataFrame()}
    elif case in {"fallback", "degraded"}:
        behavior = {"side_effect": RuntimeError("simulated DexScreener unavailable")}
    else:
        raise ValueError(f"Unknown application case: {case}")

    with patch.object(main.AlphaTokenService, "find_and_save_top_tokens", **behavior):
        main.main()
    print(f"APPLICATION_CASE={case} STATUS=completed_or_recorded")


def run_child(case: str, workspace: Path) -> None:
    """Run one case in a fresh interpreter so workspace paths are isolated."""
    environment = os.environ.copy()
    environment.update(
        {
            "ALPHA_HUNTER_WORKSPACE": str(workspace),
            "ALPHA_HUNTER_NETWORK_POLICY": str(NETWORK_POLICY_PATH),
            "GITHUB_ACTIONS": "true",
            "TELEGRAM_ENABLED": "false",
            "TELEGRAM_HEALTHCHECK_ENABLED": "false",
            "TELEGRAM_REPORTS_ENABLED": "false",
        }
    )
    command = [
        sys.executable,
        "-m",
        "validation.run_market_system_validation",
        "--case",
        case,
        "--workspace",
        str(workspace),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Application case failed: {case}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def run_expected_failure(workspace: Path, mutation: str) -> None:
    """Apply a temporary regression to artifacts and require validator failure."""
    if mutation == "missing-artifact":
        (workspace / "data/market_system_manifest.json").unlink()
    elif mutation == "contract-regression":
        path = workspace / "data/market_system_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["safety_boundary"]["automated_trading"] = True
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    else:
        raise ValueError(f"Unknown mutation: {mutation}")

    try:
        validate_workspace(workspace)
    except ContractValidationError as exc:
        print(f"EXPECTED_FAILURE={mutation} RESULT=FAIL_CLOSED REASON={exc}")
        return
    raise AssertionError(f"Validator accepted regression: {mutation}")


def run_scenario(label: str, case: str, expected: ScanOutcome) -> None:
    with tempfile.TemporaryDirectory(prefix=f"alpha-hunter-{case}-") as temporary:
        workspace = Path(temporary)
        run_child(case, workspace)
        outcome = validate_workspace(workspace)
        if outcome is not expected:
            raise AssertionError(f"{label}: expected {expected.value}, got {outcome.value}")
        print(f"{label}: PASS outcome={outcome.value}")


def run_matrix() -> None:
    """Run the required positive and fail-closed validation scenarios."""
    run_scenario("Normal Data", "normal", ScanOutcome.SUCCESS_WITH_DATA)
    run_scenario("Empty Data", "empty", ScanOutcome.SUCCESS_EMPTY)
    run_scenario("External API Failure + Fallback", "fallback", ScanOutcome.SUCCESS_FALLBACK)
    run_scenario("External API Failure without Fallback", "degraded", ScanOutcome.EXTERNAL_DEGRADED)

    with tempfile.TemporaryDirectory(prefix="alpha-hunter-regression-") as temporary:
        workspace = Path(temporary)
        run_child("normal", workspace)
        if validate_workspace(workspace) is not ScanOutcome.SUCCESS_WITH_DATA:
            raise AssertionError("Regression fixtures did not start from a valid baseline")
        baseline = workspace / "data/market_system_manifest.json"
        baseline_copy = workspace / "data/market_system_manifest.baseline.json"
        shutil.copy2(baseline, baseline_copy)
        run_expected_failure(workspace, "missing-artifact")
        shutil.copy2(baseline_copy, baseline)
        run_expected_failure(workspace, "contract-regression")
    print("Validation matrix: PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["normal", "empty", "fallback", "degraded"])
    parser.add_argument("--workspace", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    if arguments.case:
        if arguments.workspace is None:
            raise SystemExit("--workspace is required with --case")
        run_application_case(arguments.case, arguments.workspace)
        return
    run_matrix()


if __name__ == "__main__":
    main()
