#!/bin/bash
# Usage ./run_performance_test <path/to/coniql/venv> <number-of-clients>
#   <path/to/coniql/venv> = path to the location of the python virtual 
#                           environment where Coniql has been installed
#   <number-of-clients>   = number of websocket clients to start up


# Get command line arguments
args=("$@")

# Some parameters
SUB_DIR="benchmark"
N_PVS=100
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
    echo "       ./benchmark/run_performance_test <coniql-path> <number-of-clients>"
    echo "     where:"
    echo "       - <coniql-path> = path to Python virtual env where the Coniql"
    echo "                         application has been installed"
    echo "       - <number-of-clients> = number of websocket clients to run"
    echo "     E.g."
    echo "       ./benchmark/run_performance_test ../venv 2"
    echo " ************************************************************************ "
}

if [ -z ${args[0]} ]; then
    Help
    exit
elif [ ${args[0]} = "--help" ]; then
    Help
    exit 
else
    CONIQL_DIR=${args[0]}
    if [ ! -d $CONIQL_DIR ]; then
        echo "Coniql virtual env directory '$CONIQL_DIR' does not exist."
        exit
    fi
fi

if [ -z ${args[1]} ]; then
    N_CLIENTS=1
    echo "Number of clients not provided, defaulting to 1"
else
    N_CLIENTS=${args[1]} 
    if ! [[ $N_CLIENTS =~ ^[0-9]+$ ]]; then
        echo "Number of clients must be an integer"
        exit
    fi
fi


# Setup: create db file for EPICS 
for ((i=0;i<N_PVS;i++))
do
    if [ $i -lt 10 ]; then 
        str_name="0$i"
    else
        str_name="$i"
    fi

    STR="record(calcout, \"TEST:REC$str_name\"){ field(DESC, \"Performance test record\") \
    field(SCAN, \".1 second\") field(A, \"0\") field(CALC, \"A + 1\") field(OUT, \"TEST:REC$str_name.A\")}"

    if [ $i -eq 0 ]; then
        echo $STR > $SUB_DIR/coniqlPerformanceTestDb.db
    else 
        echo $STR >> $SUB_DIR/coniqlPerformanceTestDb.db
    fi
done


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
    VENV_DIR="venv_test$i"
    INSTALL3="python -m venv $VENV_DIR;source $VENV_DIR/bin/activate;pip install --upgrade pip;\
    pip install websockets;pip install psutil"
    CLEANUP3="deactivate;rm -rf $VENV_DIR"
    CMD3="sleep 1;$INSTALL3;$PYCMD;$CLEANUP3;sleep 10"
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
pids=$(pgrep softIoc)
kill -INT $pids
pids=$(pgrep coniql)
kill -INT $pids

