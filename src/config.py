"""Configuration for SmartAudit Monitor."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MiMoConfig:
    """Xiaomi MiMo API configuration."""
    api_key: str = ""
    base_url: str = "https://api.xiaomimimo.com/v1"
    model: str = "mimo-v2.5-pro"
    temperature: float = 0.1
    max_tokens: int = 4096

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.environ.get("MIMO_API_KEY", "")


@dataclass
class BlockchainConfig:
    """Blockchain RPC configuration."""
    ethereum_rpc: str = "https://eth-mainnet.g.alchemy.com/v2/"
    bsc_rpc: str = "https://bsc-dataseed.binance.org/"
    polygon_rpc: str = "https://polygon-rpc.com/"
    chains: list = field(default_factory=lambda: ["ethereum"])
    poll_interval: int = 12  # seconds between block checks
    start_block: Optional[int] = None


@dataclass
class MonitorConfig:
    """Global monitor configuration."""
    mimo: MiMoConfig = field(default_factory=MiMoConfig)
    blockchain: BlockchainConfig = field(default_factory=BlockchainConfig)

    # Operational
    daily_token_budget: int = 1_000_000
    max_concurrent_audits: int = 3
    audit_cooldown: int = 30  # seconds between audits
    min_contract_size: int = 100  # min bytecode size to audit (skip trivial contracts)

    # Storage
    db_path: str = "logs/monitor.db"
    reports_dir: str = "reports"
    logs_dir: str = "logs"

    # Alerting
    alert_on_critical: bool = True
    webhook_url: str = ""  # Discord/Telegram webhook for alerts

    # Dashboard
    dashboard_port: int = 8080
    dashboard_enabled: bool = True
