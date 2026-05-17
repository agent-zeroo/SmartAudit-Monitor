#!/usr/bin/env python3
"""
SmartAudit Monitor v2.0 — CLI Entry Point

Usage:
    python -m src.main monitor          # Start 24/7 monitoring (default)
    python -m src.main monitor --chain ethereum --chain bsc
    python -m src.main scan             # One-shot scan of recent blocks
    python -m src.main audit <file>     # Audit a single Solidity file
    python -m src.main report           # Generate daily usage report
    python -m src.main stats            # Show monitoring statistics
    python -m src.main demo             # Demo run (audit example contracts)
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime

from src.config import MonitorConfig
from src.orchestrator import MonitorOrchestrator
from src.agents.pipeline import AuditPipeline
from src.utils.token_tracker import TokenTracker, TokenUsage
from src.utils.daily_report import generate_daily_report


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🔒 SmartAudit Monitor v2.0                         ║
║     24/7 Autonomous Smart Contract Security Agent            ║
║          Powered by Xiaomi MiMo V2.5                        ║
║                                                              ║
║  📡 Blockchain → 🔍 Multi-Agent Audit → 📊 Reports          ║
╚══════════════════════════════════════════════════════════════╝
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="SmartAudit Monitor — 24/7 Autonomous Smart Contract Security Agent"
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # monitor
    mon = sub.add_parser("monitor", help="Start 24/7 autonomous monitoring")
    mon.add_argument("--chain", action="append", default=["ethereum"],
                     help="Chains to monitor (ethereum, bsc, polygon)")
    mon.add_argument("--interval", type=int, default=12, help="Poll interval (seconds)")
    mon.add_argument("--budget", type=int, default=1_000_000, help="Daily token budget")

    # scan
    scan = sub.add_parser("scan", help="One-shot scan of recent blocks")
    scan.add_argument("--chain", default="ethereum")
    scan.add_argument("--blocks", type=int, default=20, help="Number of blocks to scan")

    # audit
    audit = sub.add_parser("audit", help="Audit a single Solidity file")
    audit.add_argument("file", help="Path to .sol file")
    audit.add_argument("--chain", default="ethereum")
    audit.add_argument("--name", default="Unknown", help="Contract name")

    # report
    sub.add_parser("report", help="Generate daily usage report")

    # stats
    sub.add_parser("stats", help="Show monitoring statistics")

    # demo
    demo = sub.add_parser("demo", help="Demo run — audit example contracts")
    demo.add_argument("--no-api", action="store_true", help="Skip API calls (pattern-only)")

    return parser.parse_args()


async def cmd_monitor(args):
    """Start 24/7 monitoring."""
    config = MonitorConfig()
    config.blockchain.chains = args.chain
    config.blockchain.poll_interval = args.interval
    config.daily_token_budget = args.budget

    orchestrator = MonitorOrchestrator(config)
    await orchestrator.start()


async def cmd_scan(args):
    """One-shot scan."""
    config = MonitorConfig()
    monitor = __import__('src.monitor.blockchain', fromlist=['BlockchainMonitor']).BlockchainMonitor(config)

    print(f"\n📡 Scanning last {args.blocks} blocks on {args.chain}...\n")
    deployments = monitor.scan_new_contracts(args.chain, max_blocks=args.blocks)

    if not deployments:
        print("No new contract deployments found.")
        return

    print(f"\n📦 Found {len(deployments)} new contracts:\n")
    for d in deployments:
        status = "✅ Verified" if d.source_verified else "⬜ Unverified"
        print(f"  {status} {d.contract_name or 'Unknown':20s} | {d.address[:12]}... | {d.bytecode_size:,} bytes")


async def cmd_audit(args):
    """Audit a single file."""
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    with open(args.file) as f:
        source = f.read()

    config = MonitorConfig()
    tracker = TokenTracker()
    pipeline = AuditPipeline(config, tracker)

    print(f"\n🔍 Auditing: {args.file}")
    print(f"📄 Contract: {args.name}\n")

    result = await pipeline.audit_contract(
        source_code=source,
        address="local_file",
        chain=args.chain,
        contract_name=args.name,
    )

    # Print findings
    print(f"\n{'='*60}")
    print(f"📊 Audit Complete!")
    print(f"{'='*60}")
    print(f"Findings: {len(result.findings)}")
    print(f"Tokens: {result.total_tokens:,}")
    print(f"Duration: {result.duration_ms/1000:.1f}s\n")

    for f in sorted(result.findings, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(x.severity, 5)):
        emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "ℹ️"}.get(f.severity, "")
        print(f"  {emoji} [{f.severity}] {f.title}")

    # Save report
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/audit_{os.path.basename(args.file).replace('.sol', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, "w") as rf:
        rf.write(result.report_markdown)
    print(f"\n💾 Report: {report_path}")


async def cmd_report(args):
    """Generate daily report."""
    report = generate_daily_report()
    print(report)


async def cmd_stats(args):
    """Show stats."""
    config = MonitorConfig()
    monitor = __import__('src.monitor.blockchain', fromlist=['BlockchainMonitor']).BlockchainMonitor(config)
    tracker = TokenTracker(config.db_path.replace(".db", "_tokens.db"))

    stats = monitor.get_stats()
    usage = tracker.get_today_usage()
    session = tracker.get_session_usage()
    by_agent = tracker.get_usage_by_agent(24)

    print(f"""
📊 SmartAudit Monitor — Statistics
{'='*50}

📡 Blockchain:
   Total contracts tracked:  {stats['total_contracts']:,}
   Verified source:          {stats['verified_source']:,}
   Audited:                  {stats['audited']:,}
   Today's deployments:      {stats['today_deployments']:,}

🪙 Token Usage (Today):
   Total tokens:  {usage['total_tokens']:,}
   API calls:     {usage['total_calls']:,}

🤖 By Agent (24h):
""")
    for a in by_agent:
        print(f"   {a['agent']:25s} {a['tokens']:>10,} tokens ({a['calls']} calls)")


async def cmd_demo(args):
    """Demo run — audit example contracts."""
    print(BANNER)
    print("🎬 Running demo audit...\n")

    # Find example contracts
    example_dir = os.path.join(os.path.dirname(__file__), "..", "contracts", "examples")
    if not os.path.isdir(example_dir):
        example_dir = os.path.join("contracts", "examples")

    if not os.path.isdir(example_dir):
        print("⚠️  No example contracts found. Creating demo contracts...")
        os.makedirs("contracts/examples", exist_ok=True)
        # Create a simple vulnerable contract for demo
        _create_demo_contracts()
        example_dir = "contracts/examples"

    for filename in sorted(os.listdir(example_dir)):
        if filename.endswith(".sol"):
            filepath = os.path.join(example_dir, filename)
            print(f"\n{'='*60}")
            print(f"📄 Auditing: {filename}")
            print(f"{'='*60}")

            if args.no_api:
                # Pattern-only scan
                with open(filepath) as f:
                    source = f.read()
                from src.utils.vuln_patterns import scan_patterns
                findings = scan_patterns(source)
                print(f"\n🔍 Pattern scan: {len(findings)} issues found")
                for f in findings:
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(f["severity"], "ℹ️")
                    print(f"  {emoji} [{f['severity']}] {f['title']}")
            else:
                config = MonitorConfig()
                tracker = TokenTracker()
                pipeline = AuditPipeline(config, tracker)
                with open(filepath) as f:
                    source = f.read()
                result = await pipeline.audit_contract(source, "demo", "ethereum", filename)
                print(f"\n📊 {len(result.findings)} findings | {result.total_tokens:,} tokens")
                for f in sorted(result.findings, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(x.severity, 5)):
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "ℹ️"}.get(f.severity, "")
                    print(f"  {emoji} [{f.severity}] {f.title}")

    # Generate usage report
    tracker = TokenTracker()
    print(f"\n{tracker.generate_report()}")


def _create_demo_contracts():
    """Create demo contracts if none exist."""
    vault = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VulnerableVault {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() { owner = msg.sender; }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABILITY: Reentrancy
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;
    }

    // VULNERABILITY: tx.origin
    function adminWithdraw(address to, uint256 amount) external {
        require(tx.origin == owner);
        (bool success, ) = to.call{value: amount}("");
        require(success);
    }

    // VULNERABILITY: Unprotected selfdestruct
    function destroy() external {
        selfdestruct(payable(msg.sender));
    }

    receive() external payable {}
}
"""
    os.makedirs("contracts/examples", exist_ok=True)
    with open("contracts/examples/vulnerable_vault.sol", "w") as f:
        f.write(vault)


async def main():
    args = parse_args()

    if not args.command:
        print(BANNER)
        print("Commands: monitor | scan | audit | report | stats | demo")
        print("\nQuick start:")
        print("  python -m src.main demo --no-api    # Free demo (no API key)")
        print("  python -m src.main monitor           # Start 24/7 monitoring")
        print("  python -m src.main audit contract.sol")
        return

    if args.command == "monitor":
        await cmd_monitor(args)
    elif args.command == "scan":
        await cmd_scan(args)
    elif args.command == "audit":
        await cmd_audit(args)
    elif args.command == "report":
        await cmd_report(args)
    elif args.command == "stats":
        await cmd_stats(args)
    elif args.command == "demo":
        await cmd_demo(args)


if __name__ == "__main__":
    asyncio.run(main())
