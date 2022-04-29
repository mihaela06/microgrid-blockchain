const express = require("express");
const app = express();
const port = process.env.PORT || 5000;
const Web3 = require("web3");
// const contracts = require("./contracts.json");

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// This displays message that the server running and listening to specified port
app.listen(port, () => console.log(`Listening on port ${port}`));
console.log(process.env.GETH_HOST)

// app.post("/register_value", (req, res) => {
//     try {
//       registerValue = async () => {
//         try {
//           let web3 = new Web3(
//             new Web3.providers.HttpProvider("http://" + process.env.GETH_HOST + ":8545")
//           );
  
//           const networkId = await web3.eth.net.getId();
//           const deployedNetwork = SimpleStorageContract.networks[networkId];
//           const contract = new web3.eth.Contract(
//             contracts.SimpleStorageContract.abi,
//             deployedNetwork && deployedNetwork.address
//           );
  
//           // Stores a given value
//           await contract.methods
//             .set(req.body.value)
//             .send({ from: req.body.account });
  
//           // Get the value from the contract to prove it worked.
//           const contractResponse = await contract.methods.get().call();
//           res.send({ registeredValue: "value: " + contractResponse });
//         } catch (error) {
//           console.log(error);
//         }
//       };
  
//       registerValue();
//     } catch (error) {
//       console.error(error);
//     }
//   });
