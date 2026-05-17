"""
Token Usage Tracker — Tracks MiMo API token consumption.
Provides real-time stats for dashboard and daily reports.
"""

import json
import time
import sqlite3
import os
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Token usage record."""
    timestamp: float
    agent: str
    tokens: int
    model: str
    task_type: str  # "audit", "report", "summary"
    contract_address: str = ""
    chain: str = ""


class TokenTracker:
    """Tracks all MiMo API token usage with persistent storage."""

    def __init__(self, db_path: str = "logs/token_usage.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self.session_start = time.time()
        self.session_tokens = 0

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent TEXT,
                tokens INTEGER,
                model TEXT,
                task_type TEXT,
                contract_address TEXT,
                chain TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_tokens INTEGER,
                total_audits INTEGER,
                critical_findings INTEGER,
                high_findings INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def record(self, usage: TokenUsage):
        """Record a token usage event."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO token_usage (timestamp, agent, tokens, model, task_type, contract_address, chain) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (usage.timestamp, usage.agent, usage.tokens, usage.model, usage.task_type,
             usage.contract_address, usage.chain)
        )
        conn.commit()
        conn.close()
        self.session_tokens += usage.tokens

    def get_today_usage(self) -> dict:
        """Get today's total token usage."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT SUM(tokens), COUNT(*) FROM token_usage WHERE timestamp >= ?",
            (today_start,)
        )
        row = cursor.fetchone()
        conn.close()
        return {
            "total_tokens": row[0] or 0,
            "total_calls": row[1] or 0,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

    def get_session_usage(self) -> dict:
        """Get current session usage."""
        return {
            "session_tokens": self.session_tokens,
            "session_duration_min": (time.time() - self.session_start) / 60,
            "tokens_per_minute": self.session_tokens / max(1, (time.time() - self.session_start) / 60)
        }

    def get_usage_by_agent(self, hours: int = 24) -> list[dict]:
        """Get token usage broken down by agent."""
        since = time.time() - (hours * 3600)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT agent, SUM(tokens), COUNT(*) FROM token_usage WHERE timestamp >= ? GROUP BY agent ORDER BY SUM(tokens) DESC",
            (since,)
        )
        results = [{"agent": r[0], "tokens": r[1], "calls": r[2]} for r in cursor.fetchall()]
        conn.close()
        return results

    def get_usage_by_hour(self, hours: int = 24) -> list[dict]:
        """Hourly token usage for charting."""
        since = time.time() - (hours * 3600)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT strftime('%Y-%m-%d %H:00', timestamp, 'unixepoch') as hour, SUM(tokens) "
            "FROM token_usage WHERE timestamp >= ? GROUP BY hour ORDER BY hour",
            (since,)
        )
        results = [{"hour": r[0], "tokens": r[1]} for r in cursor.fetchall()]
        conn.close()
        return results

    def get_daily_history(self, days: int = 30) -> list[dict]:
        """Daily token usage history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT date, total_tokens, total_audits, critical_findings, high_findings "
            "FROM daily_summary ORDER BY date DESC LIMIT ?", (days,)
        )
        results = [dict(zip(["date", "tokens", "audits", "critical", "high"], r)) for r in cursor.fetchall()]
        conn.close()
        return results

    def save_daily_summary(self):
        """Save today's summary to daily_summary table."""
        usage = self.get_today_usage()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO daily_summary (date, total_tokens, total_audits, critical_findings, high_findings) VALUES (?, ?, ?, ?, ?)",
            (usage["date"], usage["total_tokens"], usage["total_calls"], 0, 0)
        )
        conn.commit()
        conn.close()

    def generate_report(self) -> str:
        """Generate a human-readable usage report."""
        today = self.get_today_usage()
        session = self.get_session_usage()
        by_agent = self.get_usage_by_agent(24)

        report = f"""
📊 SmartAudit Monitor — Token Usage Report
{'='*50}

📅 Today ({today['date']}):
   Total Tokens: {today['total_tokens']:,}
   Total API Calls: {today['total_calls']}

🔄 Current Session:
   Session Tokens: {session['session_tokens']:,}
   Duration: {session['session_duration_min']:.1f} min
   Rate: {session['tokens_per_minute']:.0f} tokens/min

🤖 Usage by Agent (24h):
"""
        for a in by_agent:
            report += f"   {a['agent']}: {a['tokens']:,} tokens ({a['calls']} calls)\n"

        return report
