const express = require("express");
const app = express();
const port = process.env.PORT || 5000;
const Web3 = require("web3");
const ProsumerContract = require("./build/contracts/Prosumer.json");
const fs = require('fs');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.listen(port, () => console.log(`Listening on port ${port}`));
console.log(process.env.GETH_HOST)

app.post("/register_value", (req, res) => {
    let prosumerContractAddress = null;
    try {
        prosumerContractAddress = process.env.PROSUMER_CONTRACT;
        console.log("prosumerContractAddress", prosumerContractAddress);

        try {
            registerValue = async () => {
                try {
                    let web3 = new Web3(
                        new Web3.providers.HttpProvider("http://" + process.env.GETH_HOST + ":8545")
                    );


                    const prosumerContract = new web3.eth.Contract(
                        ProsumerContract.abi,
                        prosumerContractAddress
                    );

                    console.log("value: ", req.body.value);

                    const accounts = await web3.eth.getAccounts();
                    console.log("default account", accounts[0])
                    await prosumerContract.methods
                        .registerValue(req.body.value)
                        .send({ from: accounts[0], gas: 10000000 })
                        .on('transactionHash', function (hash) {
                            console.log(req.body.value, hash);
                        });
                    res.send({ registeredValue: req.body.value });
                } catch (error) {
                    console.log(error);
                    res.send({ registeredValue: -1 });
                }
            };

            registerValue();
        } catch (error) {
            console.error(error);
            res.send({ registeredValue: -1 });
        }
    } catch (error) {
        console.log(error);
        res.send({ registeredValue: -1 });
    }

});

app.post("/register_baseline", (req, res) => {
    let prosumerContractAddress = null;
    try {
        prosumerContractAddress = process.env.PROSUMER_CONTRACT;
        console.log("prosumerContractAddress", prosumerContractAddress);

        try {
            registerBaseline = async () => {
                try {
                    let web3 = new Web3(
                        new Web3.providers.HttpProvider("http://" + process.env.GETH_HOST + ":8545")
                    );

                    const prosumerContract = new web3.eth.Contract(
                        ProsumerContract.abi,
                        prosumerContractAddress
                    );
                    let baseline = []
                    for (const v of req.body.baseline) {
                        baseline.push(parseInt(v))
                    }
                    console.log("baseline: ", baseline, baseline.length);

                    const accounts = await web3.eth.getAccounts();
                    console.log("default account", accounts[0])
                    await prosumerContract.methods
                        .actualizeBaseline(baseline, baseline.length)
                        .send({ from: accounts[0], gas: 10000000 })
                        .on('transactionHash', function (hash) {
                            console.log(baseline, hash);
                        });

                    res.send({ status: "succes" });
                } catch (error) {
                    console.log(error);
                    res.send({ status: "error" });
                }
            };

            registerBaseline();
        } catch (error) {
            console.error(error);
            res.send({ status: "error" });
        }
    } catch (error) {
        console.log(error);
        res.send({ status: "error" });
    }

});

app.post("/register_hash", (req, res) => {
    let prosumerContractAddress = null;
    try {
        prosumerContractAddress = process.env.PROSUMER_CONTRACT;
        console.log("prosumerContractAddress", prosumerContractAddress);

        try {
            registerHash = async () => {
                try {
                    let web3 = new Web3(
                        new Web3.providers.HttpProvider("http://" + process.env.GETH_HOST + ":8545")
                    );

                    const prosumerContract = new web3.eth.Contract(
                        ProsumerContract.abi,
                        prosumerContractAddress
                    );
                    
                    let new_hash = "0x" + req.body.hash
                    console.log("hash: ", new_hash);

                    const accounts = await web3.eth.getAccounts();
                    console.log("default account", accounts[0])
                    await prosumerContract.methods
                        .registerHash(new_hash)
                        .send({ from: accounts[0], gas: 10000000 })
                        .on('transactionHash', function (txhash) {
                            console.log(new_hash, txhash);
                        });

                    res.send({ status: "succes" });
                } catch (error) {
                    console.log(error);
                    res.send({ status: "error" });
                }
            };

            registerHash();
        } catch (error) {
            console.error(error);
            res.send({ status: "error" });
        }
    } catch (error) {
        console.log(error);
        res.send({ status: "error" });
    }

});

