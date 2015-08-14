#!/bin/sh
#ej: $1 es 30000
#    $2 es i-f2997d21 (no lo usaremos)
#    $3 es instancia-08-retail
#    $4 es openerp-server-multicore
tail -n $1 /opt/openerp/$3/log/$4.log