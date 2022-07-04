#!/bin/bash
#
# Automate microgrid simulation using Docker
# Bash script template from: https://github.com/ralish/bash-script-template/blob/main/template.sh (MIT License)

# Enable xtrace if the DEBUG environment variable is set
if [[ ${DEBUG-} =~ ^1|yes|true$ ]]; then
  set -o xtrace # Trace the execution of the script (debug)
fi

# Only enable these shell behaviours if the script is not being sourced
# Approach via: https://stackoverflow.com/a/28776166/8787985
# if ! (return 0 2>/dev/null); then
#   set -o errexit  # Exit on most errors (see the manual)
#   set -o nounset  # Disallow expansion of unset variables
#   set -o pipefail # Use last non-zero exit code in a pipeline
# fi

# Enable errtrace or the error trap handler will not work as expected
# set -o errtrace # Ensure the error trap handler is inherited

# DESC: Usage help
# ARGS: None
# OUTS: None
function script_usage() {
  cat <<EOF
Usage: $0 [-p <number>]

     -p|--prosumers             Number of prosumers used in simulation (defaults to 2)
     -h|--help                  Displays help
     -v|--verbose               Displays verbose output
     -s|--static                Runs static, preconfigured simulation
     -t|--timestamp             Simulation start time (UNIX timestamp)
     -c|--consensus             Consensus algorithm (ethash, clique)
     -b|--blockchain            Blockchain platform (ethereum, polygon)
    -nc|--no-colour             Disables colour output
EOF
}

# DESC: Variable defaults setter
# ARGS: None
# OUTS: Variables with default values set
function set_defaults() {
  PROSUMERS_NO=2
  export readonly PROSUMERS_NET="172.16.0.0/24"
  export readonly PROSUMERS_NET_NAME="prosumers-net"
  export readonly NETWORK_ID=611
  export readonly HOST_IP="10.13.105.1"
  local prefix=${PROSUMERS_NET%%/*}
  prefix=${prefix::-1}
  export readonly BOOTNODE_IP="${prefix}"2 # 172.16.0.2
  readonly balance_address="0x79b291740FE995bdF192edB78Ba7179DB7e997A5"
  export readonly PROSUMERS_IDS=(1 2 6 9 15 16 17 18)
  export readonly START_TIMESTAMP=1589500800
  export readonly DYNAMIC=true
  export readonly CONSENSUS=ethash
  export readonly BLOCKCHAIN=ethereum
}

# DESC: Parameter parser
# ARGS: $@ (optional): Arguments provided to the script
# OUTS: Variables indicating command-line parameters and options
function parse_params() {
  local param
  set_defaults
  while [[ $# -gt 0 ]]; do
    param="$1"
    shift
    case $param in
    -h | --help)
      script_usage
      exit 0
      ;;
    -v | --verbose)
      verbose=true
      ;;
    -s | --static)
      export readonly DYNAMIC=false
      ;;
    -nc | --no-colour)
      no_colour=true
      ;;
    -p | --prosumers)
      readonly PROSUMERS_NO=$1
      shift
      ;;
    -c | --consensus)
      case "$1" in
      'ethash')
        export readonly CONSENSUS='ethash'
        verbose_print "Platform Ethereum with consensus algorithm ethash was selected."
        export readonly BLOCKCHAIN=ethereum
        ;;
      'clique')
        export readonly CONSENSUS='clique'
        verbose_print "Platform Ethereum with consensus algorithm clique was selected."
        export readonly BLOCKCHAIN=ethereum
        ;;
      'ibft')
        export readonly CONSENSUS='ibft'
        verbose_print "Platform Polygon with consensus algorithm IBFT was selected."
        export readonly BLOCKCHAIN=polygon
        ;;
      *)
        script_exit "Invalid consensus algorithm was provided: $1. Accepting: ethash, clique, ibft." 1
        ;;
      esac
      shift
      ;;
    -t | --timestamp)
      export readonly START_TIMESTAMP=$1
      shift
      ;;
    *)
      script_exit "Invalid parameter was provided: $param" 1
      ;;
    esac
  done
}

# DESC: Create a Curl container to send requests to a certain host in a specified network
# ARGS: $1    (required): Destination address (hostname:port)
#       $2    (required): Name of JSON file containing request template
#       $3    (required): Name of Docker network
#       $i    (optional): Placeholder word to be replaced in template
#       $i+1  (optional): Word to replace the placeholder with
# OUTS: None
function curl_container_request() {
  mkdir tmp
  cp $2 tmp/temp_req.json
  local destination=$1
  local network=$3
  shift
  shift
  shift

  while test $# -gt 0; do
    sed -i "s/\"${1}\"/\"${2}\"/" tmp/temp_req.json
    shift
    shift
  done

  docker run --rm -it --network $network --mount type=bind,source="$PWD/tmp",target=/requests curlimages/curl curl --location $destination --header 'Content-Type: application/json' -d @/requests/temp_req.json

  rm tmp/temp_req.json
  rm -rf tmp
}

# DESC: Docker cleanup
# ARGS: None
# OUTS: None
function docker_cleanup() {
  verbose_print "Docker environment is getting cleaned up" $bg_blue$ta_bold

  # Stop all containers
  verbose_print "Stopping containers..." $bg_blue$ta_bold

  docker stop $(docker ps -qa) 2>/dev/null

  # Remove all containers
  verbose_print "Removing containers..." $bg_blue$ta_bold

  docker rm $(docker ps -qa) 2>/dev/null

  # Remove all images
  verbose_print "Removing images..." $bg_blue$ta_bold

  # docker rmi -f $(docker images -qa) 2>/dev/null

  # Remove all volumes
  verbose_print "Removing volumes..." $bg_blue$ta_bold

  docker volume rm $(docker volume ls -q) 2>/dev/null

  # Remove all networks
  verbose_print "Removing networks..." $bg_blue$ta_bold

  docker network rm $(docker network ls -q) 2>/dev/null
}

# DESC: Creating Docker logging services
# ARGS: None
# OUTS: None
function docker_logging() {
  verbose_print "Creating Docker logging services" $bg_blue$ta_bold

  docker-compose -f "${PWD}"/logging/docker-compose.yml -f "${PWD}"/logging/extensions/logspout/logspout-compose.yml up -d

  return
}

# DESC: Creating Docker main network
# ARGS: None
# OUTS: None
function docker_main_network() {
  verbose_print "Creating Docker main network that will be interconnecting Blockchain nodes" $bg_blue$ta_bold

  export PROSUMERS_NET
  export PROSUMERS_NET_NAME
  docker network create --subnet="${PROSUMERS_NET}" "$PROSUMERS_NET_NAME"
  return
}

# DESC: Creating Blockchain bootnode
# ARGS: None
# OUTS: None
function docker_bootnode() {
  if [[ $BLOCKCHAIN == "polygon"* ]]; then
    return
  fi

  verbose_print "Creating Blockchain bootnode" $bg_blue$ta_bold

  cp "${PWD}/first-node/bootnode/genesis ${CONSENSUS}.json" "${PWD}/first-node/bootnode/genesis.json"

  cp "${PWD}/first-node/bootnode/genesis.json" "${PWD}/geth-client/genesis.json"

  docker build \
    --build-arg PROSUMERS_NET="${PROSUMERS_NET}" \
    --build-arg BOOTNODE_IP="${BOOTNODE_IP}" \
    --build-arg NETWORK_ID="${NETWORK_ID}" \
    first-node/bootnode -t bootnode
  docker container run --name balance_node --network "$PROSUMERS_NET_NAME" -d bootnode
}

# DESC: Creating Geth prosumer clusters
# ARGS: None
# OUTS: None
function geth_prosumer_clusters() {
  verbose_print "Creating prosumer clusters with a Geth node each" $bg_blue$ta_bold

  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    verbose_print "Adding prosumer #$i" $bg_blue$ta_bold
    export readonly PROSUMER_SUBNET="192.168.$i.0/28"
    export readonly GETH_IP="172.16.0.$(($i + 2))"
    docker-compose -f docker-compose-geth.yaml -p prosumer"$i" up -d --build
  done
}

# DESC: Creating Polygon prosumer clusters
# ARGS: None
# OUTS: None
function polygon_prosumer_clusters() {
  verbose_print "Creating prosumer clusters with a Polygon node each" $bg_blue$ta_bold

  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    :
    sudo rm -rf polygon/node${i}
    mkdir polygon/node${i}
    output=$(docker run --rm -v ${PWD}/polygon/node${i}:/node${i} 0xpolygon/polygon-edge secrets init --data-dir /node${i})
    public_key=$(echo ${output} | egrep '0x([a-fA-F0-9]){40}' -o)
    public_keys+=(${public_key})
    echo -n $public_key >>polygon/node${i}/public_address.txt
    node_id=($(echo ${output} | egrep '([a-zA-Z0-9]){53}' -o))
    node_ids+=(${node_id})
    bootnodes+=("/ip4/172.16.0."$((i + 2))"/tcp/1478/p2p/${node_id}")
    sudo chmod -R +r polygon/node${i}
  done

  rm -rf polygon/genesis
  mkdir -p polygon/genesis
  command="docker run --rm -v ${PWD}/polygon/genesis:/genesis 0xpolygon/polygon-edge genesis --dir /genesis/genesis.json --block-gas-limit 1000000000 --consensus ibft "

  for public_key in "${public_keys[@]}"; do
    :
    command+="--ibft-validator=${public_key} "
  done

  for bootnode in "${bootnodes[@]}"; do
    :
    command+="--bootnode ${bootnode} "
  done

  for public_key in "${public_keys[@]}"; do
    :
    command+="--premine=${public_key}:1000000000000000000000 "
  done

  eval "${command}"

  export readonly GENESIS_DIR=${PWD}/polygon/genesis
  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    :
    verbose_print "Adding prosumer #$i" $bg_blue$ta_bold
    export readonly POLYGON_IP="172.16.0.$(($i + 2))"
    export readonly PROSUMER_SUBNET="192.168.$i.0/28"
    export readonly NODE_DIR=${PWD}/polygon/node${i}
    docker-compose -f docker-compose-polygon.yaml -p prosumer"$i" up -d --build
  done
}

# DESC: Creating prosumer clusters
# ARGS: None
# OUTS: None
function docker_prosumer_clusters() {
  if [[ $BLOCKCHAIN == "polygon"* ]]; then
    polygon_prosumer_clusters
  else
    geth_prosumer_clusters
  fi
}

# DESC: Creating monitoring services
# ARGS: None
# OUTS: None
function docker_monitoring() {
  verbose_print "Creating monitoring microservices" $bg_blue$ta_bold

  wget https://grafana.com/api/dashboards/14053/revisions/1/download -O "$PWD"/monitoring/grafana/geth.json

  sed -i "s/\${DS_PROMETHEUS}/Prometheus/" "$PWD"/monitoring/grafana/geth.json
  sed -i "s/\${VAR_JOB}/geth/" "$PWD"/monitoring/grafana/geth.json

  cp "$PWD"/monitoring/prometheus/prometheus-template.yml "$PWD"/monitoring/prometheus/prometheus.yml

  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    if [[ $BLOCKCHAIN == "polygon"* ]]; then
      export readonly HOSTNAME="prosumer${i}_polygon_1:5001"
    else
      export readonly HOSTNAME="prosumer${i}_geth_1:6060"
    fi
    echo -e "          - ${HOSTNAME}" >>"$PWD"/monitoring/prometheus/prometheus.yml
  done

  docker-compose -f docker-compose-monitoring.yaml -p monitoring up -d --build
}

# DESC: Creating accounts for each prosumer with initial balance
# ARGS: None
# OUTS: None
function create_prosumer_accounts() {
  if [[ $BLOCKCHAIN == "polygon"* ]]; then
    return
  fi

  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    verbose_print "Creating prosumer #$i account" $bg_blue$ta_bold
    # TODO password management
    password="parola"
    host=$"prosumer${i}_geth_1:8545"
    new_account=$(curl_container_request "$host" "./geth-backend/requests/create_account.json" "$PROSUMERS_NET_NAME" | grep "0x[a-zA-Z0-9]*" -o)
    new_enode=$(curl_container_request "$host" "./geth-backend/requests/node_info.json" "$PROSUMERS_NET_NAME" | egrep "enr:-([a-zA-Z_0-9]*-?)*" -o)
    verbose_print "Created prosumer #$i account $new_account" $bg_blue$ta_bold
    verbose_print "New enode at $new_enode" $bg_blue$ta_bold
    prosumer_accounts+=($new_account)
    prosumer_enodes+=($new_enode)
  done

  for acc in "${prosumer_accounts[@]}"; do
    :
    verbose_print "Sending initial balance to prosumer account $acc" $bg_blue$ta_bold

    curl_container_request balance_node:8545 ./geth-backend/requests/send_tokens.json $PROSUMERS_NET_NAME from_placeholder $balance_address to_placeholder $acc value_placeholder 0x100000000000000000000

  done

  verbose_print "Unlock accounts and start mining in each main account" $bg_blue$ta_bold

  if [[ $CONSENSUS == "clique"* ]]; then
    for acc in "${prosumer_accounts[@]}"; do
      :
      verbose_print "Proposing account $acc as signer" $bg_blue$ta_bold
      curl_container_request "balance_node:8545" ./geth-backend/requests/add_signer.json "${PROSUMERS_NET_NAME}" address_placeholder $acc
    done
  fi

  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    curl_container_request "prosumer${i}_geth_1:8545" ./geth-backend/requests/unlock_account.json "${PROSUMERS_NET_NAME}" address_placeholder ${prosumer_accounts[$((i - 1))]} password_placeholder parola
    curl_container_request "prosumer${i}_geth_1:8545" ./geth-backend/requests/set_etherbase.json "${PROSUMERS_NET_NAME}" address_placeholder ${prosumer_accounts[$((i - 1))]}
    curl_container_request "prosumer${i}_geth_1:8545" ./geth-backend/requests/start_mining.json "${PROSUMERS_NET_NAME}"

    for enode in "${prosumer_enodes[@]}"; do
      :
      verbose_print "Adding peer with enode ${enode} to prosumer${i}" $bg_blue$ta_bold
      curl_container_request "prosumer${i}_geth_1:8545" ./geth-backend/requests/add_peer.json "${PROSUMERS_NET_NAME}" enode_placeholder $enode
    done
    if [[ $CONSENSUS == "clique"* ]]; then

      for acc in "${prosumer_accounts[@]}"; do
        :
        verbose_print "Proposing account $acc as signer" $bg_blue$ta_bold
        curl_container_request "prosumer${i}_geth_1:8545" ./geth-backend/requests/add_signer.json "${PROSUMERS_NET_NAME}" address_placeholder $acc
      done
    fi
  done
}

# DESC: Deploy the grid balance smart contract to the Ethereum blockchain
# ARGS: None
# OUTS: None
function geth_deploy_grid_balance_contract() {
  verbose_print "Deploying grid balance smart contract" $bg_blue$ta_bold

  docker build first-node/contract-deployer -t contract-deployer

  docker container run --name contract-deployer -v "$PWD"/first-node/contract-deployer:/app --network "$PROSUMERS_NET_NAME" -e GETH_HOST=balance_node contract-deployer

  export readonly GRID_CONTRACT=$(docker logs contract-deployer 2>&1 | grep "contract address:" | egrep 0x[a-fA-F0-9]{40} -o | sed -n 2p)

  echo $GRID_CONTRACT

  verbose_print "Deployed grid contract at address" $GRID_CONTRACT

  cp -r "${PWD}"/first-node/contract-deployer/build/contracts/ "${PWD}"/geth-backend/build/
}

# DESC: Deploy the grid balance smart contract to the Polygon blockchain
# ARGS: None
# OUTS: None
function polygon_deploy_grid_balance_contract() {
  verbose_print "Deploying grid balance smart contract" $bg_blue$ta_bold

  docker build polygon-backend/ -t polygon-backend

  GRID_CONTRACT=$(docker container run --rm --name polygon-deployer -v "$PWD"/polygon:/app/nodes -v "$PWD"/polygon-backend/scripts:/app/scripts -v "$PWD"/first-node/contract-deployer/build/contracts:/app/contracts --network "$PROSUMERS_NET_NAME" -e NODE_ID=1 polygon-backend node scripts/deploy_contract.js)

  export readonly GRID_CONTRACT
}

# DESC: Deploy the grid balance smart contract from the bootnode
# ARGS: None
# OUTS: None
function deploy_grid_balance_contract() {
  if [[ $BLOCKCHAIN == "polygon"* ]]; then
    polygon_deploy_grid_balance_contract
  else
    geth_deploy_grid_balance_contract
  fi
}

# DESC: Register each prosumer in microgrid through contract deployment
# ARGS: None
# OUTS: None
function deploy_prosumer_contract() {
  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    MONGO_EXPRESS_PORT=8090
    SMART_HUB_PORT=8000
    DATA_STREAM_PORT=8060
    FRONTEND_PORT=8030

    verbose_print "Deploying prosumer smart contract for prosumer  #$i" $bg_blue$ta_bold

    export GETH_HOST="prosumer${i}_geth_1"
    export MONGO_HOST="prosumer${i}_mongo_1"
    export SMART_HUB_HOST="prosumer${i}_smart-hub_1"
    export DATA_STREAM_HOST="prosumer${i}_data-stream_1"
    export NODE_ID=${i}

    export MONGO_EXPRESS_PORT=$((MONGO_EXPRESS_PORT + i))
    export SMART_HUB_PORT=$((SMART_HUB_PORT + i))
    export FRONTEND_PORT=$((FRONTEND_PORT + i))
    export DATA_STREAM_PORT=$((DATA_STREAM_PORT + i))

    export PROSUMER_ID=${PROSUMERS_IDS[i]}

    if [[ $BLOCKCHAIN == "polygon"* ]]; then
      
      export BACKEND_HOST="prosumer${i}_polygon-backend_1"
      export PROSUMER_CONTRACT=$(docker container run --rm --name prosumer${i}_prosumer_registration_1 -v "$PWD"/polygon:/app/nodes -v "$PWD"/polygon-backend/scripts:/app/scripts -v "$PWD"/first-node/contract-deployer/build/contracts:/app/contracts --network "$PROSUMERS_NET_NAME" -e NODE_ID=${NODE_ID} -e PROSUMER_THRESHOLD=10 -e GRID_CONTRACT=${GRID_CONTRACT} polygon-backend node scripts/register_prosumer.js)

    else
      
      export BACKEND_HOST="prosumer${i}_geth-backend_1"
      export PROSUMER_CONTRACT=$(docker run --network prosumer${i}_default -e GETH_HOST=${GETH_HOST} -e GRID_CONTRACT=${GRID_CONTRACT} -e NODE_ID=${i} --name prosumer${i}_prosumer_registration_1 geth-backend node prosumer_registration.js)

    fi

    verbose_print "Prosumer registered with contract at address ${PROSUMER_CONTRACT}"

    docker-compose -f docker-compose-hub.yaml -p prosumer"$i" --profile ${BLOCKCHAIN} up -d --build

    docker stop "prosumer${i}_simulation_1"

  done
}

# DESC: Start each prosumer simulation container
# ARGS: None
# OUTS: None
function start_simulation() {
  for ((i = 1; i <= PROSUMERS_NO; i++)); do
    docker start "prosumer${i}_simulation_1"
  done
}

# DESC: Main control flow
# ARGS: $@ (optional): Arguments provided to the script
# OUTS: None
function main() {
  # trap script_trap_err ERR
  # trap script_trap_exit EXIT

  script_init "$@"
  parse_params "$@"
  colour_init

  docker_cleanup
  docker_logging
  docker_main_network
  docker_bootnode
  docker_prosumer_clusters
  docker_monitoring
  create_prosumer_accounts
  deploy_grid_balance_contract
  deploy_prosumer_contract
  start_simulation
}

# shellcheck source=functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/functions.sh"

# Invoke main with args if not sourced
# Approach via: https://stackoverflow.com/a/28776166/8787985
# Bash allows return statements only from functions and, in a script's top-level scope, only if the script is sourced.
if ! (return 0 2>/dev/null); then
  main "$@"
fi
