const express = require("express");
const fs = require('fs');
const Web3 = require('web3')
const _Common = require('@ethereumjs/common')
const eth = require('@ethereumjs/tx')

const Common = _Common.default

var provider = 'http://prosumer' + process.env.NODE_ID + '_polygon_1:8545'

var web3 = new Web3(new Web3.providers.HttpProvider(provider))
web3.transactionConfirmationBlocks = 1;

const addressFrom = fs.readFileSync('node/public_address.txt', 'utf8')
var privateKeyHex = fs.readFileSync('node/consensus/validator.key', 'utf8')
const privKey = Buffer.from(privateKeyHex, 'hex')

const custom = Common.forCustomChain(
    'mainnet',
    {
        name: 'polygon-edge',
        networkId: 100,
        chainId: 100
    },
    'petersburg',
);

value = 42


let prosumerContractAddress = process.env.PROSUMER_CONTRACT;

registerValue =  () => {
    var valueArgs = web3.eth.abi.encodeFunctionCall(
        {
            "inputs": [
                {
                    "internalType": "int32",
                    "name": "value",
                    "type": "int32"
                }
            ],
            "name": "registerValue",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
        , [String(value)]);

    var start = Date.now();
    web3.eth.getTransactionCount(addressFrom, "pending").then((txnCount) => {
        var txObject = {
            to: prosumerContractAddress,
            nonce: web3.utils.numberToHex(txnCount),
            gasPrice: web3.utils.numberToHex(1000),
            gasLimit: web3.utils.numberToHex(2000000),
            data: valueArgs
        };

        const tx = eth.Transaction.fromTxData(txObject, { common: custom })
        var rawTx = tx.sign(privKey)
        rawTxHex = "0x" + rawTx.serialize().toString('hex');

        web3.eth.sendSignedTransaction(rawTxHex)
            .on('receipt', receipt => {
                return Date.now() - startTime;
            })
            .catch(error => { console.log('Error: ', error.message); });
    })
}

test = async () => {
    for (let i = 0; i < 100; i++)
        console.log(registerValue())
}

test()