const Web3 = require('web3')
const _Common = require('@ethereumjs/common')
const fetch = require('node-fetch');
const axios = require("axios");
const fs = require('fs');

const Common = _Common.default

var provider = 'http://prosumer' + process.env.NODE_ID + '_polygon_1:8545'

var web3 = new Web3(new Web3.providers.HttpProvider(provider))
web3.transactionConfirmationBlocks = 1;

filterId = null;


var address = process.env.PROSUMER_CONTRACT

var abi = {
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

var contract = new web3.eth.Contract([abi], address);
var result = contract._encodeEventABI(abi);
var topic = result['topics'][0];

var fromBlock = 'latest'

var processed = []

async function getLogs() {
    fetch(provider, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: '{"jsonrpc":"2.0","method":"eth_getLogs","params":[{"fromBlock" : "' + fromBlock + '", "topics":["' + topic + '"], "address" : "' + address + '"}],"id":1}',
    }).then(res => res.json())
        .then(json => {
            console.log(json)

            try {
                var result = json['result']

                for (const res of result) {
                    var decoded = contract._decodeEventABI.call(abi, res);
                    if (!(processed.includes(res['transactionHash']))) {
                        let DRSignal = decoded['returnValues']['DRSignal']
                        axios.put('http://' + process.env.SMART_HUB_HOST + ":8000/dr", {
                            'signal': DRSignal
                        }).then(
                            response => {
                                console.log(response.statusText);
                                console.log("New DR Signal ", DRSignal);
                            }
                        );
                        blkNo = parseInt(res['blockNumber'], 16) + 1
                        fromBlock = blkNo.toString(16)
                        console.log(res['blockNumber'], fromBlock)
                        processed.push(res['transactionHash'])
                        break;
                    }
                }
            } catch { }

        });
    await new Promise(resolve => setTimeout(resolve, 1000));

    await getLogs();
}

getLogs()