const Web3 = require("web3");
const ProsumerContract = require("./build/contracts/Prosumer.json");
const fs = require('fs');

console.log(process.env.GETH_HOST)

let prosumerContractAddress = process.env.PROSUMER_CONTRACT;

registerValue = async () => {
    let web3 = new Web3(
        new Web3.providers.HttpProvider("http://" + process.env.GETH_HOST + ":8545")
    );


    const prosumerContract = new web3.eth.Contract(
        ProsumerContract.abi,
        prosumerContractAddress
    );


    const accounts = await web3.eth.getAccounts();
    console.log("default account", accounts[0])
    start = Date.now()
    await prosumerContract.methods
        .registerValue(42)
        .send({ from: accounts[0], gas: 10000000 })
        .on('transactionHash', function (hash) {
            console.log(42, hash);
        })
        .on('confirmation', function (confirmationNumber, receipt) {
            now = Date.now();
            console.log(now - start)
            start = now
            exit()
        })
}

registerValue();
console.log('waited')
