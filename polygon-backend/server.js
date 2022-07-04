const express = require("express");
const app = express();
const port = process.env.PORT || 5000;
const fs = require('fs');
const Web3 = require('web3')
const _Common = require('@ethereumjs/common')
const eth = require('@ethereumjs/tx')

const Common = _Common.default

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.listen(port, () => console.log(`Listening on port ${port}`));

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


app.post("/register_value", (req, res) => {
    try {
        let prosumerContractAddress = process.env.PROSUMER_CONTRACT;
        registerValue = async () => {
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
                , [String(req.body.value)]);

            web3.eth.getTransactionCount(addressFrom).then((txnCount) => {
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
                        console.log("VALUE")
                        for (const log of receipt['logs']) {
                            console.log(log);
                        }
                    })
                    .catch(error => { console.log('Error: ', error.message); });

                res.send({ registeredValue: req.body.value });
            })
        }

        registerValue();
    } catch (error) {
        console.log(error);
        res.send({ registeredValue: -1 });
    }
});

app.post("/register_baseline", (req, res) => {
    try {
        let prosumerContractAddress = process.env.PROSUMER_CONTRACT;
        registerBaseline = async () => {

            let baseline = []
            for (const v of req.body.baseline) {
                baseline.push(parseInt(v))
            }

            var baselineArgs = web3.eth.abi.encodeFunctionCall(
                {
                    "inputs": [
                        {
                            "internalType": "int32[]",
                            "name": "_baselineValues",
                            "type": "int32[]"
                        },
                        {
                            "internalType": "uint16",
                            "name": "_length",
                            "type": "uint16"
                        }
                    ],
                    "name": "actualizeBaseline",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
                , [baseline, baseline.length]);

            web3.eth.getTransactionCount(addressFrom).then((txnCount) => {
                var txObject = {
                    to: prosumerContractAddress,
                    nonce: web3.utils.numberToHex(txnCount),
                    gasPrice: web3.utils.numberToHex(1000),
                    gasLimit: web3.utils.numberToHex(2000000),
                    data: baselineArgs
                };

                const tx = eth.Transaction.fromTxData(txObject, { common: custom })
                var rawTx = tx.sign(privKey)
                rawTxHex = "0x" + rawTx.serialize().toString('hex');

                web3.eth.sendSignedTransaction(rawTxHex)
                    .on('receipt', receipt => {
                        console.log("BASELINE")
                        for (const log of receipt['logs']) {
                            console.log(log);
                            console.log(log['topics'])
                            console.log(log['data'])
                        }
                    })
                    .catch(error => { console.log('Error: ', error.message); });

                res.send({ registeredBaseline: req.body.baseline });
            })
        }

        registerBaseline();
    } catch (error) {
        console.log(error);
        res.send({ registeredBaseline: -1 });
    }
});
