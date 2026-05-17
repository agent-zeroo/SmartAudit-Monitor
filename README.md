# 🔒 SmartAudit Monitor

**24/7 Autonomous Smart Contract Security Monitoring Agent — Powered by Xiaomi MiMo V2.5**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![MiMo](https://img.shields.io/badge/Powered%20by-MiMo%20V2.5-orange.svg)](https://mimo.xiaomi.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 What Is This?

SmartAudit Monitor is a **24/7 autonomous agent** that watches blockchain networks for new smart contract deployments and automatically audits them using a **4-agent AI pipeline** powered by Xiaomi MiMo V2.5.

Unlike one-shot audit tools, SmartAudit Monitor runs **continuously**, consuming **~1M MiMo tokens/day** as it scans, analyzes, and reports on smart contract security across Ethereum, BSC, and Polygon.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                SmartAudit Monitor v2.0                       │
│            Autonomous 24/7 Security Agent                    │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Blockchain   │───▶│   Contract   │───▶│   Multi-     │   │
│  │  Event        │    │   Fetcher    │    │   Agent      │   │
│  │  Listener     │    │              │    │   Pipeline   │   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘   │
│                                                  │           │
│  ┌──────────────────────────────────────────────┼─────────┐ │
│  │              MiMo V2.5 API (1M tokens/day)   │         │ │
│  │                                               │         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───┴──────┐  │ │
│  │  │Vuln      │ │Logic     │ │Exploit   │ │Report    │  │ │
│  │  │Scanner   │ │Analyzer  │ │Cross-Ref │ │Generator │  │ │
│  │  │(15K tok) │ │(12K tok) │ │(10K tok) │ │(8K tok)  │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Token       │    │  Daily       │    │  Alert       │   │
│  │  Tracker     │    │  Reports     │    │  System      │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/agent-zeroo/SmartAudit-Monitor.git
cd SmartAudit-Monitor
pip install -r requirements.txt

# Demo (no API key needed)
python -m src.main demo --no-api

# Full audit with MiMo
export MIMO_API_KEY="your-key"
python -m src.main audit contracts/examples/vulnerable_vault.sol

# Start 24/7 monitoring
python -m src.main monitor --chain ethereum --chain bsc
```

---

## 📊 Token Consumption

| Mode | Tokens/Hour | Tokens/Day | Audits/Day |
|------|------------|------------|------------|
| **Monitoring** (3 chains) | ~42K | ~1M | ~20 |
| **Single Audit** | — | ~50K | 1 |
| **Demo (pattern-only)** | 0 | 0 | unlimited |

The system is designed to consume **~1M tokens/day** during active monitoring, demonstrating heavy sustained MiMo API usage.

---

## 🤖 Multi-Agent Pipeline

Each contract goes through 4 specialized AI agents:

1. **🔎 Vulnerability Scanner** — Detects 15+ known vulnerability patterns (reentrancy, overflow, access control, oracle manipulation)
2. **🧠 Logic Analyzer** — Deep business logic analysis for economic attacks, state machine bugs
3. **📚 Exploit Cross-Reference** — Compares against historical DeFi exploits (The DAO, bZx, Mango Markets)
4. **📝 Report Generator** — Synthesizes all findings into professional audit report

---

## 📁 Structure

```
SmartAudit-Monitor/
├── src/
│   ├── main.py                 # CLI entry point
│   ├── config.py               # Configuration
│   ├── orchestrator.py         # Main autonomous loop
│   ├── agents/
│   │   └── pipeline.py         # 4-agent audit pipeline
│   ├── monitor/
│   │   └── blockchain.py       # Blockchain event listener
│   └── utils/
│       ├── token_tracker.py    # Token usage tracking
│       ├── vuln_patterns.py    # Vulnerability pattern DB
│       └── daily_report.py     # Daily report generator
├── contracts/examples/         # Example vulnerable contracts
├── reports/                    # Generated audit reports
├── logs/                       # Monitor logs + SQLite DB
└── tests/
```

---

## 📈 Example Output

```
╔══════════════════════════════════════════════════════════════╗
║          🔒 SmartAudit Monitor v2.0                         ║
║     24/7 Autonomous Smart Contract Security Agent            ║
╚══════════════════════════════════════════════════════════════╝

📡 Scanning blocks 19500100 → 19500110 on ethereum
  📦 Found 3 new contracts

  🔍 Auditing: UniswapV3Pool (0x1234abcd...)
    🔎 Vulnerability Scanner ✅ 5 findings, 14,200 tokens
    🧠 Logic Analyzer        ✅ 3 findings, 11,800 tokens
    📚 Exploit Cross-Ref     ✅ 2 findings, 9,500 tokens
    📝 Report Generator      ✅ 8,200 tokens

  📊 Results: 10 findings | 🔴 1 🟠 3 🟡 4 🟢 2 | 43,700 tokens | 18.2s
```

---

## 🛣️ Roadmap

- [x] Blockchain monitoring (Ethereum, BSC, Polygon)
- [x] 4-agent MiMo V2.5 audit pipeline
- [x] Token usage tracking with SQLite
- [x] Daily report generation
- [ ] Web dashboard (real-time stats)
- [ ] Telegram/Discord alerts for critical findings
- [ ] Etherscan verified source auto-fetch
- [ ] Bytecode decompilation for unverified contracts
- [ ] CI/CD integration for project-specific monitoring

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

**Built with ❤️ and Xiaomi MiMo V2.5 by [@agent-zeroo](https://github.com/agent-zeroo)**
