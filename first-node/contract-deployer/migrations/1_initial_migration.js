// var Migrations = artifacts.require("./Migrations.sol");

// module.exports = function(deployer) {
//   deployer.deploy(Migrations);
// };

const Web3 = require('web3');

const TruffleConfig = require('../truffle-config.js');

var Migrations = artifacts.require("./Migrations.sol");


module.exports = function(deployer, network, addresses) {
  const config = TruffleConfig.networks[network];

  if (process.env.ACCOUNT_PASSWORD) {
    const web3 = new Web3(new Web3.providers.HttpProvider('http://' + config.host + ':' + config.port));

    console.log('>> Unlocking account ' + config.from);
    console.log(web3);
    web3.eth.personal.unlockAccount(config.from, process.env.ACCOUNT_PASSWORD, 36000);
  }

  console.log('>> Deploying migration');
  deployer.deploy(Migrations);
};