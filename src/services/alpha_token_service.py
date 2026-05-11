"""Token filtering and CSV persistence for Alpha Hunter Agent."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.ai.alpha_analyzer import AlphaAnalyzer
from src.api.dexscreener_client import DexScreenerClient
from src.utils.paths import DATA_DIR, ensure_project_directories


class AlphaTokenService:
    """Find, filter, rank, and save Alpha Hunter token candidates."""

    CSV_PATH = DATA_DIR / "alpha_tokens.csv"
    TOP_N = 10

    MIN_LIQUIDITY_USD = 50_000
    MIN_VOLUME_24H = 100_000
    MIN_PRICE_CHANGE_24H = -30
    MAX_PRICE_CHANGE_24H = 200
    MAX_FDV = 50_000_000

    def __init__(
        self,
        client: DexScreenerClient | None = None,
        analyzer: AlphaAnalyzer | None = None,
        csv_path: Path | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.client = client or DexScreenerClient()
        self.analyzer = analyzer or AlphaAnalyzer()
        self.csv_path = csv_path or self.CSV_PATH

    def find_and_save_top_tokens(self) -> pd.DataFrame:
        """Run the full discovery pipeline and save the resulting Top 10 CSV."""
        ensure_project_directories()

        addresses = self.client.get_top_boosted_solana_token_addresses()
        if not addresses:
            self.logger.warning("DexScreener returned no Solana hot token candidates")
            return self._save_empty_csv()

        pairs = self.client.get_solana_token_pairs(addresses)
        tokens = self._pairs_to_dataframe(pairs)

        if tokens.empty:
            self.logger.warning("No pair metrics were available for candidate tokens")
            return self._save_empty_csv()

        filtered_tokens = self._filter_tokens(tokens)
        analyzed_tokens = self.analyzer.analyze_tokens(filtered_tokens)
        top_tokens = self._rank_tokens(analyzed_tokens)
        top_tokens.to_csv(self.csv_path, index=False)

        self.logger.info("Saved %s filtered tokens to %s", len(top_tokens), self.csv_path)
        return top_tokens

    def _pairs_to_dataframe(self, pairs: list[dict[str, Any]]) -> pd.DataFrame:
        """Normalize nested DexScreener pair objects into a flat DataFrame."""
        rows: list[dict[str, Any]] = []

        for pair in pairs:
            base_token = pair.get("baseToken") or {}
            quote_token = pair.get("quoteToken") or {}
            liquidity = pair.get("liquidity") or {}
            volume = pair.get("volume") or {}
            price_change = pair.get("priceChange") or {}

            rows.append(
                {
                    "chain": pair.get("chainId"),
                    "dex": pair.get("dexId"),
                    "pair_address": pair.get("pairAddress"),
                    "token_address": base_token.get("address"),
                    "token_name": base_token.get("name"),
                    "symbol": base_token.get("symbol"),
                    "quote_symbol": quote_token.get("symbol"),
                    "price_usd": pair.get("priceUsd"),
                    "liquidity_usd": liquidity.get("usd"),
                    "volume_24h": volume.get("h24"),
                    "price_change_24h": price_change.get("h24"),
                    "fdv": pair.get("fdv"),
                    "market_cap": pair.get("marketCap"),
                    "pair_created_at": pair.get("pairCreatedAt"),
                    "url": pair.get("url"),
                }
            )

        dataframe = pd.DataFrame(rows)
        return self._coerce_numeric_columns(dataframe)

    def _coerce_numeric_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric metric columns and tolerate missing or malformed values."""
        numeric_columns = [
            "price_usd",
            "liquidity_usd",
            "volume_24h",
            "price_change_24h",
            "fdv",
            "market_cap",
            "pair_created_at",
        ]

        for column in numeric_columns:
            if column in dataframe.columns:
                dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        return dataframe

    def _filter_tokens(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Apply Alpha Hunter v0.1 liquidity, volume, momentum, and FDV filters."""
        required_columns = ["liquidity_usd", "volume_24h", "price_change_24h", "fdv"]
        cleaned = dataframe.dropna(subset=required_columns).copy()

        filtered = cleaned[
            (cleaned["liquidity_usd"] > self.MIN_LIQUIDITY_USD)
            & (cleaned["volume_24h"] > self.MIN_VOLUME_24H)
            & (cleaned["price_change_24h"] >= self.MIN_PRICE_CHANGE_24H)
            & (cleaned["price_change_24h"] <= self.MAX_PRICE_CHANGE_24H)
            & (cleaned["fdv"] < self.MAX_FDV)
        ]

        self.logger.info("Filtered %s pairs down to %s alpha candidates", len(dataframe), len(filtered))
        return filtered

    def _rank_tokens(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Rank candidates by 24h volume and keep the Top 10 rows."""
        columns = [
            "symbol",
            "token_name",
            "token_address",
            "price_usd",
            "liquidity_usd",
            "volume_24h",
            "price_change_24h",
            "fdv",
            "market_cap",
            "pair_created_at",
            "alpha_score",
            "risk_score",
            "ai_summary",
            "dex",
            "url",
        ]

        if dataframe.empty:
            return pd.DataFrame(columns=columns)

        return (
            dataframe.sort_values(
                by=["volume_24h", "liquidity_usd"],
                ascending=[False, False],
            )
            .drop_duplicates(subset=["token_address"], keep="first")
            .head(self.TOP_N)[columns]
            .reset_index(drop=True)
        )

    def _save_empty_csv(self) -> pd.DataFrame:
        """Save an empty CSV with stable headers when no tokens match."""
        columns = [
            "symbol",
            "token_name",
            "token_address",
            "price_usd",
            "liquidity_usd",
            "volume_24h",
            "price_change_24h",
            "fdv",
            "market_cap",
            "pair_created_at",
            "alpha_score",
            "risk_score",
            "ai_summary",
            "dex",
            "url",
        ]
        dataframe = pd.DataFrame(columns=columns)
        dataframe.to_csv(self.csv_path, index=False)
        return dataframe
