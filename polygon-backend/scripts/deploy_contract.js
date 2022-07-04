const fs = require('fs');
const Web3 = require('web3')
const _Common = require('@ethereumjs/common')
const eth = require('@ethereumjs/tx')

const Common = _Common.default

var rawdata = fs.readFileSync('contracts/GridBalance.json');
var contract = JSON.parse(rawdata);
var bytecode = contract['bytecode'];
var provider = 'http://prosumer' + process.env.NODE_ID + '_polygon_1:8545'

var web3 = new Web3(new Web3.providers.HttpProvider(provider))
web3.transactionConfirmationBlocks = 1;

const addressFrom = fs.readFileSync('nodes/node' + process.env.NODE_ID + '/public_address.txt', 'utf8')
var privateKeyHex = fs.readFileSync('nodes/node' + process.env.NODE_ID + '/consensus/validator.key', 'utf8')
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

web3.eth.getTransactionCount(addressFrom).then((txnCount) => {
    var txObject = {
        nonce: web3.utils.numberToHex(txnCount),
        gasPrice: web3.utils.numberToHex(1000),
        gasLimit: web3.utils.numberToHex(2500000),
        data: bytecode
    };

    const tx = eth.Transaction.fromTxData(txObject, { common: custom })
    var rawTx = tx.sign(privKey)
    rawTxHex = "0x" + rawTx.serialize().toString('hex');

    web3.eth.sendSignedTransaction(rawTxHex)
        .on('receipt', receipt => { console.log(receipt['contractAddress']); })
        .catch(error => { console.log('Error: ', error.message); });
})
    .catch(error => { console.log('Error: ', error.message); });