#!/bin/sh
#    $1 es la instancia, como instancia-08-retail (el directorio sería)
#    $2 es el nombre del log, sin extensión, como openerp-server-multicore
#    $3 es el número de logs a concatenar (ej. 5 logs, uno por minuto)

#############################################################################################
#                                                                                           #
# Dado que el corte es cada 5 minutos, obtenemos los logs de los 5 minutos ya transcurridos #
#   (no se considera el minuto actual)                                                      #
#                                                                                           #
#############################################################################################
FILES=$(ls /opt/openerp/$1/log/ | grep "$2" | tail -n $3)
for file in $FILES
do
    cat /opt/openerp/$1/log/$file
done
