# coding: utf-8
# Se debe utilizar CSV separado por tabulaciones y sin calificador de texto, esto por
# que hay textos con "," ";" y por que aca se complica eliminar el calificador de texto
#
#    Dada una fila CSV (es un array de elementos), la consideramos como columnas que pueden expresarse como:
#        <nombre> o <nombre>,f o <nombre>,field : un campo normal, escalar
#        <nombre>,m2m o <nombre>,many2many : un campo many2many
#
# Ejemplo: tax_id,m2m o tax_id,many2many
#
# Autor(es): Patricio Rangles, Luis Masuelli

# Importamos erppeek
from argparse import ArgumentParser
import os
import warning
import erppeek
import re
import csv
from itertools import izip_longest
import sys
import getpass


parser = ArgumentParser(description="Toma un archivo .csv (*.csv) y lo parsea como CSV, donde la primera fila "
                                    "del contenido va a ser considerada como una lista de columnas, y el resto "
                                    "de las filas va a ser considerada como una lista de registros, donde cada "
                                    "valor es para cada columna de las especificadas. Los mismos serán valores "
                                    "a ingresar en el modelo de OpenERP especificado.")

# Base de datos y modelo a afectar.
parser.add_argument('-h', '--host', metavar='host', dest="host", type=str, default='127.0.0.1',
                    help=u"Host al cual conectarse.")
parser.add_argument('-p', '--port', metavar='port', dest="port", type=int, default=8069,
                    help=u"Puerto al cual conectarse.")
parser.add_argument('-u', '--user', metavar='user', dest="user", type=str, default='openerp',
                    help=u"Usuario con el que conectarse")
parser.add_argument('-w', '--password', metavar='password', dest="password", type=str, default=None,
                    help=u"Contraseña. Si este script se está ejecutando directamente mediante línea de comandos, "
                         u"no se recomienda utilizar esta opción. Si esta opción no se especifica, se tomará en cuenta "
                         u"el contenido de la variable de entorno OEBULK_PASS. Si esta última no está asignada con "
                         u"un valor válido, se le preguntará al usuario la contraseña.")
parser.add_argument('-s', '--https', dest='https', default=False, action='store_true',
                    help=u"La conexión no será http sino https.")
parser.add_argument('-d', '--database', metavar='database', dest='database', default=None, type=str,
                    help=u"Nombre de la base de datos a utilizar.")
parser.add_argument('-m', '--model', metavar='model', dest='model', type=str, default=None,
                    help=u"Nombre del modelo en el cual se agregarán o borrarán elementos.")

# Configuración del lector CSV.
parser.add_argument('-D', '--delimiter', dest='delimiter', type=str, default=',', metavar='caracter',
                    help=u"Carácter delimitador de las líneas de CSV a cargar.")
parser.add_argument('-q', '--quote', dest='quote', type=str, default='"', metavar='caracter',
                    help=u"Carácter encomillador de los valores")
parser.add_argument('-S', '--skip-spaces', dest='skip_spaces', action='store_true', default=False,
                    help=u"Si se activa esta opción, los espacios que siguen a un carácter delimitador serán "
                         u"descartados (no formarán parte del próximo valor).")
parser.add_argument('-Q', '--double-quote', dest='double_quote', action='store_false', default=False,
                    help=u"Si se activa esta opción, se considerará un escapado correcto de caracter de comillado "
                         u"a la presencia de dos carácteres de comillado puestos juntos (finalmente se reconocerán "
                         u"como uno solo).")
parser.add_argument('-e', '--escape-char', metavar='caracter', dest='escape_char', type=str, default=None,
                    help=u"Especifica un carácter de escape. Útil si no se activa -D/--double-quote. Si no se "
                         u"especifica, no se permite ningún escapado. Lo normal es que el carácter de escape sea '\\', "
                         u"pero este no es el comportamiento predeterminado y debe considerarse con cuidado.")

# Configuración de los archivos de entrada y salida.
parser.add_argument('-i', '--import-file', dest='import_file', metavar='archivo', type=str, default=None,
                    help=u"Especifica el nombre del archivo desde el que se van a tomar los datos en CSV a insertar")
parser.add_argument('-r', '--result-file', dest='result_file', metavar='archivo', type=str, default=None,
                    help=u"Especifica el nombre del archivo en el cual se va a insertar el resultado de las "
                         u"operaciones")

arguments = parser.parse_args()


def fuckyou(message, exit_code=0):
    """
    Fuerza un mensaje de error y una salida de ejecución.
    :param message:
    :param exit_code:
    :return:
    """
    print >> sys.stderr, message
    exit(exit_code)


if not arguments.database.strip():
    fuckyou('Ninguna base de datos fue especificada', 1)


OE_HOST = '%s://%s:%s' % (('http' if arguments.https else 'https'), arguments.host, arguments.port)
OE_DB = arguments.database.strip()  # Base de Datos de OpenERP a conectarse
OE_LOGIN = arguments.user  # Usuario de OpenERP para consultas, debe tener Permisos
OE_MODEL = arguments.model
_OE_STDIN_USED = False


if arguments.password:
    OE_PASS = arguments.password
elif os.getenv('OEBULK_PASS'):
    OE_PASS = os.getenv('OEBULK_PASS')
else:
    _OE_STDIN_USED = True
    OE_PASS = getpass.getpass('Password: ')

if arguments.import_file:
    try:
        OE_SOURCE_FILE = open(arguments.import_file)
    except Exception as e:
        fuckyou('No se puede abrir para lectura el archivo a importar: %s', 2)
elif _OE_STDIN_USED:
    fuckyou(u"No se especificó ningun archivo de importación, y la entrada estándar ya está siendo "
            u"utilizada por otras operaciones. No se puede continuar.", 3)
else:
    OE_SOURCE_FILE = sys.stdin

if arguments.result_file:
    try:
        OE_RESULT_FILE = open(arguments.result_file, "ab")
    except Exception as e:
        fuckyou('No se puede abrir para escritura el archivo de salida: %s', 3)
else:
    OE_RESULT_FILE = sys.stdout
    print >> sys.stderr, u"¡Advertencia! el resultado del proceso será mostrado por salida estándar"


COLUMN_TYPE_FIELD = 1
COLUMN_TYPE_ONE2MANY = 2
COLUMN_TYPE_MANY2MANY = 3
COLUMN_TYPE_BOOLEAN = 4


def parse_columns(row, file_result):
    """
    Dada una fila CSV (es un array de elementos), la consideramos como columnas que pueden expresarse como:
        <nombre> o <nombre>,f o <nombre>,field : un campo normal, escalar
        <nombre>,m2m o <nombre>,many2many : un campo many2many
    """
    def _each_column(splitted):
        if len(splitted) == 1 or splitted[1].lower() in ['field', 'f']:
            return splitted[0], COLUMN_TYPE_FIELD
        elif splitted[1].lower() in ['o2m', 'one2many']:
            file_result.write("Advertencia!! El campo %s no puede especificarse como many2one porque este archivo"
                              " es plano. Se va a considerar como campo normal.\n" % splitted[0])
            return splitted[0], COLUMN_TYPE_FIELD
        elif splitted[1].lower() in ['m2m', 'many2many']:
            return splitted[0], COLUMN_TYPE_MANY2MANY
        elif splitted[1].lower() in ['b', 'bool', 'boolean']:
            return splitted[0], COLUMN_TYPE_BOOLEAN
        else:
            file_result.write("Advertencia!! El campo %s tiene una especificacion invalida: %s. Se va a usar campo "
                              "normal en su lugar.\n" % splitted)
            return splitted[0], COLUMN_TYPE_FIELD
    return [_each_column(str(element).split(",", 1)) for element in row]


def parse_row(columns, row, rownum, file_result):
    """
    Por cada elemento en la fila, evaluamos lo siguiente:
      * Si la fila tiene columnas en exceso, devolvemos (None, None) para esas columnas.
      * Si la fila tiene columnas en defecto, devolvemos (columna, [(6, 0, [])]) o (columna, None) para esas columnas.
      * Sino:
        * Si el valor para cierta columna en la fila corresponde a una columna de campo normal, devolvemos (columna, valor).
        * Si en cambio la columna para el valor es m2m, devolvemos (columna, [(6, 0, [1, 2, 3... los ids que sean])]) para ese elemento.
          Esperamos que el valor del campo sea algo como "1,2,3". Los valores que no sean numericos van a ser descartados.
    Todas esas tuplas generadas las metemos en un diccionario, del cual luego descartamos los valores con clave None.
    Devolvemos ese diccionario.
    """
    def parse_value(index_, field, value):
        if field is None:
            file_result.write("Advertencia!! Encontrado un valor adicional dentro de la fila %d "
                              "(columna extra: %d)\n" % (rownum, index_))
            return None, None
        elif field[1] == COLUMN_TYPE_FIELD:
            return field[0], value
        elif field[1] == COLUMN_TYPE_BOOLEAN:
            return field[0], {'1':True, 'true':True}.get(str(value).lower(), False)
        else:
            # field[1] == COLUMN_TYPE_MANY2MANY
            str_ids = [id_.strip() for id_ in str(value or '').split(',')]
            return field[0], [(6, 0, [int(str_id) for str_id in str_ids if re.match('^\d+$', str_id)])]
    record_elements = [parse_value(index_, field, value) for index_, (field, value) in enumerate(izip_longest(columns, row))]
    record = dict(record_elements)
    record.pop(None, None)  # si se metio algun None por exceso de columnas, lo tenemos que sacar
    return record


try:
    client = erppeek.Client(OE_HOST, OE_DB, OE_LOGIN,OE_PASS, verbose=True)
except Exception as e:
    fuckyou("Error al abrir la conexion: " + OE_HOST + " " + OE_DB + " " + OE_LOGIN + "\n", 4)

csv_reader = csv.reader(OE_SOURCE_FILE, delimiter=arguments.delimiter, quotechar=arguments.quote,
                        escapechar=arguments.escape_char, doublequote=arguments.double_quote,
                        skipinitialspace=arguments.skip_spaces, strict=True)
columns = ()
is_update = False
print >> OE_RESULT_FILE, "linea,nuevo_id,estado\n"
for rownum, row in enumerate(csv_reader):
    if rownum == 0:
        columns = parse_columns(row, OE_RESULT_FILE)
        is_update = any(c for c in columns if c[0] == 'id')
    else:
        registro = parse_row(columns, row, rownum, OE_RESULT_FILE)
        linea_resul_csv = ""
        if not is_update:
            try:
                OE_id = client.create(OE_MODEL, registro)
                print "id: " + str(OE_id)
                linea_resul_csv = str(rownum) + "," + str(OE_id) + "," + "CORRECTO"
            except Exception as e:
                print "error at record number: " + str(rownum)
                print >> sys.stderr, "Exception %s creating an item: %s" % (type(e).__name__, str(e))
                linea_resul_csv = str(rownum) + "," + str(False) + "," + "ERROR"
        else:
            id_ = registro.pop('id', False)
            if id_ is False:
                linea_resul_csv = str(rownum) + "," + str(False) + "," + "ERROR"
            else:
                try:
                    client.write(OE_MODEL, id_, registro)
                    print "id: " + str(id_)
                    linea_resul_csv = str(rownum) + "," + str(id_) + "," + "CORRECTO"
                except Exception as e:
                    print "error at record number: " + str(rownum)
                    print >> sys.stderr, "Exception %s updating item %d: %s" % (type(e).__name__, id_, str(e))
                linea_resul_csv = str(rownum) + "," + str(id_) + "," + "ERROR"
        print >> OE_RESULT_FILE, linea_resul_csv + "\n"