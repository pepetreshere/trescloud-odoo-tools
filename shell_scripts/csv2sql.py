#!/usr/bin/python
# coding=utf-8
from csv import reader
from argparse import ArgumentParser
from itertools import izip_longest
import re
import sys


parser = ArgumentParser(description="Toma un archivo .csv (*.csv) y lo parsea como CSV, donde la primera fila "
                                    "del contenido va a ser considerada como una lista de columnas, y el resto "
                                    "de las filas va a ser considerada como una lista de registros, donde cada"
                                    "valor es para cada columna de las especificadas.")
parser.add_argument('-t', '--table', metavar='table', type=str, default=None,
                    help=u"Nombre de la tabla en la cual se generarán los inserts.")
parser.add_argument('-d', '--delimiter', dest='delimiter', type=str, default=',', help=u"Delimitador de las líneas.")
parser.add_argument('-q', '--quote', dest='quote', type=str, default='"', help=u"Encomillador de los valores")
parser.add_argument('-s', '--skip-spaces', dest='skip_spaces', action='store_true', default=False,
                    help=u"Si se activa esta opción, los espacios que siguen a un carácter delimitador serán "
                         u"descartados (no formarán parte del próximo valor).")
parser.add_argument('-D', '--double-quote', dest='double_quote', action='store_false', default=False,
                    help=u"Si se activa esta opción, se considerará un escapado correcto de caracter de comillado "
                         u"a la presencia de dos carácteres de comillado puestos juntos (finalmente se reconocerán "
                         u"como uno solo).")
parser.add_argument('-e', '--escape-char', dest='escape_char', type=str, default=None,
                    help=u"Especifica un carácter de escape. Útil si no se activa -D/--double-quote. Si no se "
                         u"especifica, no se permite ningún escapado. Lo normal es que el carácter de escape sea '\\', "
                         u"pero este no es el comportamiento predeterminado y debe considerarse con cuidado.")
parser.add_argument('-S', '--sql-bulk', dest='sql_bulk', type=int, default=1000,
                    help=u"Especifica el número de registros que se pondrán al mismo tiempo en una sentencia "
                         u"de inserción SQL (INSERT). El valor predeterminado es 1000.")
arguments = parser.parse_args()


table = arguments.table
delimiter = arguments.delimiter
quote = arguments.quote
skip_spaces = arguments.skip_spaces
escape_char = arguments.escape_char
double_quote = arguments.double_quote
sql_bulk = arguments.sql_bulk


if delimiter.lower() == 'comma':
    delimiter = ','
if delimiter.lower() == 'semicolon':
    delimiter = ';'

if quote.lower() == "double":
    quote = '"'
if quote.lower() == "single":
    quote = "'"


def fuckyou(message, code):
    print >> sys.stderr, message
    sys.exit(code)


def chunk(elements, bulk):
    k = 0
    l = len(elements)
    while k < l:
        yield elements[k:k + bulk]
        k += bulk


def escape(v):
    if isinstance(v, (int, long, float)):
        return v
    if v is None or len(v) == 0:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    return "'" + unicode(v).replace("'", "''") + "'"


def sql_insert_line(row):
    return "(%s)" % (",".join(escape(v) for v in row))


def sql_insert_lines(rows):
    return ",\n".join(sql_insert_line(row) for row in rows)


def sql_insert(table, columns, rows):
    return "insert into %s(%s) values\n%s;" % (table, ",".join(columns), sql_insert_lines(rows))


if not table:
    fuckyou('Argument -t/--table is required', 1)

match = re.match('[a-z][a-z0-9_]', table, re.I)
if not match:
    fuckyou("Invalid table name (it must start with letter and consist of letters, numbers, and _): " + table, 1)

try:
    first = True
    columns = ()
    result = []

    for row in reader(sys.stdin, delimiter=delimiter, quotechar=quote, escapechar=escape_char,
                      doublequote=double_quote, skipinitialspace=skip_spaces, strict=True):
        if first:
            columns = row
            first = False
        else:
            result.append([p[1] for p in izip_longest(columns, row[0:len(columns)])])

    if first:
        fuckyou("CSV File was empty. No SQL file was generated", 1)

    for chunked in chunk(result, sql_bulk):
        print sql_insert(table, columns, chunked)

except Exception as e:
    fuckyou("An unexpected error occurred (%r)" % e, 255)