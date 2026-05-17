"""
Blockchain Monitor — Watches for new smart contract deployments.
Supports Ethereum, BSC, Polygon via RPC.
"""

import json
import time
import sqlite3
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class ContractDeployment:
    """A newly deployed smart contract."""
    address: str
    chain: str
    deployer: str
    tx_hash: str
    block_number: int
    timestamp: float
    bytecode_size: int
    source_verified: bool = False
    source_code: str = ""
    contract_name: str = ""
    compiler_version: str = ""


class BlockchainMonitor:
    """Monitors blockchain for new contract deployments."""

    # Known contract creation opcodes pattern
    CREATE2_PREFIX = "0x363d3d373d3d3d363d73"
    MIN_BYTECODE_SIZE = 100  # Skip trivial contracts

    def __init__(self, config):
        self.config = config
        self.db_path = config.db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self.running = False
        self.last_block = config.blockchain.start_block or 0

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                address TEXT,
                chain TEXT,
                deployer TEXT,
                tx_hash TEXT,
                block_number INTEGER,
                timestamp REAL,
                bytecode_size INTEGER,
                source_verified INTEGER DEFAULT 0,
                source_code TEXT DEFAULT '',
                contract_name TEXT DEFAULT '',
                audited INTEGER DEFAULT 0,
                audit_score TEXT DEFAULT '',
                PRIMARY KEY (address, chain)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_state (
                chain TEXT PRIMARY KEY,
                last_block INTEGER,
                last_scan REAL
            )
        """)
        conn.commit()
        conn.close()

    def get_latest_block(self, chain: str = "ethereum") -> int:
        """Get latest block number from RPC."""
        rpc_url = self._get_rpc_url(chain)
        try:
            resp = requests.post(rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
            }, timeout=10)
            return int(resp.json()["result"], 16)
        except Exception as e:
            print(f"  ⚠️  RPC error ({chain}): {e}")
            return 0

    def get_contract_creation_txs(self, block_number: int, chain: str = "ethereum") -> list[dict]:
        """Get contract creation transactions from a block."""
        rpc_url = self._get_rpc_url(chain)
        try:
            resp = requests.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(block_number), True],
                "id": 1
            }, timeout=15)
            block = resp.json().get("result", {})
            if not block:
                return []

            contracts = []
            for tx in block.get("transactions", []):
                # Contract creation: 'to' is null
                if tx.get("to") is None or tx.get("to") == "":
                    contracts.append({
                        "tx_hash": tx["hash"],
                        "deployer": tx["from"],
                        "block_number": block_number,
                        "timestamp": int(block["timestamp"], 16),
                    })
            return contracts
        except Exception as e:
            print(f"  ⚠️  Block fetch error: {e}")
            return []

    def get_contract_address(self, tx_hash: str, chain: str = "ethereum") -> Optional[str]:
        """Get contract address from transaction receipt."""
        rpc_url = self._get_rpc_url(chain)
        try:
            resp = requests.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1
            }, timeout=10)
            receipt = resp.json().get("result", {})
            return receipt.get("contractAddress")
        except Exception:
            return None

    def get_bytecode(self, address: str, chain: str = "ethereum") -> str:
        """Get contract bytecode."""
        rpc_url = self._get_rpc_url(chain)
        try:
            resp = requests.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getCode",
                "params": [address, "latest"],
                "id": 1
            }, timeout=10)
            return resp.json().get("result", "0x")
        except Exception:
            return "0x"

    def fetch_source_from_etherscan(self, address: str, chain: str = "ethereum") -> Optional[dict]:
        """Try to fetch verified source code from Etherscan."""
        api_urls = {
            "ethereum": "https://api.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api",
            "polygon": "https://api.polygonscan.com/api",
        }
        api_url = api_urls.get(chain, api_urls["ethereum"])
        try:
            resp = requests.get(api_url, params={
                "module": "contract",
                "action": "getsourcecode",
                "address": address,
                "apikey": os.environ.get("ETHERSCAN_API_KEY", ""),
            }, timeout=10)
            data = resp.json().get("result", [{}])[0]
            if data.get("SourceCode"):
                return {
                    "source_code": data["SourceCode"],
                    "contract_name": data.get("ContractName", "Unknown"),
                    "compiler_version": data.get("CompilerVersion", ""),
                }
        except Exception:
            pass
        return None

    def scan_new_contracts(self, chain: str = "ethereum", max_blocks: int = 10) -> list[ContractDeployment]:
        """Scan recent blocks for new contract deployments."""
        latest = self.get_latest_block(chain)
        if latest == 0:
            return []

        # Get last scanned block
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT last_block FROM scan_state WHERE chain=?", (chain,))
        row = cursor.fetchone()
        start_block = row[0] + 1 if row else latest - max_blocks
        conn.close()

        if start_block > latest:
            return []

        end_block = min(start_block + max_blocks, latest)
        print(f"  📡 Scanning blocks {start_block} → {end_block} on {chain}")

        deployments = []
        for block_num in range(start_block, end_block + 1):
            txs = self.get_contract_creation_txs(block_num, chain)
            for tx in txs:
                address = self.get_contract_address(tx["tx_hash"], chain)
                if not address:
                    continue

                bytecode = self.get_bytecode(address, chain)
                bytecode_size = (len(bytecode) - 2) // 2  # hex to bytes

                if bytecode_size < self.config.min_contract_size:
                    continue

                # Try to get verified source
                source_info = self.fetch_source_from_etherscan(address, chain)

                deployment = ContractDeployment(
                    address=address,
                    chain=chain,
                    deployer=tx["deployer"],
                    tx_hash=tx["tx_hash"],
                    block_number=tx["block_number"],
                    timestamp=tx["timestamp"],
                    bytecode_size=bytecode_size,
                    source_verified=source_info is not None,
                    source_code=source_info["source_code"] if source_info else "",
                    contract_name=source_info["contract_name"] if source_info else "",
                    compiler_version=source_info["compiler_version"] if source_info else "",
                )
                deployments.append(deployment)

                # Save to DB
                self._save_contract(deployment)

            time.sleep(0.1)  # Rate limiting

        # Update scan state
        self._update_scan_state(chain, end_block)

        return deployments

    def _save_contract(self, contract: ContractDeployment):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR IGNORE INTO contracts (address, chain, deployer, tx_hash, block_number, "
            "timestamp, bytecode_size, source_verified, source_code, contract_name) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (contract.address, contract.chain, contract.deployer, contract.tx_hash,
             contract.block_number, contract.timestamp, contract.bytecode_size,
             int(contract.source_verified), contract.source_code, contract.contract_name)
        )
        conn.commit()
        conn.close()

    def _update_scan_state(self, chain: str, block: int):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO scan_state (chain, last_block, last_scan) VALUES (?,?,?)",
            (chain, block, time.time())
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """Get monitoring statistics."""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
        verified = conn.execute("SELECT COUNT(*) FROM contracts WHERE source_verified=1").fetchone()[0]
        audited = conn.execute("SELECT COUNT(*) FROM contracts WHERE audited=1").fetchone()[0]
        today_start = time.time() - 86400
        today = conn.execute("SELECT COUNT(*) FROM contracts WHERE timestamp>=?", (today_start,)).fetchone()[0]
        conn.close()
        return {
            "total_contracts": total,
            "verified_source": verified,
            "audited": audited,
            "today_deployments": today,
        }

    def _get_rpc_url(self, chain: str) -> str:
        urls = {
            "ethereum": self.config.blockchain.ethereum_rpc,
            "bsc": self.config.blockchain.bsc_rpc,
            "polygon": self.config.blockchain.polygon_rpc,
        }
        return urls.get(chain, urls["ethereum"])
