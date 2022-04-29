#!/bin/bash

echo ${GETH_HOST}
truffle compile
truffle migrate
# truffle console