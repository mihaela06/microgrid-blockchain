const fs = require('fs');
const Web3 = require('web3')
const _Common = require('@ethereumjs/common')
const eth = require('@ethereumjs/tx')

const Common = _Common.default

var rawdata = fs.readFileSync('contracts/GridBalance.json');
var contract = JSON.parse(rawdata);
var bytecode = contract['bytecode'];
var provider = 'http://prosumer1_polygon_1:8545'

var web3 = new Web3(new Web3.providers.HttpProvider(provider))
web3.transactionConfirmationBlocks = 1;

const addressFrom = fs.readFileSync('nodes/node1/public_address.txt', 'utf8')
var privateKeyHex = fs.readFileSync('nodes/node1/consensus/validator.key', 'utf8')
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

let abi = {
    "anonymous": false,
    "inputs": [
        {
            "indexed": true,
            "internalType": "address",
            "name": "prosumerAddress",
            "type": "address"
        },
        {
            "indexed": false,
            "internalType": "int32[12]",
            "name": "DRSignal",
            "type": "int32[12]"
        },
        {
            "indexed": false,
            "internalType": "uint32",
            "name": "DRLength",
            "type": "uint32"
        }
    ],
    "name": "registeredDRSignal",
    "type": "event"
}

let address = '0xc01C1e9b44808e79CE8457900312d99c1c705E13'
var contract = new web3.eth.Contract([abi], address);
var result = contract._encodeEventABI(abi);

console.log(result)
