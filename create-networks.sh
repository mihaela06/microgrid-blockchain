#!/bin/bash

## Arguments parsing

usage() {
  cat << EOF >&2
Usage: $0 [-n <number>]

-n <number>: number of prosumers in network
EOF
  exit 1
}

while getopts ":n:" o; do
  case "${o}" in
    n) 
        n=$OPTARG
        ;;
    *) 
        usage
        ;;
  esac
done
shift "$((OPTIND - 1))"

if [ -z "${n}" ] ; then
    usage
fi


function send_curl_request() {
  # $1 - container from which the request is sent
  # $2 - geth destination hostname:port
  # $3 - json filename

  docker exec $1 curl -s --location $2 --header 'Content-Type: application/json' -d "@"$3
}

function curl_container_request() {
  # $1 - destination hostname:port
  # $2 - json filename
  # $i - keywords to be replaced
  # $i+1 - array of keywords to replace with

  mkdir tmp
  cp $2 tmp/temp_req.json
  destination=$1
  shift
  shift

  while test $# -gt 0
  do
    sed -i "s/\"${1}\"/\"${2}\"/" tmp/temp_req.json
    shift
    shift
  done

  cat tmp/temp_req.json

  docker run --rm -it --network prosumers-net \
        --mount type=bind,source="$(pwd)"/tmp,target=/requests \
        curlimages/curl curl --location $destination \
        --header 'Content-Type: application/json' \
        -d @/requests/temp_req.json

  rm tmp/temp_req.json
  rm -rf tmp
}


balance_address="0x79b291740FE995bdF192edB78Ba7179DB7e997A5"

## Cleanup

# Stop all containers
docker stop `docker ps -qa` 2> /dev/null

# Remove all containers
docker rm `docker ps -qa` 2> /dev/null

# Remove all images
# docker rmi -f `docker images -qa ` 2> /dev/null

# Remove all volumes
docker volume rm $(docker volume ls -q) 2> /dev/null

# Remove all networks
docker network rm `docker network ls -q` 2> /dev/null


## Create environment

# Create main network

export PROSUMERS_NET="172.16.0.0/24"
export PROSUMERS_NET_NAME="prosumers-net"
docker network create --subnet="$PROSUMERS_NET" "$PROSUMERS_NET_NAME"

# Create bootnode

docker build first-node/bootnode -t bootnode

docker container run --name balance_node --network "$PROSUMERS_NET_NAME" -d bootnode

# Create prosumer clusters

for ((i = 1 ; i <= n ; i++)); do
  echo "Adding prosumer #$i"
  export PROSUMER_SUBNET="192.168.$i.0/28"
  export GETH_IP="172.16.0.$(($i + 2))"
  docker-compose -f docker-compose-geth.yaml -p prosumer"$i" up -d
done

# Create new accounts for each prosumer

declare -a prosumer_accounts 

for ((i = 1 ; i <= n ; i++)); do
  echo "Creating prosumer #$i account"
  password="parola"
  host=$"prosumer${i}_geth_1:8545"
  new_account=$(curl_container_request  "$host" "./backend-server/requests/create_account.json" | grep "0x[a-zA-Z0-9]*" -o)
  echo "Created prosumer #$i account $new_account"
  prosumer_accounts+=($new_account)
  # docker exec "prosumer${i}_backend-server_1" curl -s --location $host --header 'Content-Type: application/json' -d @./requests/create_account.json
done

# Send initial balance to every prosumer

for acc in "${prosumer_accounts[@]}"
do
   : 
   echo $acc
   curl_container_request balance_node:8545 ./backend-server/requests/send_tokens.json from_placeholder $balance_address to_placeholder $acc value_placeholder 0x10000000000
done

# Unlock accounts and start mining in main account

for ((i = 1 ; i <= n ; i++)); do
  curl_container_request "prosumer${i}_geth_1:8545"  ./backend-server/requests/unlock_account.json address_placeholder ${prosumer_accounts[$((i-1))]} password_placeholder parola
  curl_container_request "prosumer${i}_geth_1:8545"  ./backend-server/requests/set_etherbase.json address_placeholder ${prosumer_accounts[$((i-1))]}
  curl_container_request "prosumer${i}_geth_1:8545"  ./backend-server/requests/start_mining.json

done


# Deploy main contract for grid balance

docker build first-node/contract-deployer -t contract-deployer --build-arg GETH_HOST=balance_node

docker container run --name contract-deployer --network "$PROSUMERS_NET_NAME" contract-deployer

# Register prosumer

docker image rm backend-server

for ((i = 1 ; i <= n ; i++)); do
  mod=$(($((i % 3)) + 1))
  export DATA_FILE="$mod.csv"
  export GETH_HOST="prosumer${i}_geth_1" 
  echo $GETH_HOST
  docker-compose -f docker-compose-backend.yaml -p prosumer"$i" build
  docker-compose -f docker-compose-backend.yaml -p prosumer"$i" up -d
  docker network connect "prosumer${i}_prosumer-subnet" "prosumer${i}_smart-meter_1"
  docker network connect "prosumer${i}_prosumer-subnet" "prosumer${i}_backend-server_1"
  docker exec "prosumer${i}_backend-server_1" node prosumer_registration.js
done
