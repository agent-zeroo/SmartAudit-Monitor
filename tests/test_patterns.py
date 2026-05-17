"""Tests for SmartAudit Monitor."""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.vuln_patterns import scan_patterns, PATTERNS


class TestPatternScanner:
    def test_reentrancy(self):
        code = "function w() { msg.sender.call{value: 1}(\"\"); balances[msg.sender] -= 1; }"
        findings = scan_patterns(code)
        assert any("reentrancy" in f["category"] for f in findings)

    def test_tx_origin(self):
        code = "require(tx.origin == owner);"
        findings = scan_patterns(code)
        assert any("tx.origin" in f["title"] for f in findings)

    def test_selfdestruct(self):
        code = "selfdestruct(payable(msg.sender));"
        findings = scan_patterns(code)
        assert any("selfdestruct" in f["title"].lower() for f in findings)

    def test_clean_code(self):
        code = "function safe() external pure returns (uint) { return 42; }"
        findings = scan_patterns(code)
        critical = [f for f in findings if f["severity"] == "CRITICAL"]
        assert len(critical) == 0

    def test_vulnerable_vault(self):
        vault = os.path.join(os.path.dirname(__file__), "..", "contracts", "examples", "vulnerable_vault.sol")
        if os.path.exists(vault):
            with open(vault) as f:
                code = f.read()
            findings = scan_patterns(code)
            assert len(findings) >= 3

    def test_pattern_count(self):
        assert len(PATTERNS) >= 10

    def test_all_patterns_valid(self):
        for p in PATTERNS:
            assert p.name
            assert p.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
            assert p.pattern


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
