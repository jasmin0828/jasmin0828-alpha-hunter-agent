"""Token filtering and CSV persistence for Alpha Hunter Market System."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from config import CHAIN_FILTERS, CHAIN_SEARCH_QUERIES, SUPPORTED_CHAINS
from src.ai.alpha_analyzer import AlphaAnalyzer
from src.api.dexscreener_client import DexScreenerClient
from src.utils.paths import DATA_DIR, ensure_project_directories


class AlphaTokenService:
    """Find, filter, rank, and save market intelligence token candidates."""

    CSV_PATH = DATA_DIR / "alpha_tokens.csv"
    TOP_N = 10
    PER_CHAIN_TOP_N = 5
    OUTPUT_DEFAULTS = {
        "score_change_10m": 0,
        "score_change_30m": 0,
        "volume_change_10m": 0,
        "volume_spike_ratio": 1,
        "liquidity_change_10m": 0,
        "price_change_since_last_scan": 0,
        "momentum_status": "STABLE",
        "narrative": "Unknown",
        "narrative_score": 0,
        "smart_money_score": 0,
        "smart_money_signal": "NEUTRAL",
        "token_age_minutes": 0,
        "token_age_hours": 0,
        "token_age_bucket": "UNKNOWN",
        "rug_risk_level": "LOW",
        "rug_risk_score": 0,
        "volume_liquidity_ratio": 0,
        "fdv_liquidity_ratio": 0,
        "extreme_pump_flag": False,
        "low_liquidity_flag": False,
        "suspicious_volume_flag": False,
        "risk_notes": "",
        "alert_level": "IGNORE",
        "alert_reason": "",
        "agent_score": 0,
        "first_seen_at": "",
        "is_first_seen": False,
        "scan_count": 0,
        "consecutive_up_count": 0,
        "early_alpha_score": 0,
        "early_alpha_reason": "",
    }

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
        self.diagnostics: list[dict[str, Any]] = []

    def find_and_save_top_tokens(self) -> pd.DataFrame:
        """Run the full multi-chain discovery pipeline and save the candidate CSV."""
        ensure_project_directories()
        self.diagnostics = []

        all_pairs: list[dict[str, Any]] = []
        for chain in SUPPORTED_CHAINS:
            addresses = self.client.get_top_boosted_token_addresses(chain)
            if not addresses:
                self.logger.warning("DexScreener returned no %s hot token candidates", chain)
                self.diagnostics.append({
                    "code": "DEXSCREENER_NO_HOT_CANDIDATES",
                    "message": f"DexScreener returned no {chain} hot token candidates",
                    "source": "alpha_token_service",
                    "fatal": False,
                })
            else:
                all_pairs.extend(self.client.get_token_pairs(chain, addresses))

            fallback_pairs = self.client.search_token_pairs(chain, CHAIN_SEARCH_QUERIES.get(chain, [chain]))
            if fallback_pairs:
                all_pairs.extend(fallback_pairs)

        if not all_pairs:
            self.logger.warning("DexScreener returned no multi-chain hot token candidates")
            self.diagnostics.append({
                "code": "DEXSCREENER_MULTI_CHAIN_FALLBACK_EMPTY",
                "message": "DexScreener returned no multi-chain hot token candidates",
                "source": "alpha_token_service",
                "fatal": False,
            })
            return self._save_empty_csv()

        tokens = self._pairs_to_dataframe(all_pairs)

        if tokens.empty:
            self.logger.warning("No pair metrics were available for candidate tokens")
            return self._save_empty_csv()

        filtered_tokens = self._filter_tokens(tokens)
        analyzed_tokens = self.analyzer.analyze_tokens(filtered_tokens)
        top_tokens = self._rank_tokens(analyzed_tokens)
        self._with_output_defaults(top_tokens).to_csv(self.csv_path, index=False)

        self.logger.info("Saved %s multi-chain filtered tokens to %s", len(top_tokens), self.csv_path)
        return top_tokens

    def normalize_pair(self, pair: dict[str, Any]) -> dict[str, Any]:
        """Normalize a DexScreener pair into the Alpha Hunter multi-chain schema."""
        base_token = pair.get("baseToken") or {}
        quote_token = pair.get("quoteToken") or {}
        liquidity = pair.get("liquidity") or {}
        volume = pair.get("volume") or {}
        price_change = pair.get("priceChange") or {}

        chain = str(pair.get("chainId") or "").lower()
        token_symbol = base_token.get("symbol")
        contract_address = base_token.get("address")
        pair_url = pair.get("url")

        return {
            "chain": chain,
            "token_name": base_token.get("name"),
            "token_symbol": token_symbol,
            "contract_address": contract_address,
            "price_usd": pair.get("priceUsd"),
            "liquidity_usd": liquidity.get("usd"),
            "volume_24h": volume.get("h24"),
            "price_change_24h": price_change.get("h24"),
            "fdv": pair.get("fdv"),
            "pair_created_at": pair.get("pairCreatedAt"),
            "dex": pair.get("dexId"),
            "pair_url": pair_url,
            "pair_address": pair.get("pairAddress"),
            "quote_symbol": quote_token.get("symbol"),
            "market_cap": pair.get("marketCap"),
            # Compatibility fields used by existing services and dashboard panels.
            "symbol": token_symbol,
            "token_address": contract_address,
            "url": pair_url,
        }

    def _pairs_to_dataframe(self, pairs: list[dict[str, Any]]) -> pd.DataFrame:
        """Normalize nested DexScreener pair objects into a flat DataFrame."""
        rows = [self.normalize_pair(pair) for pair in pairs]
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
        """Apply chain-specific liquidity, volume, momentum, and FDV filters."""
        required_columns = ["chain", "liquidity_usd", "volume_24h", "price_change_24h", "fdv"]
        cleaned = dataframe.dropna(subset=required_columns).copy()
        cleaned["chain"] = cleaned["chain"].astype(str).str.lower()

        filtered_frames: list[pd.DataFrame] = []
        for chain, chain_frame in cleaned.groupby("chain", dropna=False):
            filters = CHAIN_FILTERS.get(str(chain), CHAIN_FILTERS["ethereum"])
            filtered_frames.append(
                chain_frame[
                    (chain_frame["liquidity_usd"] > filters["liquidity_usd"])
                    & (chain_frame["volume_24h"] > filters["volume_24h"])
                    & (chain_frame["price_change_24h"] >= filters["min_price_change_24h"])
                    & (chain_frame["price_change_24h"] <= filters["max_price_change_24h"])
                    & (chain_frame["fdv"] < filters["fdv"])
                ]
            )

        filtered = pd.concat(filtered_frames, ignore_index=True) if filtered_frames else cleaned.head(0)

        self.logger.info("Filtered %s pairs down to %s alpha candidates", len(dataframe), len(filtered))
        return filtered

    def _rank_tokens(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Rank all-chain Top 10 plus per-chain Top 5 rows."""
        columns = [
            "chain",
            "symbol",
            "token_symbol",
            "token_name",
            "token_address",
            "contract_address",
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
            "pair_url",
        ]

        if dataframe.empty:
            return self._with_output_defaults(pd.DataFrame(columns=columns))

        ranked = dataframe.sort_values(
            by=["volume_24h", "liquidity_usd"],
            ascending=[False, False],
        ).drop_duplicates(subset=["chain", "contract_address"], keep="first")

        all_chain_top = ranked.head(self.TOP_N)
        per_chain_top = ranked.groupby("chain", dropna=False).head(self.PER_CHAIN_TOP_N)
        combined = (
            pd.concat([all_chain_top, per_chain_top], ignore_index=True)
            .drop_duplicates(subset=["chain", "contract_address"], keep="first")
            .sort_values(["volume_24h", "liquidity_usd"], ascending=[False, False])
            .reset_index(drop=True)
        )
        return combined[columns]

    def _with_output_defaults(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Ensure raw CSV output keeps v0.7-v1.0 columns during scans."""
        output = dataframe.copy()
        for column, default in self.OUTPUT_DEFAULTS.items():
            if column not in output.columns:
                output[column] = default
        return output

    def _save_empty_csv(self) -> pd.DataFrame:
        """Save an empty CSV with stable headers when no tokens match."""
        columns = [
            "chain",
            "symbol",
            "token_symbol",
            "token_name",
            "token_address",
            "contract_address",
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
            "pair_url",
        ]
        dataframe = self._with_output_defaults(pd.DataFrame(columns=columns))
        dataframe.to_csv(self.csv_path, index=False)
        return dataframe
