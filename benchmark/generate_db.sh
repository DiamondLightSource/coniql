#!/bin/bash
# Generate an EPICS record database of a specified size in a
# specified location

# Usage:
#    ./generate_db.sh <directory> <num_pvs>
# where:
#    <directory> = directory in which the database file will be created
#    <num_pvs> = the number of records the database will contain.


SUB_DIR=$1
N_PVS=$2

DATABASE_FILE=$SUB_DIR/coniqlPerformanceTestDb.db

# Setup: create db file for EPICS
echo "-> Creating EPICS db with $N_PVS PVs at $DATABASE_FILE"
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

done >$DATABASE_FILE

echo "-> Created EPICS db"
