#!/bin/sh
#%# family=manual
#%# capabilities=autoconf suggest
case $1 in
    autoconf)
        exit 0
    ;;
    suggest)
        exit 0
    ;;
    config)
        echo graph_category openerp
        echo "graph_title openerp rpc request count (all instancia1)"
        echo graph_vlabel num requests/minute in last 5 minutes
        echo requests.label num requests
        exit 0
    ;;
esac
result=`/usr/local/bin/munin-openerp/oe_transactions_minute.sh "[a-zA-Z0-9_]*" openerp70_instancia1 openerp-server-multicore`
echo "requests.value $result"