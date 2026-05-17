// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VulnerableVault
 * @notice INTENTIONALLY VULNERABLE — SmartAudit Monitor demo
 * @dev Contains 7+ security vulnerabilities for testing
 */

contract VulnerableVault {
    mapping(address => uint256) public balances;
    address public owner;
    bool public initialized;

    constructor() { owner = msg.sender; }

    function initialize(address _owner) public {
        // BUG: No initialized check — anyone can claim ownership
        owner = _owner;
        initialized = true;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // BUG: Reentrancy — external call before state update
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }

    // BUG: tx.origin authentication
    function adminWithdraw(address to, uint256 amount) external {
        require(tx.origin == owner, "Not owner");
        (bool success, ) = to.call{value: amount}("");
        require(success);
    }

    // BUG: Unchecked return value
    function unsafeTransfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        to.call{value: amount}("");
    }

    // BUG: Unprotected selfdestruct
    function destroy() external {
        selfdestruct(payable(msg.sender));
    }

    // BUG: Unbounded loop — gas limit risk
    function batchTransfer(address[] calldata recipients, uint256 amount) external {
        for (uint i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += amount;
        }
        balances[msg.sender] -= amount * recipients.length;
    }

    // BUG: Block timestamp dependency
    function isLucky() external view returns (bool) {
        return block.timestamp % 7 == 0;
    }

    receive() external payable {}
}
