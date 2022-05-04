FROM node

WORKDIR /app

RUN npm install -g truffle

RUN truffle init

ENV GETH_HOST=balance_node

CMD [ "/bin/sh", "./entry.sh" ]