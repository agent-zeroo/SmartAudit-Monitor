"""
SmartAudit Monitor — Main Orchestrator.
The autonomous loop that ties blockchain monitoring + audit pipeline together.
"""

import asyncio
import json
import os
import signal
import time
from datetime import datetime

from .config import MonitorConfig
from .monitor.blockchain import BlockchainMonitor
from .agents.pipeline import AuditPipeline
from .utils.token_tracker import TokenTracker, TokenUsage


class MonitorOrchestrator:
    """
    Main orchestrator — runs the autonomous monitoring loop.

    Flow:
    1. Poll blockchain for new contract deployments
    2. For each verified contract → trigger multi-agent audit
    3. Save audit report + findings to disk
    4. Track token usage for dashboard
    5. Alert on critical findings
    6. Generate daily summary reports
    """

    def __init__(self, config: MonitorConfig = None):
        self.config = config or MonitorConfig()
        self.blockchain = BlockchainMonitor(self.config)
        self.tracker = TokenTracker(self.config.db_path.replace(".db", "_tokens.db"))
        self.pipeline = AuditPipeline(self.config, self.tracker)
        self.running = False
        self.stats = {
            "start_time": 0,
            "contracts_scanned": 0,
            "audits_completed": 0,
            "critical_findings": 0,
            "high_findings": 0,
            "total_tokens": 0,
            "errors": 0,
        }

    async def start(self):
        """Start the autonomous monitoring loop."""
        self.running = True
        self.stats["start_time"] = time.time()

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║          🔒 SmartAudit Monitor v2.0                         ║
║     24/7 Autonomous Smart Contract Security Agent            ║
║          Powered by Xiaomi MiMo V2.5                        ║
╚══════════════════════════════════════════════════════════════╝

🚀 Starting autonomous monitoring loop...
📡 Chains: {', '.join(self.config.blockchain.chains)}
🪙 Token Budget: {self.config.daily_token_budget:,}/day
⏱️  Poll Interval: {self.config.blockchain.poll_interval}s
🤖 Max Concurrent: {self.config.max_concurrent_audits}
""")

        cycle = 0
        while self.running:
            cycle += 1
            try:
                await self._run_cycle(cycle)
            except KeyboardInterrupt:
                print("\n⚠️  Shutting down gracefully...")
                break
            except Exception as e:
                self.stats["errors"] += 1
                print(f"  ❌ Cycle error: {e}")
                await asyncio.sleep(30)

            # Check daily budget
            today = self.tracker.get_today_usage()
            if today["total_tokens"] >= self.config.daily_token_budget:
                print(f"\n  ⏸️  Daily token budget reached ({today['total_tokens']:,}). Sleeping until reset...")
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(self.config.blockchain.poll_interval)

        self._shutdown()

    async def _run_cycle(self, cycle: int):
        """Single monitoring cycle."""
        for chain in self.config.blockchain.chains:
            deployments = self.blockchain.scan_new_contracts(chain, max_blocks=5)

            if deployments:
                print(f"\n  📦 Cycle {cycle}: Found {len(deployments)} new contracts on {chain}")

                for deployment in deployments:
                    self.stats["contracts_scanned"] += 1

                    # Only audit contracts with verified source (or large bytecode)
                    if deployment.source_verified and deployment.source_code:
                        print(f"\n  🔍 Auditing: {deployment.contract_name} ({deployment.address[:10]}...)")
                        await self._audit_and_save(deployment)
                    elif deployment.bytecode_size > 1000:
                        # Large unverified contract — still interesting
                        print(f"\n  📐 Analyzing bytecode: {deployment.address[:10]}... ({deployment.bytecode_size} bytes)")
                        await self._bytecode_analysis(deployment)
            else:
                if cycle % 50 == 0:  # Print heartbeat every ~50 cycles
                    uptime_min = (time.time() - self.stats["start_time"]) / 60
                    today = self.tracker.get_today_usage()
                    print(f"  💓 Heartbeat #{cycle} | Uptime: {uptime_min:.0f}min | "
                          f"Tokens today: {today['total_tokens']:,} | "
                          f"Audits: {self.stats['audits_completed']} | "
                          f"Errors: {self.stats['errors']}")

    async def _audit_and_save(self, deployment):
        """Run full audit on a verified contract and save results."""
        try:
            result = await self.pipeline.audit_contract(
                source_code=deployment.source_code,
                address=deployment.address,
                chain=deployment.chain,
                contract_name=deployment.contract_name,
            )

            self.stats["audits_completed"] += 1
            self.stats["total_tokens"] += result.total_tokens

            # Count severities
            for f in result.findings:
                if f.severity == "CRITICAL":
                    self.stats["critical_findings"] += 1
                elif f.severity == "HIGH":
                    self.stats["high_findings"] += 1

            # Save report
            self._save_report(deployment, result)

            # Summary
            sev_counts = {}
            for f in result.findings:
                sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

            print(f"    📊 Results: {len(result.findings)} findings | "
                  f"🔴 {sev_counts.get('CRITICAL', 0)} 🟠 {sev_counts.get('HIGH', 0)} "
                  f"🟡 {sev_counts.get('MEDIUM', 0)} | "
                  f"{result.total_tokens:,} tokens | {result.duration_ms/1000:.1f}s")

            # Alert on critical
            if self.config.alert_on_critical and sev_counts.get("CRITICAL", 0) > 0:
                await self._send_alert(deployment, result, sev_counts)

        except Exception as e:
            self.stats["errors"] += 1
            print(f"    ❌ Audit failed: {e}")

    async def _bytecode_analysis(self, deployment):
        """Analyze unverified contract bytecode patterns."""
        try:
            prompt = f"Analyze this contract bytecode for security patterns:\nAddress: {deployment.address}\nChain: {deployment.chain}\nBytecode size: {deployment.bytecode_size} bytes\n\nThis contract is NOT verified on Etherscan. Based on bytecode size and patterns, assess the risk level and any observable patterns."
            resp = await self.pipeline.llm.chat(
                "You are a bytecode analysis expert. Assess smart contract bytecode for security risks.",
                prompt, temperature=0.2
            )
            self.tracker.record(TokenUsage(
                time.time(), "Bytecode Analyzer", resp.tokens_used,
                self.config.mimo.model, "analysis", deployment.address, deployment.chain
            ))
            self.stats["total_tokens"] += resp.tokens_used
            print(f"    ✅ Bytecode analysis done ({resp.tokens_used:,} tokens)")
        except Exception as e:
            print(f"    ⚠️  Bytecode analysis failed: {e}")

    def _save_report(self, deployment, result):
        """Save audit report to disk."""
        date_dir = datetime.now().strftime("%Y-%m-%d")
        report_dir = os.path.join(self.config.reports_dir, date_dir)
        os.makedirs(report_dir, exist_ok=True)

        filename = f"{deployment.chain}_{deployment.address[:10]}_{deployment.contract_name}.md"
        filepath = os.path.join(report_dir, filename)

        with open(filepath, "w") as f:
            f.write(result.report_markdown)

        # Also save JSON summary
        summary = {
            "address": deployment.address,
            "chain": deployment.chain,
            "contract_name": deployment.contract_name,
            "deployer": deployment.deployer,
            "block_number": deployment.block_number,
            "bytecode_size": deployment.bytecode_size,
            "findings_count": len(result.findings),
            "total_tokens": result.total_tokens,
            "duration_ms": result.duration_ms,
            "severities": {},
            "timestamp": time.time(),
        }
        for f_obj in result.findings:
            summary["severities"][f_obj.severity] = summary["severities"].get(f_obj.severity, 0) + 1

        json_path = filepath.replace(".md", ".json")
        with open(json_path, "w") as jf:
            json.dump(summary, jf, indent=2)

    async def _send_alert(self, deployment, result, sev_counts):
        """Send alert on critical findings."""
        alert_msg = (
            f"🚨 CRITICAL VULNERABILITY FOUND\n"
            f"Contract: {deployment.contract_name} ({deployment.address[:10]}...)\n"
            f"Chain: {deployment.chain}\n"
            f"Findings: 🔴 {sev_counts.get('CRITICAL', 0)} | 🟠 {sev_counts.get('HIGH', 0)}\n"
            f"Tokens used: {result.total_tokens:,}"
        )
        print(f"\n    {alert_msg}")

    def _shutdown(self):
        """Graceful shutdown — save stats."""
        self.tracker.save_daily_summary()
        session = self.tracker.get_session_usage()
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🛑 Monitor Stopped                        ║
╠══════════════════════════════════════════════════════════════╣
║  Session Tokens:  {session['session_tokens']:>10,}                              ║
║  Duration:        {session['session_duration_min']:>10.1f} min                          ║
║  Contracts:       {self.stats['contracts_scanned']:>10,}                              ║
║  Audits:          {self.stats['audits_completed']:>10,}                              ║
║  Critical:        {self.stats['critical_findings']:>10,}                              ║
║  Errors:          {self.stats['errors']:>10,}                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    def get_dashboard_data(self) -> dict:
        """Get all data for dashboard rendering."""
        return {
            "stats": self.stats,
            "token_usage": self.tracker.get_today_usage(),
            "session": self.tracker.get_session_usage(),
            "by_agent": self.tracker.get_usage_by_agent(24),
            "hourly": self.tracker.get_usage_by_hour(24),
            "contracts": self.blockchain.get_stats(),
            "uptime_min": (time.time() - self.stats["start_time"]) / 60 if self.stats["start_time"] else 0,
        }
