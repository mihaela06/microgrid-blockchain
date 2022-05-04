#!/bin/bash

sed -i "s/\"host_placeholder\"/\"${GETH_HOST}\"/" truffle-config.js
echo ${GETH_HOST}
truffle compile --all
truffle migrate
# truffle console