#!/bin/sh
#%# family=manual
#%# capabilities=autoconf suggest
AWK_FILE=$(cd `dirname $0` && pwd)/oe_transactions_minute.awk
BULK_FILE=$(cd `dirname $0` && pwd)/oe_log_bulk.sh
# watch out for the time zone of the logs => using date -u for UTC timestamps
DATABASE="$1"
PROCESS="$2"
LOGFILE="$3"
$BULK_FILE $PROCESS $LOGFILE 5 | grep "DEBUG $DATABASE openerp.netsvc.rpc.request: object.execute_kw time" | awk -f $AWK_FILE
# awk "BEGIN{print $result / 5}"