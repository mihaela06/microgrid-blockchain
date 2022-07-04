FROM node

WORKDIR /app

RUN apt-get update

RUN apt-get install curl -y

COPY ["package.json", "package-lock.json*", "./"]

RUN npm install

COPY . .

CMD [ "node", "server.js" ]