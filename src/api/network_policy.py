"""Fail-closed network policy for isolated Alpha Hunter execution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from src.utils.paths import DATA_DIR, PROJECT_ROOT, WORKSPACE_ENV


POLICY_ENV = "ALPHA_HUNTER_NETWORK_POLICY"
CORRELATION_ENV = "ALPHA_HUNTER_RUN_CORRELATION_ID"
REQUEST_EVIDENCE_PATH = DATA_DIR / "network_requests.jsonl"
SUPPORTED_CHAINS = {"ethereum", "solana", "bsc"}
EVM_ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}")
SOLANA_ADDRESS = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
_EVIDENCE_WRITE_LOCK = threading.Lock()


class NetworkPolicyError(RuntimeError):
    """Raised before transmission when a request is outside the approved policy."""


@dataclass(frozen=True)
class NetworkDecision:
    method: str
    origin: str
    path: str
    query_parameters: tuple[str, ...]


class NetworkPolicy:
    """Validate exact origins, methods, paths, queries, and token batches."""

    def __init__(self, document: dict[str, Any], digest: str) -> None:
        self.document = document
        self.digest = digest
        self._validate_document()

    @classmethod
    def from_path(cls, path: Path) -> "NetworkPolicy":
        try:
            raw = Path(path).read_bytes()
            document = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise NetworkPolicyError("network policy is unreadable") from exc
        if not isinstance(document, dict):
            raise NetworkPolicyError("network policy must be an object")
        return cls(document, hashlib.sha256(raw).hexdigest())

    def _validate_document(self) -> None:
        if self.document.get("version") != "alpha_hunter_network_policy.v1":
            raise NetworkPolicyError("unsupported network policy version")
        if self.document.get("capability") != "alpha_hunter.daily_scan@1.0.0":
            raise NetworkPolicyError("network policy capability mismatch")
        if self.document.get("allowed_origins") != ["https://api.dexscreener.com"]:
            raise NetworkPolicyError("network policy origin must be the exact DexScreener origin")
        requests = self.document.get("allowed_requests")
        if not isinstance(requests, list) or not requests:
            raise NetworkPolicyError("network policy requires allowed requests")
        required_rules = {
            "/latest/dex/search": {
                "endpoint_id": "dexscreener.search_pairs", "method": "GET",
                "path_pattern": "/latest/dex/search", "allowed_query_parameters": ["q"],
                "required_query_parameters": ["q"],
            },
            "/token-boosts/top/v1": {
                "endpoint_id": "dexscreener.top_boosts", "method": "GET",
                "path_pattern": "/token-boosts/top/v1", "allowed_query_parameters": [],
            },
            "/tokens/v1/{chain}/{addresses}": {
                "endpoint_id": "dexscreener.token_batch", "method": "GET",
                "path_pattern": "/tokens/v1/{chain}/{addresses}", "allowed_query_parameters": [],
                "constraints": {"chains": ["ethereum", "solana", "bsc"], "maximum_addresses": 30},
            },
        }
        observed_patterns: set[str] = set()
        for rule in requests:
            if not isinstance(rule, dict) or rule.get("method") != "GET":
                raise NetworkPolicyError("network policy permits GET rules only")
            pattern = rule.get("path_pattern")
            if pattern not in required_rules or pattern in observed_patterns or rule != required_rules[pattern]:
                raise NetworkPolicyError("network policy contains an unknown or duplicate path")
            observed_patterns.add(pattern)
        if observed_patterns != set(required_rules):
            raise NetworkPolicyError("network policy endpoint inventory is incomplete")

    def authorize(self, method: str, url: str) -> NetworkDecision:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port is not None or parsed.fragment:
            raise NetworkPolicyError("request URL scheme, authority, port, or fragment is not approved")
        origin = f"{parsed.scheme}://{parsed.hostname or ''}"
        if origin not in self.document["allowed_origins"]:
            raise NetworkPolicyError("request origin is not approved")
        if method.upper() != "GET":
            raise NetworkPolicyError("request method is not approved")
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True) if parsed.query else {}
        rule = self._match_rule(parsed.path)
        allowed_query = set(rule.get("allowed_query_parameters", []))
        required_query = set(rule.get("required_query_parameters", []))
        if set(query) - allowed_query or not required_query.issubset(query):
            raise NetworkPolicyError("request query parameters are not approved")
        if any(len(values) != 1 or not values[0] for values in query.values()):
            raise NetworkPolicyError("request query parameter value is invalid")
        return NetworkDecision(method="GET", origin=origin, path=parsed.path, query_parameters=tuple(sorted(query)))

    def _match_rule(self, path: str) -> dict[str, Any]:
        for rule in self.document["allowed_requests"]:
            pattern = rule["path_pattern"]
            if path == pattern and "{" not in pattern:
                return rule
            if pattern == "/tokens/v1/{chain}/{addresses}" and path.startswith("/tokens/v1/"):
                parts = path.split("/")
                if len(parts) != 5:
                    break
                self._validate_batch(parts[3], parts[4], rule)
                return rule
        raise NetworkPolicyError("request path is not approved")

    @staticmethod
    def _validate_batch(chain: str, addresses: str, rule: dict[str, Any]) -> None:
        constraints = rule.get("constraints", {})
        allowed_chains = set(constraints.get("chains", []))
        if chain not in SUPPORTED_CHAINS or chain not in allowed_chains:
            raise NetworkPolicyError("token batch chain is not approved")
        values = addresses.split(",")
        maximum = constraints.get("maximum_addresses", 30)
        if not values or len(values) > maximum or len(values) != len(set(values)):
            raise NetworkPolicyError("token batch address list is invalid")
        validator = SOLANA_ADDRESS.fullmatch if chain == "solana" else EVM_ADDRESS.fullmatch
        if any(validator(value) is None for value in values):
            raise NetworkPolicyError("token batch address format is invalid")


def resolve_network_policy() -> NetworkPolicy | None:
    """Require explicit policy whenever isolated workspace mode is active."""
    configured_workspace = os.getenv(WORKSPACE_ENV)
    configured_policy = os.getenv(POLICY_ENV)
    isolated = bool(configured_workspace and Path(configured_workspace).expanduser().resolve() != PROJECT_ROOT)
    if isolated and not configured_policy:
        raise NetworkPolicyError("isolated execution requires ALPHA_HUNTER_NETWORK_POLICY")
    if not configured_policy:
        return None
    return NetworkPolicy.from_path(Path(configured_policy).expanduser().resolve())


def _utc_timestamp() -> str:
    """Return the evidence emission time as microsecond UTC RFC 3339."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def write_request_evidence(record: dict[str, Any]) -> None:
    """Append a secret-free process-correlated request decision record."""
    REQUEST_EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    safe = {
        "timestamp": _utc_timestamp(),
        "run_correlation_id": os.getenv(CORRELATION_ENV, "production-unattributed"),
        "method": record["method"],
        "origin": record["origin"],
        "path": record["path"],
        "query_parameter_names": record.get("query_parameters", []),
        "policy_decision": record["policy_decision"],
        "attempt": record["attempt"],
        "redirect_index": record.get("redirect_index", 0),
        "policy_digest": record.get("policy_digest"),
    }
    line = json.dumps(safe, sort_keys=True) + "\n"
    with _EVIDENCE_WRITE_LOCK:
        with REQUEST_EVIDENCE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
