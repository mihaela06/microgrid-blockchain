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
    -nc|--no-colour             Disables colour output
EOF
}

# DESC: Variable defaults setter
# ARGS: None
# OUTS: Variables with default values set
function set_defaults() {
  prosumers_no=2
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
      readonly prosumers_no=$1
      shift
      ;;
    -c | --consensus)
      case "$1" in
      'ethash')
        export readonly CONSENSUS='ethash'
        ;;
      'clique')
        export readonly CONSENSUS='clique'
        ;;
      *)
        script_exit "Invalid consensus algorithm was provided: $param" 1
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

# DESC: Creating prosumer clusters
# ARGS: None
# OUTS: None
function docker_prosumer_clusters() {
  verbose_print "Creating prosumer clusters with a Blockchain node each" $bg_blue$ta_bold
  # TODO create static-nodes.json file from output parsing
  for ((i = 1; i <= prosumers_no; i++)); do
    verbose_print "Adding prosumer #$i" $bg_blue$ta_bold
    export readonly PROSUMER_SUBNET="192.168.$i.0/28"
    export readonly GETH_IP="172.16.0.$(($i + 2))"
    docker-compose -f docker-compose-geth.yaml -p prosumer"$i" up -d --build
  done
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

  for ((i = 1; i <= prosumers_no; i++)); do
    export readonly GETH_HOSTNAME="prosumer${i}_geth_1:6060"
    echo -e "          - ${GETH_HOSTNAME}" >>"$PWD"/monitoring/prometheus/prometheus.yml
  done

  docker-compose -f docker-compose-monitoring.yaml -p monitoring up -d --build
}

# DESC: Creating logging services
# ARGS: None
# OUTS: None
function docker_logging() {
  verbose_print "Creating logging microservices" $bg_blue$ta_bold

  docker-compose -f docker-compose-logging.yaml up -d --build
}

# DESC: Creating accounts for each prosumer with initial balance
# ARGS: None
# OUTS: None
function create_prosumer_accounts() {
  for ((i = 1; i <= prosumers_no; i++)); do
    verbose_print "Creating prosumer #$i account" $bg_blue$ta_bold
    # TODO password management
    password="parola"
    host=$"prosumer${i}_geth_1:8545"
    new_account=$(curl_container_request "$host" "./backend-server/requests/create_account.json" "$PROSUMERS_NET_NAME" | grep "0x[a-zA-Z0-9]*" -o)
    new_enode=$(curl_container_request "$host" "./backend-server/requests/node_info.json" "$PROSUMERS_NET_NAME" | egrep "enr:-([a-zA-Z_0-9]*-?)*" -o)
    verbose_print "Created prosumer #$i account $new_account" $bg_blue$ta_bold
    verbose_print "New enode at $new_enode" $bg_blue$ta_bold
    prosumer_accounts+=($new_account)
    prosumer_enodes+=($new_enode)
  done

  for acc in "${prosumer_accounts[@]}"; do
    :
    verbose_print "Sending initial balance to prosumer account $acc" $bg_blue$ta_bold

    curl_container_request balance_node:8545 ./backend-server/requests/send_tokens.json $PROSUMERS_NET_NAME from_placeholder $balance_address to_placeholder $acc value_placeholder 0x100000000000000000000

  done

  verbose_print "Unlock accounts and start mining in each main account" $bg_blue$ta_bold

  for acc in "${prosumer_accounts[@]}"; do
    :
    verbose_print "Proposing account $acc as signer" $bg_blue$ta_bold
    curl_container_request "balance_node:8545" ./backend-server/requests/add_signer.json "${PROSUMERS_NET_NAME}" address_placeholder $acc
  done

  for ((i = 1; i <= prosumers_no; i++)); do
    curl_container_request "prosumer${i}_geth_1:8545" ./backend-server/requests/unlock_account.json "${PROSUMERS_NET_NAME}" address_placeholder ${prosumer_accounts[$((i - 1))]} password_placeholder parola
    curl_container_request "prosumer${i}_geth_1:8545" ./backend-server/requests/set_etherbase.json "${PROSUMERS_NET_NAME}" address_placeholder ${prosumer_accounts[$((i - 1))]}
    curl_container_request "prosumer${i}_geth_1:8545" ./backend-server/requests/start_mining.json "${PROSUMERS_NET_NAME}"

    for enode in "${prosumer_enodes[@]}"; do
      :
      verbose_print "Adding peer with enode ${enode} to prosumer${i}" $bg_blue$ta_bold
      curl_container_request "prosumer${i}_geth_1:8545" ./backend-server/requests/add_peer.json "${PROSUMERS_NET_NAME}" enode_placeholder $enode
    done

    for acc in "${prosumer_accounts[@]}"; do
      :
      verbose_print "Proposing account $acc as signer" $bg_blue$ta_bold
      curl_container_request "prosumer${i}_geth_1:8545" ./backend-server/requests/add_signer.json "${PROSUMERS_NET_NAME}" address_placeholder $acc
    done

  done
}

# DESC: Deploy the grid balance smart contract from the bootnode
# ARGS: None
# OUTS: None
function deploy_grid_balance_contract() {
  verbose_print "Deploying grid balance smart contract" $bg_blue$ta_bold

  docker build first-node/contract-deployer -t contract-deployer

  docker container run --name contract-deployer -v "$PWD"/first-node/contract-deployer:/app --network "$PROSUMERS_NET_NAME" -e GETH_HOST=balance_node contract-deployer

  export readonly GRID_CONTRACT=$(docker logs contract-deployer 2>&1 | grep "contract address:" | egrep 0x[a-fA-F0-9]{40} -o | sed -n 2p)

  echo $GRID_CONTRACT

  verbose_print "Deployed grid contract at address" $GRID_CONTRACT

  cp -r "${PWD}"/first-node/contract-deployer/build/contracts/ "${PWD}"/backend-server/build/

}

# DESC: Register each prosumer in microgrid through contract deployment
# ARGS: None
# OUTS: None
function deploy_prosumer_contract() {
  for ((i = 1; i <= prosumers_no; i++)); do
    MONGO_EXPRESS_PORT=8090
    SMART_HUB_PORT=8000
    DATA_STREAM_PORT=8060
    FRONTEND_PORT=8030

    verbose_print "Deploying prosumer smart contract for prosumer  #$i" $bg_blue$ta_bold

    # TODO replace smart-meter with smart-hub; add periodic post to backend;
    # TODO important !!! parameterize simulation
    # http://host_placeholder:5000

    export BACKEND_HOST="prosumer${i}_backend-server_1"
    export GETH_HOST="prosumer${i}_geth_1"
    export MONGO_HOST="prosumer${i}_mongo_1"
    export SMART_HUB_HOST="prosumer${i}_smart-hub_1"
    export DATA_STREAM_HOST="prosumer${i}_data-stream_1"

    export MONGO_EXPRESS_PORT=$((MONGO_EXPRESS_PORT + i))
    export SMART_HUB_PORT=$((SMART_HUB_PORT + i))
    export FRONTEND_PORT=$((FRONTEND_PORT + i))
    export DATA_STREAM_PORT=$((DATA_STREAM_PORT + i))

    export PROSUMER_ID=${PROSUMERS_IDS[i]}

    export PROSUMER_CONTRACT=$(docker run --network prosumer${i}_default -e GETH_HOST=${GETH_HOST} -e GRID_CONTRACT=${GRID_CONTRACT} --name prosumer${i}_prosumer_registration_1 backend-server node prosumer_registration.js)
    verbose_print "Prosumer registered with contract at address ${PROSUMER_CONTRACT}"

    docker-compose -f docker-compose-hub.yaml -p prosumer"$i" up -d --build
    docker stop "prosumer${i}_simulation_1"
  done
}

# DESC: Start each prosumer simulation container
# ARGS: None
# OUTS: None
function start_simulation() {
  for ((i = 1; i <= prosumers_no; i++)); do
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
  # lock_init system

  docker_cleanup
  # docker_logging
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
