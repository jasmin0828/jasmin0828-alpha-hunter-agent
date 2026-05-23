"""DexScreener API client for Solana token discovery."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests


class DexScreenerClient:
    """Small wrapper around the public DexScreener HTTP API."""

    BASE_URL = "https://api.dexscreener.com"
    CHAIN_ID = "solana"
    REQUEST_TIMEOUT_SECONDS = 15
    TOKEN_BATCH_SIZE = 30
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 3

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get_top_boosted_solana_token_addresses(self) -> list[str]:
        """Return unique Solana token addresses from DexScreener top boosts."""
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

            if chain_id != self.CHAIN_ID or not isinstance(token_address, str):
                continue

            if token_address not in seen:
                seen.add(token_address)
                addresses.append(token_address)

        self.logger.info("Fetched %s Solana hot token candidates", len(addresses))
        return addresses

    def get_solana_token_pairs(self, token_addresses: list[str]) -> list[dict[str, Any]]:
        """Fetch pair-level metrics for Solana token addresses in API-sized batches."""
        pairs: list[dict[str, Any]] = []

        for batch in self._chunk_addresses(token_addresses):
            endpoint = f"/tokens/v1/{self.CHAIN_ID}/{','.join(batch)}"
            payload = self._get_json(endpoint)

            if not isinstance(payload, list):
                self.logger.warning("Skipping batch with unexpected response format: %s", batch)
                continue

            pairs.extend(pair for pair in payload if isinstance(pair, dict))

        self.logger.info("Fetched %s Solana token pairs", len(pairs))
        return pairs

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
