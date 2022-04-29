FROM ethereum/client-go:alltools-stable

COPY node.key .

COPY genesis.json /tmp

COPY password.txt /tmp/password.txt

RUN mkdir -p /root/.ethereum/keystore

COPY UTC--2022-04-09T22-21-30.192595401Z--79b291740fe995bdf192edb78ba7179db7e997a5 /root/.ethereum/keystore

RUN geth init /tmp/genesis.json \
    && rm -f ~/.ethereum/geth/nodekey 

ENV PROSUMERS_NET=${PROSUMERS_NET}

CMD geth \
        --nodekey=node.key \
        --http \
        --http.api db,eth,net,web3,admin,personal,miner,signer:insecure_unlock_protect  \
        --ws \
        --ws.api db,eth,net,web3,admin,personal,miner \
        --ws.origins="*" \
        --ws.addr="0.0.0.0" \
        --networkid 611 \
        --unlock 0 \
        --http.corsdomain="*" \
        --http.addr="0.0.0.0" \
        --http.vhosts=* \
        --password /tmp/password.txt \
        --allow-insecure-unlock \
        --mine \
        --miner.threads=1 \
        # --netrestrict=${PROSUMERS_NET} \
        --netrestrict=172.16.0.0/24 \
        --nat=extip:172.16.0.2 \
        --vmodule=p2p=5,eth=1