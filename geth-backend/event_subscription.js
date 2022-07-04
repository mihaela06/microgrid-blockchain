const Web3 = require("web3");
const fs = require('fs');
const GridBalanceContract = require("./build/contracts/GridBalance.json");
const ProsumerContract = require("./build/contracts/Prosumer.json");
const axios = require("axios");

const hostname = process.env.GETH_HOST
console.log("Geth hostname: ", hostname);

const XHR = require("xhr2-cookies").XMLHttpRequest;
XHR.prototype._onHttpRequestError = function (request, error) {
    if (this._request !== request) {
        return;
    }
    console.log(error, "request");
    this._setError();
    request.abort();
    this._setReadyState(XHR.DONE);
    this._dispatchProgress("error");
    this._dispatchProgress("loadend");
};

eventSubscription = async () => {
    try {
        let web3 = new Web3(
            new Web3.providers.WebsocketProvider("ws://" + hostname + ":8546")
        );

        const gridContract = new web3.eth.Contract(
            GridBalanceContract.abi,
            process.env.GRID_CONTRACT
        );

        const prosumerContract = new web3.eth.Contract(
            ProsumerContract.abi,
            process.env.PROSUMER_CONTRACT
        );

        prosumerContract.events.registeredDRSignal({
            fromBlock: 'latest'
        }, function (error, event) {
            console.log(event["returnValues"]["DRSignal"]);
            var DRSignal = event["returnValues"]["DRSignal"];
            axios.put('http://' + process.env.SMART_HUB_HOST + ":8000/dr", {
                'signal': DRSignal
            }).then(
                response => {
                    console.log(response.statusText);
                    console.log("New DR Signal ", DRSignal);
                }
            );
        })
        // .on("connected", function (subscriptionId) {
        //     console.log(subscriptionId);
        // })
        // .on('data', function (event) {
        //     console.log(event["returnValues"])
        // console.log("data", event); // same results as the optional callback above
        // })
        // .on('changed', function (event) {
        //     // remove event from local database
        //     console.log("changed", event);
        // })
        // .on('error', function (error, receipt) { // If the transaction was rejected by the network with a receipt, the second parameter will be the receipt.
        //     console.log("error", error, receipt);
        // });

    } catch (error) {
        console.log("error3", error);
    }
};

eventSubscription();
