#!/bin/python
# coding=utf-8
from datetime import datetime
import sys
import subprocess

date = datetime.now().strftime("%Y%m%d-%H%M%S")
#username = 'openerp70_instancia1'
username = 'openerp'
bucket = 'bucket-fdu-backups'
#host = 'fdu-postgres-04.cme2wnzlzxnr.us-east-1.rds.amazonaws.com'
host = 'localhost'


def backup(database, host, username):
    """
    Realiza un backup de la base de datos en cuestión.
    :param database:
    :param host:
    :param username:
    :return:
    """
    output_file = 'postgres.%s.dump.%s.sql' % (database, date)
    command = 'pg_dump -Fc dbname="%s" --host="%s" --username="%s" -f %s' % (
        database, host, username, output_file
    )
    print "Ejecutando: " + command
    returned = subprocess.call(command)
    if returned:
        print >> sys.stderr, "Exportando la base de datos %s hubo un error (%d)" % (database, returned)
    else:
        print "Exportación exitosa"

command = "psql --username=%s --dbname=postgres --host=%s -l | tail -n +4 | head -n -2 | cut -f1,2 -d'|'" % (username, host)
print "Ejecutando: " + command
psql = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
outdata, errdata = psql.communicate()
print outdata, errdata


outdata_lines = outdata.split('\n')
for line in outdata.split('\n'):
    try:
        _database, _user = line.split('|')
    except:
        continue
    _database = _database.strip()
    _user = _user.strip()
    if _user == username:
        backup(_database, host, username)