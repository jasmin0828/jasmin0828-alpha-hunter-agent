"""First-stage Memory Agent for stable Daily Alpha Report assets."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryAgent:
    """Archive Daily Alpha Reports and maintain a lightweight report index."""

    REPORT_DATE_PATTERN = re.compile(r"Daily Alpha Report\s*-\s*(\d{4}-\d{2}-\d{2})")
    FILENAME_DATE_PATTERN = re.compile(r"daily_alpha_report_(\d{4}-\d{2}-\d{2})\.md$")
    BULLET_PATTERN = re.compile(r"^\s*-\s+(.*)$")

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2])
        self.memory_dir = self.project_root / "memory"
        self.reports_dir = self.memory_dir / "reports"
        self.index_path = self.memory_dir / "index.json"

    def archive_daily_report(self, report_path: Path | str) -> dict[str, Any]:
        """Copy a Daily Alpha Report into memory and upsert its index record."""
        source = Path(report_path)
        if not source.exists():
            raise FileNotFoundError(f"Daily report file not found: {source}")
        if not source.is_file():
            raise FileNotFoundError(f"Daily report path is not a file: {source}")

        content = source.read_text(encoding="utf-8")
        report_date = self._extract_report_date(content, source)
        destination = self.reports_dir / f"daily_alpha_report_{report_date}.md"

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        record = {
            "report_date": report_date,
            "file_path": str(destination),
            "top_theme": self._extract_top_theme(content),
            "top_tokens": self._extract_top_tokens(content),
            "risk_count": len(self._extract_section_bullets(content, "Risks")),
            "social_signal_count": self._extract_social_signal_count(content),
            "high_hype_count": self._extract_high_hype_count(content),
            "top_social_signal": self._extract_top_social_signal(content),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._upsert_record(record)
        return record

    def load_index(self) -> dict[str, list[dict[str, Any]]]:
        """Return the current Memory Agent index."""
        if not self.index_path.exists():
            return {"reports": []}

        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"reports": []}

        reports = data.get("reports", [])
        if not isinstance(reports, list):
            return {"reports": []}
        return {"reports": [row for row in reports if isinstance(row, dict)]}

    def list_recent_reports(self, limit: int = 3) -> list[dict[str, Any]]:
        """List the most recent archived reports from the index."""
        index = self.load_index()
        reports = sorted(index["reports"], key=lambda row: str(row.get("report_date", "")), reverse=True)
        return reports[: max(limit, 0)]

    def _upsert_record(self, record: dict[str, Any]) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        index = self.load_index()
        records = [row for row in index["reports"] if row.get("report_date") != record["report_date"]]
        records.append(record)
        records.sort(key=lambda row: str(row.get("report_date", "")), reverse=True)
        self.index_path.write_text(
            json.dumps({"reports": records}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _extract_report_date(self, content: str, source: Path) -> str:
        title_match = self.REPORT_DATE_PATTERN.search(content)
        if title_match:
            return title_match.group(1)

        filename_match = self.FILENAME_DATE_PATTERN.search(source.name)
        if filename_match:
            return filename_match.group(1)

        raise ValueError(f"Could not determine report date from: {source}")

    def _extract_top_theme(self, content: str) -> str:
        for bullet in self._extract_section_bullets(content, "Market Summary"):
            if bullet.startswith("top_theme:"):
                value = bullet.split(":", 1)[1].strip()
                return value or "none"

        themes = self._extract_section_bullets(content, "Top Themes")
        if not themes:
            return "none"
        return themes[0].split(" strength=", 1)[0].strip() or "none"

    def _extract_top_tokens(self, content: str) -> list[str]:
        tokens: list[str] = []
        for bullet in self._extract_section_bullets(content, "Top Tokens"):
            if bullet.startswith("No token rows"):
                continue
            symbol = bullet.split(" ", 1)[0].strip()
            if symbol and symbol not in tokens:
                tokens.append(symbol)
        return tokens[:5]

    def _extract_social_signal_count(self, content: str) -> int:
        social_bullets = self._extract_section_bullets(content, "Social Signals")
        return len([bullet for bullet in social_bullets if not bullet.startswith("No social signals")])

    def _extract_high_hype_count(self, content: str) -> int:
        high_hype_bullets = [
            bullet
            for bullet in self._extract_section_bullets(content, "Social Signals")
            if "hype=HIGH" in bullet
        ]
        return len(high_hype_bullets)

    def _extract_top_social_signal(self, content: str) -> str:
        for bullet in self._extract_section_bullets(content, "Social Evidence Summary"):
            if bullet.startswith("top_social_signal:"):
                value = bullet.split(":", 1)[1].strip()
                return value or "none"
        return "none"

    def _extract_section_bullets(self, content: str, section_name: str) -> list[str]:
        bullets: list[str] = []
        in_section = False
        target_heading = f"## {section_name}"

        for line in content.splitlines():
            if line.strip() == target_heading:
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if not in_section:
                continue

            match = self.BULLET_PATTERN.match(line)
            if match:
                bullets.append(match.group(1).strip())

        return bullets
