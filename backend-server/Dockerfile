FROM node

ENV NODE_ENV=production

WORKDIR /app

RUN apt-get update

RUN apt-get install curl -y

COPY ["package.json", "package-lock.json*", "./"]

RUN npm install --production

RUN npm install -g truffle

COPY . .

ARG GETH_HOST

RUN sed -i "s/\"host_dummy\"/\"${GETH_HOST}\"/" truffle-config.js

RUN sed -i "s/\"host_dummy\"/\"${GETH_HOST}\"/" prosumer_registration.js

RUN truffle compile

ENV GETH_HOST=$GETH_HOST

CMD [ "node", "server.js" ]