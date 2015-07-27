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
        echo "graph_title openerp rpc request count (beraca in instancia1)"
        echo graph_vlabel num requests/minute in last 30 minutes
        echo requests.label num requests
        exit 0
    ;;
esac
result=`/usr/local/bin/munin-openerp/oe_transactions_minute.sh beraca i-f2997d21 instancia-08-retail openerp-server-multicore`
echo "requests.value $result"