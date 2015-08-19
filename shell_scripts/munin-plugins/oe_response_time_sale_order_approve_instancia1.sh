#!/bin/sh
#%# family=manual
#%# capabilities=autoconf suggest
case $1 in
    config)
        echo graph_category openerp
        echo "graph_title openerp rpc requests (sale.order approval in retail) min/average response time (all instancia1)"
        echo graph_vlabel seconds
        echo graph_args --units-exponent -3
        echo min.label min
        echo min.warning 1
        echo min.critical 5
        echo avg.label average
        echo avg.warning 1
        echo avg.critical 5
        exit 0
    ;;
esac
result=`/usr/local/bin/munin-openerp/oe_response_time_sale_order_approve.sh "[a-zA-Z0-9_]*" openerp70_instancia1 openerp-server-multicore`
echo -n "min.value "
echo ${result} | cut -d" " -f1
echo -n "avg.value "
echo ${result} | cut -d" " -f2
