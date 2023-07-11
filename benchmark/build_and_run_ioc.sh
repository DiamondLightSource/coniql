#!/bin/bash
# Generate an EPICS database and then run a softIOC using it
# Requires:
#    EPICS installed and available
# Usage:
#    ./build_and_run_ioc.sh <num_pvs>
# where:
#    <num_pvs> = the number of records the database will contain

NUM_PVS=$1

./generate_db.sh . $NUM_PVS

softIoc -d ./coniqlPerformanceTestDb.db
