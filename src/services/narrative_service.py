"""Narrative Detection engine for Alpha Hunter Market System."""

from __future__ import annotations

import pandas as pd


class NarrativeService:
    """Classify token narratives from token_name and symbol text."""

    RULES: list[tuple[str, tuple[str, ...], int]] = [
        ("AI", ("AI", "GPT", "AGENT", "BOT"), 92),
        ("Political", ("TRUMP", "USA", "MAGA", "AMERICA", "PRESIDENT"), 88),
        ("Sports", ("WORLD", "CUP", "FIFA", "FOOTBALL", "SOCCER"), 84),
        ("Celebrity", ("ELON", "MUSK", "KANYE", "TAYLOR", "DRAKE"), 80),
        ("Gaming", ("GAME", "GAMING", "PLAY", "QUEST", "ARENA"), 78),
        ("DeFi", ("DEFI", "SWAP", "YIELD", "STAKE", "LEND"), 76),
        ("Solana Ecosystem", ("SOL", "JUP", "RAY", "BONK"), 82),
        ("Meme", ("PEPE", "DOGE", "BONK", "TROLL", "LOL", "COPE", "COPIUM"), 75),
    ]

    def classify_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Add narrative and narrative_score columns."""
        if tokens.empty:
            result = tokens.copy()
            result["narrative"] = pd.Series(dtype="object")
            result["narrative_score"] = pd.Series(dtype="float64")
            return result

        result = tokens.copy()
        classified = result.apply(self._classify_row, axis=1, result_type="expand")
        result["narrative"] = classified["narrative"]
        result["narrative_score"] = classified["narrative_score"]
        return result

    def _classify_row(self, row: pd.Series) -> dict[str, object]:
        """Classify one token by matching uppercase symbol/name text."""
        text = f"{row.get('symbol', '')} {row.get('token_name', '')}".upper()
        for narrative, keywords, score in self.RULES:
            if any(keyword in text for keyword in keywords):
                return {"narrative": narrative, "narrative_score": float(score)}
        return {"narrative": "Unknown", "narrative_score": 20.0}
