FROM node

WORKDIR /app

RUN npm install -g truffle

RUN truffle init

COPY . .

ARG GETH_HOST=balance_node

RUN sed -i "s/\"host_dummy\"/\"${GETH_HOST}\"/" truffle-config.js

ENTRYPOINT [ "/bin/sh" ]
CMD [ "./entry.sh" ]