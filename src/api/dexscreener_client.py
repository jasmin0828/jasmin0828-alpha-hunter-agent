"""DexScreener API client for multi-chain token discovery."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote_plus

import requests


class DexScreenerClient:
    """Small wrapper around the public DexScreener HTTP API."""

    BASE_URL = "https://api.dexscreener.com"
    REQUEST_TIMEOUT_SECONDS = 15
    TOKEN_BATCH_SIZE = 30
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 3

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get_top_boosted_token_addresses(self, chain: str) -> list[str]:
        """Return unique token addresses for one chain from DexScreener top boosts."""
        normalized_chain = self._normalize_chain(chain)
        payload = self._get_json("/token-boosts/top/v1")
        if not isinstance(payload, list):
            raise ValueError("Unexpected DexScreener top boosts response format")

        addresses: list[str] = []
        seen: set[str] = set()

        for token in payload:
            if not isinstance(token, dict):
                continue

            chain_id = str(token.get("chainId", "")).lower()
            token_address = token.get("tokenAddress")

            if chain_id != normalized_chain or not isinstance(token_address, str):
                continue

            if token_address not in seen:
                seen.add(token_address)
                addresses.append(token_address)

        self.logger.info("Fetched %s %s hot token candidates", len(addresses), normalized_chain)
        return addresses

    def get_token_pairs(self, chain: str, token_addresses: list[str]) -> list[dict[str, Any]]:
        """Fetch pair-level metrics for token addresses on one chain."""
        normalized_chain = self._normalize_chain(chain)
        pairs: list[dict[str, Any]] = []

        for batch in self._chunk_addresses(token_addresses):
            endpoint = f"/tokens/v1/{normalized_chain}/{','.join(batch)}"
            payload = self._get_json(endpoint)

            if not isinstance(payload, list):
                self.logger.warning("Skipping batch with unexpected response format: %s", batch)
                continue

            for pair in payload:
                if not isinstance(pair, dict):
                    continue
                pair["chainId"] = str(pair.get("chainId") or normalized_chain).lower()
                pairs.append(pair)

        self.logger.info("Fetched %s %s token pairs", len(pairs), normalized_chain)
        return pairs

    def search_token_pairs(self, chain: str, queries: list[str]) -> list[dict[str, Any]]:
        """Search DexScreener pairs for one chain as a public-data fallback."""
        normalized_chain = self._normalize_chain(chain)
        pairs: list[dict[str, Any]] = []
        seen_pairs: set[str] = set()

        for query in queries:
            payload = self._get_json(f"/latest/dex/search?q={quote_plus(query)}")
            if not isinstance(payload, dict):
                self.logger.warning("Skipping search query with unexpected response format: %s", query)
                continue

            for pair in payload.get("pairs") or []:
                if not isinstance(pair, dict):
                    continue
                if str(pair.get("chainId") or "").lower() != normalized_chain:
                    continue
                pair_key = str(pair.get("pairAddress") or pair.get("url") or "")
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                pair["chainId"] = normalized_chain
                pairs.append(pair)

        self.logger.info("Fetched %s %s token pairs from search fallback", len(pairs), normalized_chain)
        return pairs

    def get_top_boosted_solana_token_addresses(self) -> list[str]:
        """Return unique Solana token addresses from DexScreener top boosts."""
        return self.get_top_boosted_token_addresses("solana")

    def get_solana_token_pairs(self, token_addresses: list[str]) -> list[dict[str, Any]]:
        """Fetch pair-level metrics for Solana token addresses in API-sized batches."""
        return self.get_token_pairs("solana", token_addresses)

    def _get_json(self, endpoint: str) -> Any:
        """Call DexScreener with retry and return decoded JSON."""
        url = f"{self.BASE_URL}{endpoint}"
        retryable_errors = (
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=self.REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                return response.json()
            except ValueError as exc:
                self.logger.exception("DexScreener returned invalid JSON: %s", url)
                raise RuntimeError(f"DexScreener returned invalid JSON: {url}") from exc
            except retryable_errors as exc:
                if attempt >= self.MAX_RETRIES:
                    self.logger.warning(
                        "DexScreener request failed after %s attempts: %s (%s)",
                        self.MAX_RETRIES,
                        url,
                        exc,
                    )
                    raise RuntimeError(f"DexScreener request failed: {url}") from exc

                self.logger.warning(
                    "DexScreener request failed on attempt %s/%s: %s (%s). Retrying in %s seconds",
                    attempt,
                    self.MAX_RETRIES,
                    url,
                    exc,
                    self.RETRY_DELAY_SECONDS,
                )
                time.sleep(self.RETRY_DELAY_SECONDS)

        raise RuntimeError(f"DexScreener request failed: {url}")

    def _chunk_addresses(self, addresses: list[str]) -> list[list[str]]:
        """Split addresses into chunks accepted by DexScreener token lookup."""
        return [
            addresses[index : index + self.TOKEN_BATCH_SIZE]
            for index in range(0, len(addresses), self.TOKEN_BATCH_SIZE)
        ]

    def _normalize_chain(self, chain: str) -> str:
        """Return the DexScreener chain id used by API endpoints."""
        return str(chain or "").strip().lower()
