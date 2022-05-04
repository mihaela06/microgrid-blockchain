// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;
import "./GridBalance.sol";

contract Prosumer {
    address gridBalanceContract;
    address prosumerAddress;
    int256[2880] registeredValues;

    constructor(address _gridBalanceContract, address _prosumerAddress) {
        gridBalanceContract = _gridBalanceContract;
        prosumerAddress = _prosumerAddress;
    }

    function registerValue(int256 value, uint256 index) public {
        require(prosumerAddress == msg.sender);
        registeredValues[index] = value;
    }

    function getValue(uint256 index) public view returns (int256) {
        return registeredValues[index];
    }
}
