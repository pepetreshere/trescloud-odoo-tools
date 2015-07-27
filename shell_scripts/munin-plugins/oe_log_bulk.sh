#!/bin/sh
#ej: $1 es 30000
#    $2 es i-f2997d21
#    $3 es instancia-08-retail
#    $4 es openerp-server-multicore
tail -n $1 /mnt/collected_logs/bucket-de-instancias/$2/*/$3/$4.log