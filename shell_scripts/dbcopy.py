# coding=utf-8
from gettext import gettext as _
import argparse
import datetime
import os
import subprocess


class _Getch:
    """Gets a single character from standard input.  Does not echo to the screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self):
        return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

getch = _Getch()


def input_option(message, options="yn", error_message=None):
    """
    Lee una opción de la pantalla
    """
    got = None
    while True:
        print u"%s [%s]: " % (message, "/".join(options.lower())),
        got = getch().lower()
        print got
        if got not in options:
            if error_message:
                print error_message % got
        else:
            break
    return got

"""
Debemos tener lo siguiente en consideracion:
  [host][:puerto] de la base de datos de origen
  base de datos de origen
  usuario de la base de datos de origen
  password de la base de datos de origen

  [host][:puerto] de la base de datos de destino
  base de datos de destino
  usuario de la base de datos de destino
  password de la base de datos de destino

Las lineas de comando se generan con las siguientes opciones:
  pg_dump --dbname=... --username=... --password=... --host=... --port=... --file=archivotemporal.dump
"""

parser = argparse.ArgumentParser(description=u"Toma dos configuraciones de bases de datos: una de origen y una de "
                                             u"destino. Intenta descargar un dump de la base de datos de origen a "
                                             u"la de destino. Luego de eso, en ambas bases de datos instala una "
                                             u"función de verificación de tablas (verifica que las tablas sean "
                                             u"de cantidades iguales -indicador, algo precario, de que el proceso "
                                             u"tuvo éxito- y muestra las diferencias entre ambas tablas (si es que "
                                             u"no hubo éxito)",
                                 epilog=u"Se recomienda realizar este proceso a través de un tunel de SSH para "
                                        u"facilitarnos el especificar los datos de conectividad.\n"
                                        u"\n"
                                        u"Si no se muestran diferencias, debe considerarse -a los efectos de esta "
                                        u"aplicación- que el respaldo fue exitoso.",
                                 add_help=False)

parser.add_argument('-?', '--help', action='help', default=argparse.SUPPRESS, help=_('show this help message and exit'))
parser.add_argument('-h', '--source-host', metavar="host origen", dest="source_host", type=str, default=None,
                    help="Host de origen (ej. 127.0.0.1 o localhost)")
parser.add_argument('-p', '--source-port', metavar="puerto origen", dest="source_port", type=int, default=5432,
                    help="Puerto de origen (ej. 5432)")
parser.add_argument('-u', '--source-user', metavar="usuario origen", dest="source_user", type=str, default=None,
                    help="Usuario de origen (ej. admin, u openerp)")
parser.add_argument('-w', '--source-password', metavar="password de origen", dest="source_password", type=str, default=None,
                    help="Password de origen (para el usuario especificado - mucho cuidado con los caracteres "
                         "especiales enviados por shell)")
parser.add_argument('-d', '--source-dbname', metavar="base de datos de origen", dest="source_database", type=str,
                    default=None, help="Base de datos a replicar (si no se especifica, se va a buscar una base "
                                       "de datos con el mismo nombre que el usuario)")
parser.add_argument('-H', '--dest-host', metavar="host destino", dest="dest_host", type=str, default=None,
                    help="Host de destino (ej. 127.0.0.1 o localhost)")
parser.add_argument('-P', '--dest-port', metavar="puerto destino", dest="dest_port", type=int, default=5432,
                    help="Puerto de destino (ej. 5432)")
parser.add_argument('-U', '--dest-user', metavar="usuario destino", dest="dest_user", type=str, default=None,
                    help="Usuario de destino (ej. admin, u openerp)")
parser.add_argument('-W', '--dest-password', metavar="password de destino", dest="dest_password", type=str, default=None,
                    help="Password de destino (para el usuario especificado - mucho cuidado con los caracteres "
                         "especiales enviados por shell)")
parser.add_argument('-D', '--dest-dbname', metavar="base de datos de destino", dest="dest_database", type=str,
                    default=None, help="Base de datos hacia donde replicar (si no se especifica, se va a buscar una base "
                                       "de datos con el mismo nombre que el usuario)")


args = parser.parse_args()

directory = '~/.openerp-trescloud-migrations'
origin_password = args.source_password
destination_password = args.dest_password
sql_function_filename = os.path.join(os.path.dirname(__file__), 'dbcopy.sql')
curdate = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
dump_filename = '%s/%s.sql' % (directory, curdate)
stats_old_filename = '%s/%s.old.txt' % (directory, curdate)
stats_new_filename = '%s/%s.new.txt' % (directory, curdate)
diff_filename = '%s/%s.diff' % (directory, curdate)

"""
0. Creando directorio
"""

mkdir_command = ['mkdir', '-p', directory]

"""
1. Construyendo el comando psql para insertar una funcion SQL de estadistica de uso en la base de origen.
"""

origin_function_command = ['psql']

if args.source_host:
    origin_function_command.append('--host=%s' % args.source_host)

origin_function_command.append('--port=%d' % args.source_port)

if args.source_user:
    origin_function_command.append('--username=%s' % args.source_user)

if args.source_database:
    origin_function_command.append('--dbname=%s' % args.source_database)

origin_function_command.append('<')
origin_function_command.append(sql_function_filename)

"""
2. Construyendo el comando pg_dump (para formatos planos) desde la base de origen.
"""

dump_command = ['pg_dump', '-f', dump_filename]

if args.source_host is not None:
    dump_command.append('--host=%s' % args.source_host)

dump_command.append('--port=%d' % args.source_port)

if args.source_user is not None:
    dump_command.append('--username=%s' % args.source_user)

if args.source_database is not None:
    dump_command.append(args.source_database)

"""
3. Construyendo el comando para obtener una lista de estadistica de la base de datos de origen.
"""

origin_statistics_command = ['psql']

if args.source_host:
    origin_statistics_command.append('--host=%s' % args.source_host)

origin_statistics_command.append('--port=%d' % args.source_port)

if args.source_user:
    origin_statistics_command.append('--username=%s' % args.source_user)

if args.source_database:
    origin_statistics_command.append('--dbname=%s' % args.source_database)

origin_statistics_command.append('--command="select table_schema,  table_name, count_rows(table_schema, table_name) '
                                 'from information_schema.tables where table_schema not in (\'pg_catalog\', '
                                 '\'information_schema\') and table_type=\'BASE TABLE\' order by table_schema, table_name desc"')
origin_statistics_command.append("")
origin_statistics_command.append('>')
origin_statistics_command.append(stats_old_filename)

"""
4. Construyendo el comando para crear una base de datos en el host de destino.
"""

create_database_command = ['createdb']

if args.dest_database:
    create_database_command.append(args.dest_database)

if args.dest_user:
    create_database_command.append('--username=%s' % args.dest_user)

if args.dest_host:
    create_database_command.append('--host=%s' % args.dest_host)

if args.dest_port:
    create_database_command.append('--port=%s' % args.dest_port)

"""
5. Construyendo el comando psql para carga de dump (formato plano) en la base de destino.
"""

load_command = ['psql']

if args.dest_host:
    load_command.append('--host=%s' % args.dest_host)

load_command.append('--port=%d' % args.dest_port)

if args.dest_user:
    load_command.append('--username=%s' % args.dest_user)

if args.dest_database:
    load_command.append('--dbname=%s' % args.dest_database)

load_command.append('<')
load_command.append(dump_filename)

"""
6. Construyendo el comando psql para insertar una funcion SQL de estadistica de uso en la base de origen.
"""

destination_function_command = ['psql']

if args.dest_host:
    destination_function_command.append('--host=%s' % args.dest_host)

destination_function_command.append('--port=%d' % args.dest_port)

if args.dest_user:
    destination_function_command.append('--username=%s' % args.dest_user)

if args.dest_database:
    destination_function_command.append('--dbname=%s' % args.dest_database)

destination_function_command.append('<')
destination_function_command.append(sql_function_filename)

"""
7. Construyendo el comando para obtener una lista de estadistica de la base de datos de destino.
"""

destination_statistics_command = ['psql']

if args.dest_host:
    destination_statistics_command.append('--host=%s' % args.dest_host)

destination_statistics_command.append('--port=%d' % args.dest_port)

if args.dest_user:
    destination_statistics_command.append('--username=%s' % args.dest_user)

if args.dest_database:
    destination_statistics_command.append('--dbname=%s' % args.dest_database)

destination_statistics_command.append('--command="select table_schema,  table_name, count_rows(table_schema, table_name) '
                                      'from information_schema.tables where table_schema not in (\'pg_catalog\', '
                                      '\'information_schema\') and table_type=\'BASE TABLE\' order by table_schema, table_name desc"')
destination_statistics_command.append('>')
destination_statistics_command.append(stats_new_filename)

"""
8. Visualizando diferencias
"""

diff_command = ['meld', stats_new_filename, stats_old_filename]

"""
Todos los comandos juntos (probamos por pantalla)
"""

origin_password_env = ['PGPASSWORD=' + origin_password] if origin_password else []
destination_password_env = ['PGPASSWORD=' + destination_password] if destination_password else []

commands = [
    mkdir_command,
    origin_password_env + origin_function_command,
    origin_password_env + dump_command,
    origin_password_env + origin_statistics_command,
    destination_password_env + create_database_command,
    destination_password_env + load_command,
    destination_password_env + destination_function_command,
    destination_password_env + destination_statistics_command,
    diff_command
]

print """
--------
----------------
Herramienta migradora de datos de TresCloud Cia. Ltda.
----------------
--------
"""
for command in commands:
    print "Corriendo %s ..." % " ".join(command)
    returncode = subprocess.call(" ".join(command), shell=True)
    if returncode and (command != diff_command):
        message = u"El proceso devolvió un código resultado distinto de 0 (código: %d). Esto puede significar un error. ¿Desea continuar de todos modos?" % \
                  (returncode,)
        if input_option(message) == 'n':
            break

print """
--------
Gracias por migrar con Trescloud.
--------
"""