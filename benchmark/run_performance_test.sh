#!/bin/bash
# Usage ./run_performance_test <path/to/coniql/venv> <number-of-clients>
#   <path/to/coniql/venv> = path to the location of the python virtual 
#                           environment where Coniql has been installed
#   <number-of-clients>   = number of websocket clients to start up


# Get command line arguments
args=("$@")

# Some parameters
SUB_DIR="benchmark"
N_SAMPLES=1000
# 1 = old, 2 = new
PROTOCOL=2

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
    echo "      -h | --help:    display this help message"
    echo "      -p | --path:    [required] path to Python virtual env. where the"
    echo "                       Coniql application has been installed."
    echo "      -c | --clients: [optional] number of websocket clients to run."
    echo "                       If not provided then default is 1."
    echo "      -n | --npvs:    [optional] number of PVs to subscribe to. If not "
    echo "                      provided then default is 100."
    echo "     E.g."
    echo "       ./benchmark/run_performance_test -p ../venv -c 1 -n 10"
    echo " ************************************************************************ "
}

if [ -z ${args[0]} ]; then
    Help
    exit
fi

VALID_ARGS=$(getopt -o hp:c:n: --long help,path:,clients:,npvs: -- "$@")
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

# Setup: create db file for EPICS 
echo "-> Creating EPICS db with $N_PVS PVs"
for ((i=0;i<$N_PVS;i++))
do

    record_name="TEST:REC$i"
    cat <<EOF
record(calcout, "$record_name")
{
    field(DESC, "Performance test record")
    field(SCAN, ".1 second")
    field(A, "0")
    field(CALC, "A + 1")
    field(OUT, "$record_name.A")
}
EOF

done >$SUB_DIR/coniqlPerformanceTestDb.db


# 1. EPICS IOCS
CMD1="softIoc -d $SUB_DIR/coniqlPerformanceTestDb.db"
TAB1=(--tab -- bash -c "${CMD1}")
echo "-> Starting EPICS IOC"
gnome-terminal "${TAB1[@]}"


#2. Coniql
CMD2="sleep 2;source $CONIQL_DIR/bin/activate;coniql"
TAB2=(--tab -- bash -c "${CMD2}")
echo "-> Starting Coniql"
gnome-terminal "${TAB2[@]}"


# 3. Performance test
OUTPUT_FILE="$SUB_DIR/performance_test_results_NClients_$N_CLIENTS.txt"
PYCMD="python $SUB_DIR/coniql_performance_test.py -n $N_PVS -s $N_SAMPLES -p $PROTOCOL -f $OUTPUT_FILE"
for ((i=1;i<=$N_CLIENTS;i++)) 
do
    VENV="source $CONIQL_DIR/bin/activate"
    CLEANUP3="deactivate"
    CMD3="sleep 10;$VENV;$PYCMD;$CLEANUP3;sleep 10"
    TAB3=(--tab -- bash -c "${CMD3}")
    echo "-> Starting websocket client $i"
    gnome-terminal "${TAB3[@]}"
done


# Monitor when the python performance test has finished
loop=true
running=false
echo -n "-> Running "
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
    fi
    echo -n "."
done
echo " Completed"

# Clean up long running applications (EPICS & Coniql)
for pid in $(pgrep softIoc) $(pgrep coniql)
do
    if [ -n "$pid" ]; then
        kill -INT $pid
    fi
done