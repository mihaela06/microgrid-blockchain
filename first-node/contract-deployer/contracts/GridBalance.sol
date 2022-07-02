// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 */
import "./Prosumer.sol";

contract GridBalance {
    mapping(address => address) private prosumerContracts;
    address[] private registeredProsumers;
    mapping(address => int32) private prosumerImbalances;
    event ProsumerRegistered(address contractAddress, address prosumerAddress);
    event newDRSignals(int32 balanceState);
    event imbalanceRegistered(address prosumerAddress, int32 newBalanceState);
    uint32 private rewardRate = 1;
    int32 balanceState;
    uint32 gridThreshold = 50; // when ~= 0 island mode
    uint256 DRStart;
    uint32 DRLength = 12;

    function registerProsumer(uint32 _threshold) public returns (address) {
        address prosumerAddress = msg.sender;
        // require(prosumerContracts[prosumerAddress] == address(0x0));
        address newProsumer = address(
            new Prosumer(address(this), prosumerAddress, _threshold)
        );
        emit ProsumerRegistered(newProsumer, prosumerAddress);
        prosumerContracts[prosumerAddress] = newProsumer;
        registeredProsumers.push(prosumerAddress);
        return newProsumer;
    }

    function getRewardRate() external view returns (uint32) {
        // require(prosumerContracts[tx.origin] == msg.sender);
        return rewardRate; // TODO: setter and private var that modifies - increases with grid imbalance
    }

    function registerProsumerImbalance(int32 _imbalance) external {
        // require(prosumerContracts[tx.origin] == msg.sender); // the Prosumer contract that called the function is registered for the prosumer account address that began the transaction
        balanceState -= prosumerImbalances[tx.origin];
        balanceState += _imbalance;
        prosumerImbalances[tx.origin] = _imbalance;
        int32 absBalanceState = balanceState;
        if (absBalanceState < 0) absBalanceState = 0 - absBalanceState;
        if (uint32(absBalanceState) > gridThreshold) sendDRSignals();
        emit imbalanceRegistered(tx.origin, balanceState);
    }

    function sendDRSignals() private {
        uint256 nowTimestamp = block.timestamp;
        if (nowTimestamp - DRStart < DRLength * 2)
            // if not every second i should multiply DRLength with period T
            return;
        for (uint256 i = 0; i < registeredProsumers.length; i++) {
            Prosumer prosumer = Prosumer(
                prosumerContracts[registeredProsumers[i]]
            );
            prosumer.actualizeDRSignal(balanceState, DRLength);
            // TODO reset imbalances and balance state?
        }
        emit newDRSignals(balanceState);
        DRStart = nowTimestamp;
    }

    // function to change DR len, reward rate
}
