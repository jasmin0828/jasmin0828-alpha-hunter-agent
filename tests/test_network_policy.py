from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.api.dexscreener_client import DexScreenerClient
from src.api.network_policy import (
    CORRELATION_ENV,
    NetworkPolicy,
    NetworkPolicyError,
    resolve_network_policy,
    write_request_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/daily_scan_network_policy.json"


class FakeResponse:
    def __init__(self, payload=None, *, status=200, location=None):
        self.payload = {} if payload is None else payload
        self.status_code = status
        self.headers = {} if location is None else {"Location": location}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class NetworkPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = NetworkPolicy.from_path(POLICY_PATH)

    def test_daily_scan_endpoint_inventory_is_complete(self):
        document = json.loads(POLICY_PATH.read_text())
        observed = {rule["path_pattern"] for rule in document["allowed_requests"]}
        self.assertEqual(observed, {
            "/latest/dex/search", "/token-boosts/top/v1", "/tokens/v1/{chain}/{addresses}",
        })
        source = (ROOT / "src/api/dexscreener_client.py").read_text()
        for fragment in ('/latest/dex/search', '/token-boosts/top/v1', '/tokens/v1/{normalized_chain}'):
            self.assertIn(fragment, source)

    def test_exact_approved_requests_are_allowed(self):
        allowed = (
            "https://api.dexscreener.com/latest/dex/search?q=SOL",
            "https://api.dexscreener.com/token-boosts/top/v1",
            "https://api.dexscreener.com/tokens/v1/ethereum/0x1111111111111111111111111111111111111111",
            "https://api.dexscreener.com/tokens/v1/solana/11111111111111111111111111111111",
        )
        for url in allowed:
            with self.subTest(url=url):
                self.assertEqual(self.policy.authorize("GET", url).origin, "https://api.dexscreener.com")

    def test_unknown_origin_scheme_port_path_query_chain_and_addresses_are_denied(self):
        denied = (
            "https://example.com/latest/dex/search?q=SOL",
            "http://api.dexscreener.com/latest/dex/search?q=SOL",
            "https://api.dexscreener.com:443/latest/dex/search?q=SOL",
            "https://api.dexscreener.com/latest/dex/other?q=SOL",
            "https://api.dexscreener.com/latest/dex/search?q=SOL&secret=x",
            "https://api.dexscreener.com/tokens/v1/unknown/0x1111111111111111111111111111111111111111",
            "https://api.dexscreener.com/tokens/v1/ethereum/not-an-address",
        )
        for url in denied:
            with self.subTest(url=url), self.assertRaises(NetworkPolicyError):
                self.policy.authorize("GET", url)

    def client(self, responses):
        with patch.dict(os.environ, {"ALPHA_HUNTER_WORKSPACE": ""}, clear=False):
            client = DexScreenerClient()
        client.network_policy = self.policy
        client.session = FakeSession(responses)
        return client

    def test_redirects_are_manually_validated(self):
        client = self.client([
            FakeResponse(status=302, location="/token-boosts/top/v1"),
            FakeResponse([]),
        ])
        with patch("src.api.dexscreener_client.write_request_evidence") as evidence:
            self.assertEqual(client._get_json("/latest/dex/search?q=SOL"), [])
        self.assertEqual(len(client.session.calls), 2)
        self.assertTrue(all(call[1]["allow_redirects"] is False for call in client.session.calls))
        self.assertEqual(evidence.call_count, 2)

    def test_unapproved_redirect_path_and_origin_are_denied_before_follow(self):
        for target in ("/unapproved", "https://example.com/latest/dex/search?q=SOL"):
            with self.subTest(target=target):
                client = self.client([FakeResponse(status=302, location=target)])
                with patch("src.api.dexscreener_client.write_request_evidence"), self.assertRaises(NetworkPolicyError):
                    client._get_json("/latest/dex/search?q=SOL")
                self.assertEqual(len(client.session.calls), 1)

    def test_redirect_loop_is_bounded(self):
        client = self.client([
            FakeResponse(status=302, location="/token-boosts/top/v1"),
            FakeResponse(status=302, location="/latest/dex/search?q=SOL"),
        ])
        with patch("src.api.dexscreener_client.write_request_evidence"), self.assertRaises(NetworkPolicyError):
            client._get_json("/latest/dex/search?q=SOL")
        self.assertEqual(len(client.session.calls), 2)

    def test_retry_revalidates_allowed_request_and_denial_is_not_retried(self):
        client = self.client([requests.Timeout("controlled"), FakeResponse({"pairs": []})])
        with patch("src.api.dexscreener_client.write_request_evidence") as evidence, patch("time.sleep"):
            self.assertEqual(client._get_json("/latest/dex/search?q=SOL"), {"pairs": []})
        self.assertEqual(len(client.session.calls), 2)
        self.assertEqual(evidence.call_count, 2)

        denied = self.client([])
        with patch("src.api.dexscreener_client.write_request_evidence") as evidence, self.assertRaises(NetworkPolicyError):
            denied._get_json("/unapproved")
        self.assertEqual(denied.session.calls, [])
        self.assertEqual(evidence.call_args.args[0]["attempt"], 0)

    def test_request_evidence_is_process_correlated_and_secret_free(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "src.api.network_policy.REQUEST_EVIDENCE_PATH", Path(tmp) / "requests.jsonl"
        ), patch("src.api.network_policy._utc_timestamp", return_value="2026-07-20T01:23:45.123456Z"), patch.dict(
            os.environ, {CORRELATION_ENV: "run.test"}, clear=False
        ):
            write_request_evidence({
                "method": "GET", "origin": "https://api.dexscreener.com", "path": "/latest/dex/search",
                "query_parameters": ["q"], "policy_decision": "allowed", "attempt": 1,
                "policy_digest": self.policy.digest,
            })
            record = json.loads((Path(tmp) / "requests.jsonl").read_text())
        self.assertEqual(record["timestamp"], "2026-07-20T01:23:45.123456Z")
        self.assertEqual(record["run_correlation_id"], "run.test")
        self.assertEqual(record["query_parameter_names"], ["q"])
        self.assertNotIn("response", record)
        self.assertNotIn("SOL", json.dumps(record))

    def test_retry_redirect_and_denial_records_have_independent_utc_timestamps(self):
        timestamps = [
            "2026-07-20T01:23:45.100001Z", "2026-07-20T01:23:45.100002Z",
            "2026-07-20T01:23:45.100003Z", "2026-07-20T01:23:45.100004Z",
            "2026-07-20T01:23:45.100005Z",
        ]
        with tempfile.TemporaryDirectory() as tmp, patch(
            "src.api.network_policy.REQUEST_EVIDENCE_PATH", Path(tmp) / "requests.jsonl"
        ), patch("src.api.network_policy._utc_timestamp", side_effect=timestamps), patch.dict(
            os.environ, {CORRELATION_ENV: "run.timestamp-test"}, clear=False
        ), patch("time.sleep"):
            retry = self.client([requests.Timeout("controlled"), FakeResponse({"pairs": []})])
            self.assertEqual(retry._get_json("/latest/dex/search?q=SOL"), {"pairs": []})
            redirect = self.client([FakeResponse(status=302, location="/token-boosts/top/v1"), FakeResponse([])])
            self.assertEqual(redirect._get_json("/latest/dex/search?q=SOL"), [])
            denied = self.client([])
            with self.assertRaises(NetworkPolicyError):
                denied._get_json("/unapproved")
            lines = (Path(tmp) / "requests.jsonl").read_text().splitlines()
        records = [json.loads(line) for line in lines]
        self.assertEqual(len(records), 5)
        self.assertEqual([record["timestamp"] for record in records], timestamps)
        self.assertEqual([record["attempt"] for record in records[:2]], [1, 2])
        self.assertEqual([record["redirect_index"] for record in records[2:4]], [0, 1])
        self.assertEqual(records[-1]["policy_decision"], "denied")
        self.assertEqual(records[-1]["attempt"], 0)
        self.assertEqual(denied.session.calls, [])
        for record in records:
            self.assertEqual(record["run_correlation_id"], "run.timestamp-test")
            self.assertTrue(record["timestamp"].endswith("Z"))
            self.assertNotIn("headers", record)
            self.assertNotIn("response", record)
            self.assertNotIn("SOL", json.dumps(record))

    def test_production_compatibility_and_isolated_missing_policy_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(resolve_network_policy())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"ALPHA_HUNTER_WORKSPACE": tmp}, clear=True
        ), self.assertRaises(NetworkPolicyError):
            resolve_network_policy()


if __name__ == "__main__":
    unittest.main()
