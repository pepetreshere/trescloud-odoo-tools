#!/bin/bash
backupTime=`date +%Y%m%d-%H%M`
backupBucket=bucket-fdu-backups
# backupRDS=fdu-postgres-04.cme2wnzlzxnr.us-east-1.rds.amazonaws.com
# backupDBuser=openerp70_instancia1
backupRDS=localhost
backupDBuser=openerp

# obtenemos todas las bases de datos para el usuario
databases=`psql -q -t -c "select d.datname from pg_database d inner join pg_user u on (u.usesysid = d.datdba) where u.usename = '${backupDBuser}';" template1 -U ${backupDBuser}`

# iteramos sobre ellas
for database in $databases
do
    backupFilename=postgres.${database}.dump.${backupTime}.sql
    pg_dump -Fc dbname=${database} -h ${backupRDS} -U ${backupDBuser} -f ${backupFilename}
done
