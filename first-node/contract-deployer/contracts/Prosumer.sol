// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./GridBalance.sol";

/**
 * @title Prosumer
 * @dev Register current consumption
 */
contract Prosumer {
    address private gridBalanceContract;
    address private prosumerAddress;

    uint32 threshold;
    int32[12] private DRSignal;
    int32[12] private baselineValues;
    uint16 private DRIndex;
    uint16 private baselineIndex;
    uint32 private DRLength;
    int32 private balance;
    bytes32 private hash;

    event valueRegistered(address indexed prosumerAddress, int256 value);
    event registeredDRSignal(address indexed prosumerAddress, int32[12] DRSignal, uint32 DRLength);
    
    /**
     * @dev Set prosumer account address and grid balance SC address
     * @param _gridBalanceContract address of grid balance SC
     * @param _prosumerAddress address of prosumer account
     */
    constructor(address _gridBalanceContract, address _prosumerAddress, uint32 _threshold) {
        gridBalanceContract = _gridBalanceContract;
        prosumerAddress = _prosumerAddress;
        threshold = _threshold;
        DRIndex = 0;
        DRLength = 0;
        baselineIndex = 0;
    }

    function increaseIndex(uint16 _index) private pure returns (uint16) {
        _index += 1;
        if (_index == 12)
            _index = 0;
        return _index;
    }

    /**
     * @dev Register new consumption value
     * @param value New consumption value (in W)
     */
    function registerValue(int32 value) external {        
        // require(prosumerAddress == msg.sender);
        
        emit valueRegistered(prosumerAddress, value);

        GridBalance gridContract = GridBalance(gridBalanceContract);
        int32 requiredValue;
        if (DRLength < DRIndex)
            requiredValue = DRSignal[DRIndex];
        else
            requiredValue = baselineValues[baselineIndex];

        int32 diff = requiredValue - value;
        diff = 0 - diff;
        uint32 diffAbs = uint32(diff);
        uint32 rewardRate = gridContract.getRewardRate();

        if (diffAbs > threshold) {
            balance -= (100 * int32(diffAbs - threshold)) * int32(rewardRate) / int32(threshold);
        }
        else if (diffAbs < threshold) {
            balance += (100 * int32(threshold - diffAbs)) * int32(rewardRate) / int32(threshold);
        }
        gridContract.registerProsumerImbalance(diff);
        DRIndex = increaseIndex(DRIndex);
    }

    function actualizeBaseline(int32[] calldata _baselineValues, uint16 _length) external {
        // require(_length == 12);
        // require(prosumerAddress == msg.sender);

        // TODO limit how often you can call it and emit event to be interpreted by tso

        baselineIndex = 0;
        for (uint16 i = 0; i < _length; i++) 
            baselineValues[i] = _baselineValues[i];
    }

    function actualizeDRSignal(int32 _balanceState, uint32 _DRLength) public {
        // require(msg.sender == gridBalanceContract);
        // require(_DRLength <= 12);
        DRIndex = 0;
        for (uint i = 0; i < _DRLength; i++) {
            if (baselineValues[i] == 0)
                DRSignal[i] = 0;
            else
                DRSignal[i] = baselineValues[i] + (_balanceState/baselineValues[i]);
        }
        DRLength = _DRLength;
        emit registeredDRSignal(prosumerAddress, DRSignal, DRLength);
    }

    
    function registerHash(bytes32 _hash) external {
        hash = _hash;
    }

    function getHash() public view returns (bytes32) {
        return hash;
    }
}
