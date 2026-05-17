"""
Multi-Agent Audit Pipeline — Core MiMo V2.5 integration.
4 specialized agents for comprehensive smart contract analysis.
"""

import json
import time
import os
import re
from dataclasses import dataclass
from typing import Optional

import openai

from ..utils.token_tracker import TokenUsage


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int


@dataclass
class AuditFinding:
    title: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    description: str
    impact: str
    recommendation: str
    confidence: float
    code_snippet: str = ""


@dataclass
class AuditResult:
    contract_address: str
    chain: str
    findings: list[AuditFinding]
    report_markdown: str
    total_tokens: int
    duration_ms: int
    agents_used: list[str]


class MiMoLLM:
    """Xiaomi MiMo V2.5 API client."""

    def __init__(self, config):
        self.client = openai.AsyncOpenAI(
            api_key=config.api_key or os.environ.get("MIMO_API_KEY", ""),
            base_url=config.base_url,
        )
        self.model = config.model
        self.default_temp = config.temperature
        self.default_max = config.max_tokens

    async def chat(self, system: str, user: str, temperature: float = None,
                   max_tokens: int = None) -> LLMResponse:
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature or self.default_temp,
                max_tokens=max_tokens or self.default_max,
            )
            return LLMResponse(
                content=resp.choices[0].message.content or "",
                model=resp.model,
                tokens_used=resp.usage.total_tokens if resp.usage else 0,
            )
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", model=self.model, tokens_used=0)


# ============================================================
# AGENT SYSTEM PROMPTS
# ============================================================

VULN_SCANNER_PROMPT = """You are a smart contract security expert specializing in static vulnerability analysis.
Scan Solidity source code for KNOWN vulnerability patterns:
1. Reentrancy 2. Integer Overflow 3. Access Control 4. Unchecked Calls
5. Front-running 6. Denial of Service 7. Flash Loan 8. Logic Errors
9. Centralization 10. Signature Issues

Return JSON: {"findings": [{"title":"...", "severity":"CRITICAL|HIGH|MEDIUM|LOW|INFO", "category":"...", "location":"...", "description":"...", "impact":"...", "recommendation":"...", "confidence":0.0-1.0}]}
Be thorough. False positives > missed vulns."""

LOGIC_ANALYZER_PROMPT = """You are a senior smart contract auditor specializing in business logic analysis.
Analyze beyond known patterns:
1. Business Logic Flaws 2. Economic Attacks 3. State Machine Bugs
4. Composability Risks 5. Upgrade Risks 6. Oracle Dependencies
7. Token Standards 8. Governance Attacks

Return JSON: {"findings": [{"title":"...", "severity":"...", "category":"logic|economic|state|oracle|governance", "description":"...", "impact":"...", "attack_vector":"...", "recommendation":"...", "confidence":0.0-1.0}]}
Think like an attacker."""

EXPLOIT_CROSSREF_PROMPT = """You are a blockchain security researcher with deep knowledge of historical DeFi exploits.
Cross-reference the contract with known exploits:
- Flash loan attacks (bZx, PancakeBunny, Cream)
- Oracle manipulation (Mango Markets, Bonq DAO)
- Reentrancy (The DAO, Cream Finance)
- Access control (Poly Network, Wormhole)
- Logic bugs (Wormhole, Ronin Bridge)
- Governance attacks (Beanstalk)

Return JSON: {"findings": [{"title":"...", "severity":"...", "similar_to":"...", "description":"...", "historical_context":"...", "risk_assessment":"...", "recommendation":"...", "confidence":0.0-1.0}]}"""

REPORT_GENERATOR_PROMPT = """You are a professional smart contract audit report writer.
Synthesize all findings into a clear, professional audit report.
Structure:
1. Executive Summary (overall risk, key stats)
2. Scope & Methodology
3. Findings Summary Table
4. Detailed Findings (sorted by severity)
5. Recommendations
6. Agent Analysis Summary

Use Markdown. Be professional and actionable."""


class AuditPipeline:
    """Multi-agent audit pipeline using MiMo V2.5."""

    def __init__(self, config, token_tracker):
        self.llm = MiMoLLM(config.mimo)
        self.tracker = token_tracker
        self.config = config

    async def audit_contract(self, source_code: str, address: str,
                             chain: str = "ethereum",
                             contract_name: str = "Unknown") -> AuditResult:
        """Run full multi-agent audit on a contract."""
        start = time.time()
        all_findings = []
        total_tokens = 0
        agents_used = []

        context = f"Contract: {contract_name}\nAddress: {address}\nChain: {chain}\n\n```solidity\n{source_code}\n```"

        # Agent 1: Vulnerability Scanner
        print(f"    🔎 Vulnerability Scanner...")
        resp1 = await self.llm.chat(VULN_SCANNER_PROMPT, context, temperature=0.1)
        findings1 = self._parse_findings(resp1.content)
        all_findings.extend(findings1)
        total_tokens += resp1.tokens_used
        agents_used.append("Vulnerability Scanner")
        self.tracker.record(TokenUsage(time.time(), "Vulnerability Scanner", resp1.tokens_used,
                                       self.config.mimo.model, "audit", address, chain))
        print(f"       ✅ {len(findings1)} findings, {resp1.tokens_used:,} tokens")

        # Agent 2: Logic Analyzer
        print(f"    🧠 Logic Analyzer...")
        resp2 = await self.llm.chat(LOGIC_ANALYZER_PROMPT, context, temperature=0.2)
        findings2 = self._parse_findings(resp2.content)
        all_findings.extend(findings2)
        total_tokens += resp2.tokens_used
        agents_used.append("Logic Analyzer")
        self.tracker.record(TokenUsage(time.time(), "Logic Analyzer", resp2.tokens_used,
                                       self.config.mimo.model, "audit", address, chain))
        print(f"       ✅ {len(findings2)} findings, {resp2.tokens_used:,} tokens")

        # Agent 3: Exploit Cross-Reference
        print(f"    📚 Exploit Cross-Reference...")
        resp3 = await self.llm.chat(EXPLOIT_CROSSREF_PROMPT, context, temperature=0.15)
        findings3 = self._parse_findings(resp3.content)
        all_findings.extend(findings3)
        total_tokens += resp3.tokens_used
        agents_used.append("Exploit Cross-Reference")
        self.tracker.record(TokenUsage(time.time(), "Exploit Cross-Reference", resp3.tokens_used,
                                       self.config.mimo.model, "audit", address, chain))
        print(f"       ✅ {len(findings3)} findings, {resp3.tokens_used:,} tokens")

        # Agent 4: Report Generator
        print(f"    📝 Report Generator...")
        findings_json = json.dumps([f.__dict__ for f in all_findings], indent=2)
        report_prompt = f"Contract: {contract_name} ({address}) on {chain}\n\nAll findings:\n{findings_json}\n\nGenerate comprehensive audit report in Markdown."
        resp4 = await self.llm.chat(REPORT_GENERATOR_PROMPT, report_prompt, temperature=0.3, max_tokens=8192)
        total_tokens += resp4.tokens_used
        agents_used.append("Report Generator")
        self.tracker.record(TokenUsage(time.time(), "Report Generator", resp4.tokens_used,
                                       self.config.mimo.model, "report", address, chain))
        print(f"       ✅ {resp4.tokens_used:,} tokens")

        duration_ms = int((time.time() - start) * 1000)

        return AuditResult(
            contract_address=address,
            chain=chain,
            findings=all_findings,
            report_markdown=resp4.content,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            agents_used=agents_used,
        )

    def _parse_findings(self, raw: str) -> list[AuditFinding]:
        """Parse agent JSON output into AuditFinding objects."""
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            data = json.loads(raw)
            items = data.get("findings", data if isinstance(data, list) else [])
            findings = []
            for f in items:
                findings.append(AuditFinding(
                    title=f.get("title", "Unknown"),
                    severity=f.get("severity", "INFO").upper(),
                    category=f.get("category", ""),
                    description=f.get("description", ""),
                    impact=f.get("impact", ""),
                    recommendation=f.get("recommendation", ""),
                    confidence=float(f.get("confidence", 0.5)),
                    code_snippet=f.get("code_snippet", ""),
                ))
            return findings
        except (json.JSONDecodeError, KeyError, IndexError):
            return [AuditFinding(
                title="Analysis Output",
                severity="INFO",
                category="general",
                description=raw[:500],
                impact="",
                recommendation="See full output",
                confidence=0.3,
            )]
