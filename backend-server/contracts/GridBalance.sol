// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;
import "./Prosumer.sol";
contract GridBalance {
    mapping(address => address) prosumerContracts;
    event ProsumerRegistered(address contractAddress, address prosumerAddress);
    function registerProsumer() public returns (address) {
        address prosumerAddress = msg.sender;
        require(prosumerContracts[prosumerAddress] == address(0x0));
        address newProsumer = address(new Prosumer(address(this), prosumerAddress));
        emit ProsumerRegistered(newProsumer, prosumerAddress);
        prosumerContracts[prosumerAddress] = newProsumer;
        return newProsumer;
    }
}