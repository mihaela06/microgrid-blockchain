FROM node

ENV NODE_ENV=production

WORKDIR /app

RUN apt-get update

RUN apt-get install curl -y

COPY ["package.json", "package-lock.json*", "./"]

RUN npm install --production

COPY . .

ENV GETH_HOST=$GETH_HOST

CMD [ "node", "server.js" ]