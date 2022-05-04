const Web3 = require("web3");
const fs = require('fs');
const GridBalanceContract = require("./build/contracts/GridBalance.json");

const hostname = "host_placeholder"
console.log(hostname);

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

registerProsumer = async () => {
    try {
        let web3 = new Web3(
            new Web3.providers.HttpProvider("http://" + hostname + ":8545")
        );

        const gridContract = new web3.eth.Contract(
            GridBalanceContract.abi,
            "0x416431C9207521e4BB13AA769804222A78112956" //from log contract-deployer, replace with env var
        );

        let txHash = null;

        web3.eth.getAccounts().then((accounts) => {
            console.log("account", accounts[0]);
            web3.eth.getBalance(accounts[0]).then((balance) => { console.log("balance", balance) });
            gridContract.methods.registerProsumer().estimateGas()
                .then(function (gasAmount) {
                    console.log("gas", gasAmount);
                }).catch(function (error) {
                    console.log("error1", error);
                });
            gridContract.methods.registerProsumer().send({ from: accounts[0], gasPrice: 100000 }).on('transactionHash', function (hash) {
                console.log("txhash", hash);
                txHash = hash;
            })
                .on('confirmation', function (confirmationNumber, receipt) {
                    if (confirmationNumber == 5) {
                        console.log("confirmed", confirmationNumber, receipt);
                        gridContract.getPastEvents('ProsumerRegistered', {
                            fromBlock: receipt.blockNumber,
                            toBlock: receipt.blockNumber
                        }, function (error, events) {
                            console.log("error event", error);
                        })
                            .then(function (events) {
                                console.log("events", events) // same results as the optional callback above

                                for (const event of events) {
                                    if (event.transactionHash == txHash) {
                                        console.log(event.returnValues.contractAddress);
                                        fs.writeFile('/app/contract_address.txt', event.returnValues.contractAddress, err => {
                                            if (err) {
                                                console.error(err);
                                            }
                                            // file written successfully
                                        });
                                    }
                                }
                            });
                    }

                })
                // .on('receipt', function (receipt) {
                //     console.log("receipt", receipt);
                // })
                .on('error', function (error, receipt) { // If the transaction was rejected by the network with a receipt, the second parameter will be the receipt.
                    console.log("error2", error, receipt);
                });
        });


    } catch (error) {
        console.log("error3", error);
    }
};

registerProsumer();
