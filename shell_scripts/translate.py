# coding: utf-8
from argparse import ArgumentParser
from ConfigParser import ConfigParser
from fnmatch import fnmatch
import sys
import os
import glob
import subprocess


class OEConfigParser(ConfigParser):

    def get(self, section, option, coerce=True, raw=False, vars=None):
        """
        Obtiene un elemento de configuración de OpenERP, casteándolo
          según corresponda.
        :param section:
        :param option:
        :param raw:
        :param vars:
        :return:
        """
        element = ConfigParser.get(self, section, option, raw, vars)
        if not coerce:
            return element

        try:
            return float(element)
        except ValueError:
            pass

        try:
            return int(element)
        except ValueError:
            pass

        return {
            'true': True,
            'false': False
        }.get(element.lower(), element)


def fuckyou(message, code):
    print >> sys.stderr, message
    sys.exit(code)


parser = ArgumentParser(description="Instala en una base de datos las traducciones automáticamente. Se debe "
                                    "especificar el script de cliente de OpenERP, la base de datos con la que "
                                    "trabajar, y el archivo de configuración a usar para correrlo.")
parser.add_argument('script', metavar='script', type=str, help=u"Script de ejecución de OpenERP.")
parser.add_argument('config', metavar='config', type=str, help=u"Archivo de configuración de servidor.")
parser.add_argument('database', metavar='database', type=str, help=u"Base de datos a usar.")
parser.add_argument('-p', '--pattern', metavar=u'máscara', dest="patterns", action="append", type=str, default=[], help=u"Cada rama a descargar (esta opción se puede incluir varias veces - en su ausencia permanece la rama 'master'), para todos los repositorios")
arguments = parser.parse_args()
addons_path = []


script = os.path.abspath(os.path.expanduser(arguments.script))
config = os.path.abspath(os.path.expanduser(arguments.config))
patterns = [os.path.abspath(os.path.expanduser(pattern)) for pattern in arguments.patterns]


if not (os.path.isfile(script) and os.access(script, os.X_OK)):
    fuckyou("El archivo de script de OpenERP debe existir y ser ejecutable por el usuario actual", 1)

try:
    with open(config) as fp:
        cfgparser = OEConfigParser()
        cfgparser.readfp(fp)
        addons_path = cfgparser.get('options', 'addons_path', coerce=False).split(',')
except Exception as e:
    fuckyou("Hubo un error al abrir o parsear el archivo de configuración de OpenERP elegido", 2)


def file_matches(filename):
    if patterns:
        """
        Solamente los archivos que respeten los patrones especificados se
          van a tomar en cuenta.
        """
        return any(fnmatch(filename, pattern) for pattern in patterns)
    else:
        """
        No se especificaron patrones para comparar. Cualquier archivo vale.
        """
        return True


for rep in addons_path:
    for filename in glob.iglob(os.path.join(rep, '*', 'i18n', 'es.po')):
        if file_matches(filename):
            CMD = '%s -c %s -d %s -l es_ES --i18n-import=%s --i18n-overwrite --stop-after-init' % (
                script, config, arguments.database, filename
            )
            print "Ejecutando: %s" % CMD
            subprocess.call(CMD.split())
print "Gracias por usar la herramienta de traducción de Trescloud para OpenERP"