#!/bin/bash

# Get command line arguments
args=("$@")

# Some parameters
SUB_DIR="benchmark"

Help()
{
    echo " ************************************************************************ "
    echo " Script to run Coniql performance tests "
    echo " - Requires:"
    echo "      - EPICS installed and available"
    echo "      - Coniql installed into a Python virtual environment"
    echo " - Usage:"
    echo "     Run from the top of the coniql directory"
    echo "       ./benchmark/run_performance_test <options...>"
    echo "     options:"
    echo "      -h | --help:      display this help message"
    echo "      -p | --path:      [required] path to Python virtual env. where the"
    echo "                         Coniql application has been installed."
    echo "      -c | --clients:   [optional] number of websocket clients to run."
    echo "                         If not provided then default is 1."
    echo "      -n | --npvs:      [optional] number of PVs to subscribe to. If not "
    echo "                         provided then default is 100."
    echo "      -s | --samples:   [optional] number of sample to collect. If not "
    echo "                         provided then default is 1000."
    echo "      -w | --websocket: [optional] websocket protocol to use. "
    echo "                         Options: "
    echo "                               1: graphql-ws (old)"
    echo "                               2: graphql-transport-ws (new)"
    echo "                         If not provided then default is 2."
    echo "     E.g."
    echo "      ./benchmark/run_performance_test -p ../venv -c 1 -n 10 -s 1000 -w 2"
    echo " ************************************************************************ "
}

# Display help message if not arguments are provided
if [ -z ${args[0]} ]; then
    Help
    exit
fi

# Parse command line options
VALID_ARGS=$(getopt -o hp:c:n:s:w: --long help,path:,clients:,npvs:,samples:,websocket: -- "$@")
if [[ $? -ne 0 ]]; then
    exit 1;
fi

eval set -- "$VALID_ARGS"
while [ : ]; do
    case "$1" in
        -h | --help)
            Help
            exit 1
            ;;
        -p | --path)
            CONIQL_DIR="$2"
            if [ ! -d $CONIQL_DIR ]; then
                echo "Coniql virtual env directory '$CONIQL_DIR' does not exist."
                exit 1
            fi
            shift 2
            ;;
        -c | --clients)
            N_CLIENTS="$2"
            if ! [[ $N_CLIENTS =~ ^[0-9]+$ ]]; then
                echo "Number of clients must be an integer"
                exit
            fi
            shift 2
            ;;
        -n | --npvs)
            N_PVS="$2"
            if ! [[ $N_PVS =~ ^[0-9]+$ ]]; then
                echo "Number of PVs must be an integer"
                exit
            fi
            shift 2
            ;;
        -s | --samples)
            N_SAMPLES="$2"
            if ! [[ $N_SAMPLES =~ ^[0-9]+$ ]]; then
                echo "Number of samples must be an integer"
                exit
            fi
            shift 2
            ;;
        -w | --websocket)
            PROTOCOL="$2"
            if [[ $PROTOCOL -ne 1 ]] && [[ $PROTOCOL -ne 2 ]]; then
                echo "Invalid websocket protocol option"
                echo " Select from:"
                echo "  1: graphql-ws (old)"
                echo "  2: graphql-transport-ws (new)"
                exit
            fi
            shift 2
            ;;
        --) shift;
            break
            ;;
    esac
done

# Check what variables have been set by user
if [ -z $CONIQL_DIR ]; then
    echo "Coniql virtual env directory has not been provided."
    echo "Run './benchmark/run_performance_test --help' for script usage."
    exit
fi
if [ -z $N_CLIENTS ]; then
    N_CLIENTS=1
    echo "Number of clients not provided, defaulting to $N_CLIENTS"
fi
if [ -z $N_PVS ]; then
    N_PVS=1
    echo "Number of PVs not provided, defaulting to $N_PVS"
fi
if [ -z $N_SAMPLES ]; then
    N_SAMPLES=1000
    echo "Number of samples not provided, defaulting to $N_SAMPLES"
fi
if [ -z $PROTOCOL ]; then
    PROTOCOL=2
    echo "Websocket protocol not provided, defaulting to 'graphql-transport-ws' (2)"
fi

$SUB_DIR/generate_db.sh $SUB_DIR $N_PVS

# Make directory to store logs
LOG_DIR=$SUB_DIR"/logs"
if [ ! -d $LOG_DIR ]; then
    mkdir -p $LOG_DIR;
fi

# 1. EPICS IOCS
CMD1="softIoc -d $SUB_DIR/coniqlPerformanceTestDb.db"
CMD1_TO_LOG=$CMD1" &> $LOG_DIR/epics_ioc.log"
TAB1=(--tab -- bash -c "${CMD1_TO_LOG}")
echo "-> Starting EPICS IOC"
gnome-terminal "${TAB1[@]}"


#2. Coniql
CMD2="sleep 2;source $CONIQL_DIR/bin/activate;coniql"
CMD2_TO_LOG=$CMD2" &> $LOG_DIR/coniql.log"
TAB2=(--tab -- bash -c "${CMD2_TO_LOG}")
echo "-> Starting Coniql"
gnome-terminal "${TAB2[@]}"

# Time script from starting of the Python clients
start_time="$(date -u +%s)"

# 3. Performance test
# Create a log directory for Python script in tmp
TMP_DIR="/tmp/coniql_performance_tests_$(date +"%Y-%m-%d-%H:%M:%S")"
mkdir -p "$TMP_DIR";
# Define output and log file
OUTPUT_FILE="$SUB_DIR/performance_test_results_NClients_$N_CLIENTS.txt"
PY_PROGRESS_FILE="$TMP_DIR/test_progress.txt"
PYCMD0="python -u $SUB_DIR/coniql_performance_test.py -n $N_PVS -s $N_SAMPLES -p $PROTOCOL -f $OUTPUT_FILE"
for ((i=1;i<=$N_CLIENTS;i++))
do
    # Configure first client to monitor subscription progress
    if [ $i -eq 1 ]; then
        PYCMD=$PYCMD0" --log-file $PY_PROGRESS_FILE"
    else
        # Subsequent clients should not create a CPU monitor
        # as the first instance will handle this
        PYCMD=$PYCMD0" --no-cpu-monitor"
    fi
    PYCMD_TO_LOG=$PYCMD" &> $LOG_DIR/performance_test_client$i.log"
    VENV="source $CONIQL_DIR/bin/activate"
    CLEANUP3="deactivate"
    CMD3="sleep 10;$VENV;$PYCMD_TO_LOG;$CLEANUP3;sleep 10"
    TAB3=(--tab -- bash -c "${CMD3}")
    echo "-> Starting websocket client $i"
    gnome-terminal "${TAB3[@]}"
done


# Monitor when the python performance test has finished
loop=true
running=false
progress=""
echo "-> Running "
while $loop
do
    sleep 1
    TASK=$(ps -ef | grep  "${PYCMD}" | grep -v grep | grep -v bash | awk '{print $2}')
    if [ -z "${TASK}" ]; then
        if $running; then
            loop=false
        fi
    else
        running=true
        tail=$(tail --lines=1 $PY_PROGRESS_FILE)
        if [ "${tail}" != "${progress}" ]; then
            progress="${tail}"
            echo "   "$progress
        fi
    fi
done
echo " Completed"

# Clean up long running applications (EPICS & Coniql)
for pid in $(pgrep softIoc) $(pgrep coniql)
do
    if [ -n "$pid" ]; then
        kill -INT $pid
    fi
done

end_time="$(date -u +%s)"
elapsed_time="$(($end_time-$start_time))"
echo "Performance test completed in $elapsed_time seconds"
