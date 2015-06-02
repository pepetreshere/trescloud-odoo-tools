# coding: utf-8
"""
Este archivo define un script para realizar una migración desde una vieja versión hasta una nueva
  versión. Las tareas necesarias se definen según se documenta en el mismo incidente mediante adjunto:

  https://docs.google.com/document/d/1TLX4fD-x8-8s7Wty0mB5sPwqE06qmGkrSojspyQh7I8

Nos vamos a dar a la tarea de lo siguiente:
    - Los servidores se encuentran localmente (host=127.0.0.1, en diferentes puertos).
    - Especificamos archivo de origen (requerido).
    - Especificamos puerto de origen (requerido).
    - Especificamos archivo de destino (requerido).
    - Especificamos puerto de destino (requerido).
"""

from ConfigParser import ConfigParser
import subprocess
import datetime
import argparse
import sys
import os

parser = argparse.ArgumentParser(description=u"Dados dos archivos de configuración de OpenERP, intenta realizar una "
                                             u"migración desde una base de datos en un servidor hacia otra en otro "
                                             u"servidor. Puede darse que los dos servidores (de bases de datos) sean "
                                             u"el mismo. El nombre de DB destino se infiere a partir del nombre de DB "
                                             u"de origen (más un distintivo), y la BD será creada. El sitio de origen "
                                             u"estará en mantenimiento mientras se realice este proceso de migración. ",
                                 epilog=u"Cuando este proceso se realice exitosamente, la base de datos de origen "
                                        u"permanecerá bloqueada sin posibilidad de que se vuelva a acceder a ella "
                                        u"bajo ningún concepto. IMPORTANTE REMARCAR que el servername que se tomará "
                                        u"en cuenta está relacionado con la base de datos (es decir: si la base de "
                                        u"datos es `mibase`, el nombre del host será `mibase.facturadeuna.com`).")
parser.add_argument('source_file', metavar="archivo OpenERP de origen", type=str,
                    help=u"Archivo .conf existente de configuración que se usa en el servidor de origen")
parser.add_argument('database', metavar="base de datos a exportar", type=str,
                    help=u"Nombre de la base de datos existente a exportar desde el servidor de origen. Una "
                         u"base de datos con el mismo nombre será creada en el servidor de destino. El host de "
                         u"OpenERP se identificará como `<basededatos>.facturadeuna.com` en todos los casos.")
parser.add_argument('target_file', metavar="archivo OpenERP de destino", type=str,
                    help=u"Archivo .conf existente de configuración que se usa en el servidor de destino")
parser.add_argument('oeexec_path', metavar="ubicacion de openerp-server", type=str,
                    help=u"Directorio donde se encuentra el archivo openerp-server.py, ej "
                         u"/usr/local/bin/openerp-deploy si el ejecutable se ubica en "
                         u"/usr/local/bin/openerp-deploy/openerp-server.py")

arguments = parser.parse_args()

source_file = os.path.abspath(arguments.source_file)
target_file = os.path.abspath(arguments.target_file)
database = arguments.database
oeexec_path = os.path.abspath(arguments.oeexec_path)
server_name = '%s.facturadeuna.com' % database
stats_craete_filename = os.path.join(os.getcwd(), 'stats_create.sql')


class PythonCoercibleConfigParser(ConfigParser):
    """
    Es un parser normal pero agrega un método (getcoerced) que nos facilita el convertir un
      valor a su equivalente apropiado en Python. Por lo demás, es un ConfigParser normal.
    """

    def getcoerced(self, section, option, raw=False, vars=None):
        """
        Intenta obtener un valor desde la configuracion pero realizando
          una coercion a entero, flotante, booleano, None, o dejándolo
          como string.
        :param section:
        :param option:
        :param raw:
        :param vars:
        :return:
        """

        value = self.get(section, option, raw, vars)
        if value is not None:
            """
            Intentamos convertir el valor de las tres formas que nos permitimos.
            """

            try:
                return int(value)
            except ValueError:
                pass

            try:
                return float(value)
            except ValueError:
                pass

            if isinstance(value, (str, unicode)):
                if value.lower() == 'false':
                    return False
                if value.lower() == 'true':
                    return True
                if value.lower() == 'none':
                    return None

        return value


class _Getch:
    """Gets a single character from standard input.  Does not echo to the screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


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


def input_option(message, options="yn", error_message=None, stderr=False):
    """
    Lee una opción de la pantalla
    """
    got = None
    while True:
        full_message = u"%s [%s]: " % (message, "/".join(options.lower()))
        if not stderr:
            print full_message,
        else:
            print >> sys.stderr, full_message,
        got = getch().lower()
        print got
        if got not in options:
            if error_message:
                print error_message % got
        else:
            break
    return got


def invoke(command, notify_error=True, ask_continue=True, *args, **kwargs):
    """
    Invoca un comando por shell. Devuelve el codigo de retorno, y lo normal
      es que muestra el mensaje de error apropiado cuando hubo un retorno
      distinto de 0, y que pregunte si se desea continuar a pesar de haber
      ocurrido un error.

    :returns: 0 si el proceso devolvio 0 o ante un error se permitió y se
      eligió continuar. 1 en otros casos.
    """
    print u"Ejecutando: " + u" ".join(command)
    returned = subprocess.call(command, shell=True, *args, **kwargs)
    if returned and notify_error:
        error_message = u"El comando devolvió un código de error (%s)" % returned
        if not ask_continue:
            print >> sys.stderr, error_message
        else:
            if input_option(error_message + u' ¿desea continuar?', stderr=True) == 'n':
                return returned
            else:
                return 0
    else:
        return returned


u"""
1. Obtenemos las variables de ambos archivos. Si no podemos abrir alguno de los dos archivos,
   debemos tirar error y detener el proceso, sin posibilidad de seguir. Tenemos que poder obtener
   los diferentes datos: db_host (como default será localhost), db_port (como default será 5432),
   xmlrpc_port (default en 8069 - si ocurre que el mismo puerto está en ambas configuraciones puede
   dar lugar a problemas al momento de volver a iniciar la instancia que se encuentra en mantenimiento),
   db_user (como default no usamos nada, y así será para luego correr los comandos de psql - recordando
   que el usuario que se tomará será el del shell), db_password (como default no usamos nada, y así será
   para luego correr los comandos de psql, rezando para que el usuario que realiza el log-in tenga
   acceso "confiado").
"""


def parse_files(source_file, target_file):
    """
    Parsea ambos archivos de la misma manera en que lo hace OpenERP, y devuelve los 5 (cinco)
      elementos dentro de cada archivo que nos importan (user, password, host, puerto, puerto de OE).
    """
    try:
        with open(source_file, 'r') as f:
            cfgparser = PythonCoercibleConfigParser(defaults={
                'xmlrpc_port': 8069
            }, allow_no_value=True)
            cfgparser.readfp(f)
            source_db_user = cfgparser.getcoerced('options', 'db_user')
            source_db_pass = cfgparser.getcoerced('options', 'db_password')
            source_db_host = cfgparser.getcoerced('options', 'db_host')
            source_db_port = cfgparser.getcoerced('options', 'db_port')
            source_oe_port = cfgparser.getcoerced('options', 'xmlrpc_port')

        with open(target_file, 'r') as f:
            cfgparser = PythonCoercibleConfigParser(defaults={
                'xmlrpc_port': 8069
            }, allow_no_value=True)
            cfgparser.readfp(f)
            target_db_user = cfgparser.getcoerced('options', 'db_user')
            target_db_pass = cfgparser.getcoerced('options', 'db_password')
            target_db_host = cfgparser.getcoerced('options', 'db_host')
            target_db_port = cfgparser.getcoerced('options', 'db_port')
            target_oe_port = cfgparser.getcoerced('options', 'xmlrpc_port')

        return (
            source_db_host, source_db_port, source_db_user, source_db_pass, source_oe_port
        ), (
            target_db_host, target_db_port, target_db_user, target_db_pass, target_oe_port
        )
    except Exception as e:
        print >> sys.stderr, u"No se pudieron abrir los archivos de configuración. Ocurrió una excepción (%s): %s" % (
            type(e).__name__, e.args
        )
        sys.exit(1)


u"""
2. Ejecutamos los comandos para refrescar el nginx y ponerlo en mantenimiento.
"""


def nginx_maintenance(database):
    # TODO HACER ESTE PUNTO.
    return 0


u"""
X. Inicio de sesion como postgres
"""


def su_postgres():
    return invoke("sudo su - postgres".split(' '))


u"""
3. Cortamos todas las conexiones existentes a postgres (para poder poner la base de datos
   y toda la aplicación en modo de mantenimiento).
"""


def postgres_terminate(database, host, user, password, port):
    """
    Ejecuta el comando en postgres que te corta todas las conexiones a la
      base de datos.
    """
    psql_command = ['psql']
    if host:
        psql_command.append('--host='+host)
    if user:
        psql_command.append('--username='+user)
    if port:
        psql_command.append('--port='+port)
    psql_command.append('--dbname='+database)
    psql_command.append(('--command="select pg_terminate_backend(procpid) from pg_stat_activity where datname = \'%s\' '
                         'and procpid <> pg_backend_pid()"') % database)
    if password:
        psql_command = ['PGPASSWORD='+password] + psql_command

    return invoke(psql_command)


u"""
4. Cambiamos el nombre de la base de datos para que tenga un nombre diferente.
"""


def postgres_rename(database, host, user, password, port, newname):
    """
    Ejecuta el comando en postgres que renombra la base de datos.
    """
    psql_command = ['psql']
    if host:
        psql_command.append('--host='+host)
    if user:
        psql_command.append('--username='+user)
    if port:
        psql_command.append('--port='+port)
    psql_command.append('--dbname='+database)
    psql_command.append('--command="alter database %s rename to %s"' % (database, newname))
    if password:
        psql_command = ['PGPASSWORD='+password] + psql_command

    return invoke(psql_command)


u"""
5. En la base de datos con el nuevo nombre instalamos una función de estadísticas.
"""


def postgres_old_stats(newname, host, user, password, port, sql_filename, output_filename):
    """
    Ejecuta el comando en postgres que instala la función de estadísticas en la
      base de datos vieja (con nuevo nombre).
    """
    psql_command = ['psql']
    if host:
        psql_command.append('--host='+host)
    if user:
        psql_command.append('--username='+user)
    if port:
        psql_command.append('--port='+port)
    psql_command.append('--dbname='+newname)
    psql_command.append('< ' + sql_filename)
    if password:
        psql_command = ['PGPASSWORD='+password] + psql_command

    psql_command_get = ['psql']
    if host:
        psql_command_get.append('--host='+host)
    if user:
        psql_command_get.append('--username='+user)
    if port:
        psql_command_get.append('--port='+port)
    psql_command_get.append('--dbname='+newname)
    psql_command_get.append('--command="select table_schema, table_name, count_rows(table_schema, table_name) from '
                            'information_schema.tables where table_schema not in (\'pg_catalog\', '
                            '\'information_schema\') and table_type=\'BASE TABLE\' order by 1, 2 desc"')
    psql_command_get.append('> ' + output_filename)
    if password:
        psql_command_get = ['PGPASSWORD='+password] + psql_command_get
    return invoke(psql_command) or invoke(psql_command_get)


u"""
6. Obtenemos un dump, en sql, de la base de datos de origen.
"""


def postgres_dump(database, host, user, password, port, newname):
    """
    Realiza un dump de la base de datos en formato sql.
    """
    pg_dump_command = ['time', 'pg_dump']
    if host:
        pg_dump_command.append('--host='+host)
    if user:
        pg_dump_command.append('--username='+user)
    if port:
        pg_dump_command.append('--port='+port)
    pg_dump_command.append('--dbname='+newname)
    pg_dump_command.append('-f /tmp/%s.sql' % database)
    if password:
        pg_dump_command = ['PGPASSWORD='+password] + pg_dump_command

    return invoke(pg_dump_command)


u"""
7. Bloqueamos permanentemente la base de datos vieja.
"""


def postgres_block(newname, host, user, password, port):
    """
    Realiza un dump de la base de datos en formato sql.
    """
    pg_block_command = ['psql']
    if host:
        pg_block_command.append('--host='+host)
    if user:
        pg_block_command.append('--username='+user)
    if port:
        pg_block_command.append('--port='+port)
    pg_block_command.append('--dbname='+newname)
    pg_block_command.append('--command="update pg_database set datallowconn = false where datname = \'%s\'"' % newname)
    if password:
        pg_block_command = ['PGPASSWORD='+password] + pg_block_command

    return invoke(pg_block_command)


u"""
8. Creamos la nueva base de datos (es la misma, pero en el nuevo servidor).
"""


def postgres_create(database, host, user, password, port):
    """
    Crea y popula una base de datos con un dump preexistente.
    """

    # Crear base de datos
    createdb_command = ['createdb']
    if database:
        createdb_command.append(database)
    if host:
        createdb_command.append('--host='+host)
    if user:
        createdb_command.append('--username='+user)
    if port:
        createdb_command.append('--port='+port)
    if password:
        createdb_command = ['PGPASSWORD='+password] + createdb_command

    # Importar base de datos
    pg_restore_command = ['pg_restore', '-n', 'public', '--no-owner']
    if host:
        pg_restore_command.append('--host='+host)
    if user:
        pg_restore_command.append('--username='+user)
    if port:
        pg_restore_command.append('--port='+port)
    if database:
        pg_restore_command.append('--dbname='+database)
    pg_restore_command.append('/tmp/%s.sql' % database)
    if password:
        pg_restore_command = ['PGPASSWORD='+password] + pg_restore_command

    return invoke(createdb_command) or invoke(pg_restore_command)


u"""
9. Desde la nueva base de datos obtenemos las estadisticas.
"""


def postgres_new_stats(newname, host, user, password, port, output_filename):
    """
    Obtiene las estadísticas de la nueva tabla, ya que la funcion ya existe.
    """

    psql_command_get = ['psql']
    if host:
        psql_command_get.append('--host='+host)
    if user:
        psql_command_get.append('--username='+user)
    if port:
        psql_command_get.append('--port='+port)
    psql_command_get.append('--dbname='+newname)
    psql_command_get.append('--command="select table_schema, table_name, count_rows(table_schema, table_name) from '
                            'information_schema.tables where table_schema not in (\'pg_catalog\', '
                            '\'information_schema\') and table_type=\'BASE TABLE\' order by 1, 2 desc"')
    psql_command_get.append('> ' + output_filename)
    if password:
        psql_command_get = ['PGPASSWORD='+password] + psql_command_get
    return invoke(psql_command_get)


u"""
10. Análisis de diferencias entre los dos archivos.
"""


def postgres_diff(old_output_file, new_output_file):
    """
    Obtiene una diferencia entre dos archivos. El valor de retorno será 1 si los dos
      archivos son diferentes.
    """

    return invoke(['diff', old_output_file, new_output_file])


u"""
11. Actualizamos la base de datos nueva (OpenERP).
"""


def openerp_update(openerp_path, target_config_file, database):
    """
    Corre el openerp para el nuevo servidor.
    """

    openerp_command = ['time', os.path.join(openerp_path, 'openerp-server.py'),
                       '-c', target_config_file, '-d', database, '-u', 'all', '--stop-after-init']
    return invoke(openerp_command)


u"""
12. Reactivamos el nginx en el viejo servidor.
"""


def nginx_new(database):
    """
    Hacemos que el nginx apunte al nuevo servidor
    """
    # TODO hacer esto
    return 0


u"""
13. Imprimimos mensaje de confirmación
"""


def confirm(newname):
    print u"""
    La actualización ha terminado.
    Debe verificar el log para determinar el éxito de la migración a los nuevos modulos de OpenERP.
    Si no encuentra errores debe eliminar manualmente la base de datos: %s
    """ % newname


(
    source_host, source_port, source_user, source_pass, source_oe_port
), (
    target_host, target_port, target_user, target_pass, target_oe_port
) = parse_files(source_file, target_file)


newname = database + '_' + datetime.datetime.now().strftime('%Y%m%d%H%I%S')
stats_old = '~/%s.old.txt' % database
stats_new = '~/%s.new.txt' % database


sys.exit(nginx_maintenance(database) or
         su_postgres() or
         postgres_terminate(database, source_host, source_user, source_pass, source_port) or
         postgres_rename(database, source_host, source_user, source_pass, source_port, newname) or
         postgres_old_stats(newname, source_host, source_user, source_pass, source_port, stats_craete_filename,
                            stats_old) or
         postgres_dump(database, source_host, source_user, source_pass, source_port, newname) or
         postgres_block(newname, source_host, source_user, source_pass, source_port) or
         postgres_create(database, target_host, target_user, target_pass, target_port) or
         postgres_new_stats(newname, target_host, target_user, target_pass, target_port, stats_new) or
         postgres_diff(stats_old, stats_new) or
         openerp_update(oeexec_path, target_file, database) or
         nginx_new(database) or
         confirm(newname))