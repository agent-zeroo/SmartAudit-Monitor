"""
Vulnerability Pattern Database — Static analysis patterns.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class VulnPattern:
    name: str
    category: str
    severity: str
    description: str
    pattern: str
    fix: str
    cwe_id: Optional[str] = None


PATTERNS = [
    VulnPattern("Reentrancy - External Call Before State Update", "reentrancy", "CRITICAL",
                "External call before state update.", r"\.call\{.*value.*\}[\s\S]*?(?:balances|balanceOf)\[.*\]\s*[-+]=",
                "Update state before external calls.", "CWE-841"),
    VulnPattern("tx.origin Authentication", "access_control", "HIGH",
                "Using tx.origin for authentication.", r"tx\.origin\s*==",
                "Use msg.sender instead.", "CWE-477"),
    VulnPattern("Unprotected Selfdestruct", "access_control", "CRITICAL",
                "selfdestruct callable by anyone.", r"selfdestruct\s*\(\s*payable",
                "Add strict access control.", "CWE-284"),
    VulnPattern("Unchecked Low-Level Call", "unchecked_calls", "HIGH",
                "Return value not checked.", r"\.call[\{\(]",
                "Check return values.", "CWE-252"),
    VulnPattern("Spot Price Oracle", "oracle", "HIGH",
                "Using DEX spot price as oracle.", r"getReserves|getAmountOut|quote",
                "Use TWAP or Chainlink.", "CWE-829"),
    VulnPattern("Missing Access Control", "access_control", "CRITICAL",
                "Critical function lacks modifiers.", r"function\s+(?:withdraw|mint|burn|pause|upgrade)\w*\(",
                "Add onlyOwner modifier.", "CWE-284"),
    VulnPattern("Unbounded Loop", "dos", "MEDIUM",
                "Loop over unbounded array.", r"for\s*\(\s*uint\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*\w+\.length",
                "Implement pagination.", "CWE-400"),
    VulnPattern("Block Timestamp Dependency", "front_running", "MEDIUM",
                "Logic depends on block.timestamp.", r"block\.timestamp\s*[<>=!]+",
                "Use block numbers.", "CWE-829"),
    VulnPattern("Missing ERC20 Return Check", "token", "MEDIUM",
                "ERC20 return value not checked.", r"\.transfer\(|\.transferFrom\(",
                "Use SafeERC20.", "CWE-252"),
    VulnPattern("ecrecover Without Validation", "signature", "HIGH",
                "ecrecover result not validated.", r"ecrecover\([^)]+\)",
                "Validate result != address(0).", "CWE-347"),
    VulnPattern("Unchecked Send", "unchecked_calls", "MEDIUM",
                "send() return not checked.", r"\.send\([^)]*\)",
                "Check return or use transfer.", "CWE-252"),
    VulnPattern("Delegatecall to User Input", "access_control", "CRITICAL",
                "delegatecall with user-controlled target.", r"delegatecall\(",
                "Restrict delegatecall targets.", "CWE-829"),
    VulnPattern("Floating Pragma", "code_quality", "LOW",
                "Compiler version not pinned.", r"pragma solidity \^",
                "Pin exact compiler version.", None),
    VulnPattern("Dangerous Approve", "token", "MEDIUM",
                "Unlimited token approval.", r"\.approve\(.*,\s*2\*\*256\s*-\s*1|type\(uint\)\.max",
                "Use increaseAllowance or limit.", None),
    VulnPattern("Centralization - Single Owner", "centralization", "MEDIUM",
                "Single owner can drain funds.", r"function\s+(?:emergency|drain|sweep)\w*.*onlyOwner",
                "Add timelock/multisig.", None),
]


def scan_patterns(source_code: str) -> list[dict]:
    """Scan source code against vulnerability patterns."""
    findings = []
    for p in PATTERNS:
        try:
            for match in re.finditer(p.pattern, source_code, re.MULTILINE | re.DOTALL):
                start = max(0, match.start() - 50)
                end = min(len(source_code), match.end() + 50)
                findings.append({
                    "title": p.name, "severity": p.severity, "category": p.category,
                    "description": p.description, "code_snippet": source_code[start:end].strip(),
                    "recommendation": p.fix, "cwe_id": p.cwe_id, "confidence": 0.7,
                })
        except re.error:
            continue
    return findings
