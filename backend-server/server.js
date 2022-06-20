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

index = 0;

app.post("/register_value", (req, res) => {
    let prosumerContractAddress = null;
    try {
        prosumerContractAddress = fs.readFileSync('/app/contract_address.txt', 'utf8');
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
                        .registerValue(req.body.value, index)
                        .send({ from: accounts[0], gas: 40000 })
                        .on('transactionHash', function (hash) {
                            console.log(req.body.value, hash);
                        });

                    const registeredValue = await prosumerContract.methods.getValue(index).call({ from: accounts[0] });
                    res.send({ registeredValue: registeredValue });
                    index++;
                    if (index == 2880)
                        index = 0;


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
