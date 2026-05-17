// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DeFiLendingPool
 * @notice INTENTIONALLY VULNERABLE — SmartAudit Monitor demo
 * @dev Simulates DeFi lending with oracle manipulation and reentrancy risks
 */

interface IPriceOracle {
    function getPrice(address token) external view returns (uint256);
}

contract DeFiLendingPool {
    struct Loan {
        address borrower;
        uint256 collateralAmount;
        uint256 borrowAmount;
        uint256 startTime;
        bool active;
    }

    address public admin;
    IPriceOracle public oracle;
    mapping(address => Loan) public loans;
    mapping(address => uint256) public depositBalances;
    uint256 public totalDeposits;
    uint256 public totalBorrowed;
    uint256 public constant COLLATERAL_RATIO = 150;
    uint256 public constant INTEREST_RATE = 5;

    constructor(address _oracle) {
        oracle = IPriceOracle(_oracle);
        admin = msg.sender;
    }

    // BUG: State update after transfer (reentrancy with ERC777)
    function deposit(uint256 amount) external {
        depositBalances[msg.sender] += amount;
        totalDeposits += amount;
    }

    // BUG: Oracle price can be flash-loaned
    function borrow(uint256 collateralAmt, uint256 borrowAmt) external {
        require(!loans[msg.sender].active, "Existing loan");
        uint256 collateralValue = collateralAmt * oracle.getPrice(address(this));
        require(collateralValue >= borrowAmt * COLLATERAL_RATIO / 100, "Insufficient collateral");

        loans[msg.sender] = Loan(msg.sender, collateralAmt, borrowAmt, block.timestamp, true);
        totalBorrowed += borrowAmt;
    }

    // BUG: Oracle manipulation via flash loan for liquidation
    function liquidate(address borrower) external {
        Loan storage loan = loans[borrower];
        require(loan.active, "No active loan");
        uint256 collateralValue = loan.collateralAmount * oracle.getPrice(address(this));
        uint256 loanValue = loan.borrowAmount + _calculateInterest(loan);

        if (collateralValue * 100 < loanValue * 120) {
            // Liquidator gets collateral — oracle can be manipulated
            totalBorrowed -= loan.borrowAmount;
            delete loans[borrower];
        }
    }

    // BUG: Admin can drain funds (centralization)
    function emergencyWithdraw(uint256 amount) external {
        require(msg.sender == admin, "Not admin");
        totalDeposits -= amount;
    }

    // BUG: No zero-address check
    function updateOracle(address newOracle) external {
        require(msg.sender == admin, "Not admin");
        oracle = IPriceOracle(newOracle);
    }

    function _calculateInterest(Loan storage loan) internal view returns (uint256) {
        uint256 duration = block.timestamp - loan.startTime;
        return loan.borrowAmount * INTEREST_RATE * duration / (365 days * 100);
    }
}
