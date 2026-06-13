"""Trend Alpha engine for Alpha Hunter Market System."""

from __future__ import annotations

import pandas as pd


class TrendService:
    """Compute score, volume, liquidity, price, and momentum trend fields."""

    def calculate_trends(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        """Return snapshots with v0.7 trend metrics populated."""
        if snapshots.empty:
            return snapshots

        df = snapshots.copy()
        if "chain" not in df.columns:
            df["chain"] = "unknown"
        df["chain"] = df["chain"].fillna("unknown").astype(str).str.lower()
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        df = df.sort_values(["chain", "token_address", "created_at", "id"]).reset_index(drop=True)

        for column in [
            "score_change_10m",
            "score_change_30m",
            "volume_change_10m",
            "volume_spike_ratio",
            "liquidity_change_10m",
            "price_change_since_last_scan",
        ]:
            df[column] = 0.0
        df["volume_spike_ratio"] = 1.0
        df["momentum_status"] = "STABLE"

        result_groups = []
        for _, group in df.groupby(["chain", "token_address"], dropna=False):
            result_groups.append(self._calculate_group(group.copy()))

        result = pd.concat(result_groups, ignore_index=True)
        result["momentum_status"] = result.apply(self._momentum_status, axis=1)
        return result

    def _calculate_group(self, group: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend metrics within one token history."""
        group = group.sort_values(["created_at", "id"]).copy()
        created_at = pd.to_datetime(group["created_at"], errors="coerce", utc=True).reset_index(drop=True)
        ordered_indexes = list(group.index)

        for position, index in enumerate(ordered_indexes):
            if position == 0:
                continue

            row = group.loc[index]
            last = group.loc[ordered_indexes[position - 1]]
            current_time = created_at.iloc[position]
            if pd.isna(current_time):
                ref_10m = last
                ref_30m = last
            else:
                ref_10m = group.loc[self._window_ref_index(created_at, ordered_indexes, position, current_time, 10)]
                ref_30m = group.loc[self._window_ref_index(created_at, ordered_indexes, position, current_time, 30)]

            group.loc[index, "score_change_10m"] = self._number(row["alpha_score"]) - self._number(ref_10m["alpha_score"])
            group.loc[index, "score_change_30m"] = self._number(row["alpha_score"]) - self._number(ref_30m["alpha_score"])
            group.loc[index, "volume_change_10m"] = self._pct_change(row["volume_24h"], ref_10m["volume_24h"])
            group.loc[index, "liquidity_change_10m"] = self._pct_change(row["liquidity_usd"], ref_10m["liquidity_usd"])
            group.loc[index, "price_change_since_last_scan"] = self._pct_change(row["price_usd"], last["price_usd"])
            group.loc[index, "volume_spike_ratio"] = self._ratio(row["volume_24h"], ref_10m["volume_24h"])
        return group

    def _window_ref_index(
        self,
        created_at: pd.Series,
        ordered_indexes: list[int],
        position: int,
        current_time: pd.Timestamp,
        minutes: int,
    ) -> int:
        """Return the earliest prior row index inside a lookback window."""
        cutoff = current_time - pd.Timedelta(minutes=minutes)
        prior_times = created_at.iloc[:position]
        window_positions = prior_times[prior_times >= cutoff].index
        if len(window_positions) == 0:
            return ordered_indexes[position - 1]
        return ordered_indexes[int(window_positions[0])]

    def _momentum_status(self, row: pd.Series) -> str:
        """Classify momentum status by the v0.7 rules."""
        score_change_10m = self._number(row.get("score_change_10m"))
        volume_spike_ratio = self._number(row.get("volume_spike_ratio"))
        alpha_score = self._number(row.get("alpha_score"))
        risk_score = self._number(row.get("risk_score"))

        if score_change_10m >= 10 or volume_spike_ratio >= 1.5:
            return "HEATING_UP"
        if alpha_score >= 85 and risk_score <= 40:
            return "HOT"
        if score_change_10m <= -10:
            return "COOLING_DOWN"
        return "STABLE"

    def _pct_change(self, current: object, previous: object) -> float:
        """Return percent change with zero-safe fallback."""
        previous_number = self._number(previous)
        if previous_number == 0:
            return 0.0
        return round(((self._number(current) - previous_number) / previous_number) * 100, 2)

    def _ratio(self, current: object, previous: object) -> float:
        """Return current divided by previous with zero-safe fallback."""
        previous_number = self._number(previous)
        if previous_number == 0:
            return 1.0
        return round(self._number(current) / previous_number, 4)

    def _number(self, value: object) -> float:
        """Convert nullable dataframe values to float."""
        if pd.isna(value):
            return 0.0
        return float(value)
