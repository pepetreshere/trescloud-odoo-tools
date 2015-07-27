#!/bin/sh
#%# family=manual
#%# capabilities=autoconf suggest
AWK_FILE=$(cd `dirname $0` && pwd)/oe_response_time.awk
BULK_FILE=$(cd `dirname $0` && pwd)/oe_log_bulk.sh
# watch out for the time zone of the logs => using date -u for UTC timestamps
DATABASE="$1"
INSTANCE="$2"
PROCESS="$3"
LOGFILE="$4"
LINE=$($BULK_FILE 30000 $INSTANCE $PROCESS $LOGFILE | grep -P "^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}" | tail -n 1)
if [ -z "$LINE" ]
then
    FECHA=`date +"%Y-%m-%d %H:%M:%S" -ud '5 min ago'`
else
    T=$(echo $LINE | cut -c1-19)
    FECHA=`date +"%Y-%m-%d %H:%M:%S" -d@$(expr $(date +%s --date="$T") - 300)`
fi
$BULK_FILE 30000 $INSTANCE $PROCESS $LOGFILE | grep "DEBUG $DATABASE openerp.netsvc.rpc.request: object.execute_kw time" | awk -f $AWK_FILE -v FECHA="$FECHA"