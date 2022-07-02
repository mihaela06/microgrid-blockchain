FROM ethereum/client-go

COPY genesis.json /tmp
COPY node.key .
COPY static-nodes.json /root/.ethereum/geth/static-nodes.json

RUN geth init /tmp/genesis.json \
    && rm -f /root/.ethereum/geth/nodekey 

ENTRYPOINT ["geth"]
