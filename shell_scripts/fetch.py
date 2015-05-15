#!/usr/bin/python
#coding: utf-8
import argparse
from datetime import datetime
import getpass
import os
import urllib
import errno
import subprocess
import sys
import re


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

parser = argparse.ArgumentParser(description=u"Toma un usuario de GitHub y uno o más repositorios, con una o más ramas, e intenta clonarlos y pullear sus ramas.", epilog="Ingresar un usuario y una clave es fundamental para los repositorios privados.")

u"""
Necesitamos los siguientes elementos:
  usuario de github (-u, --user, obligatorio)
  contraseña del usuario de github (-p, --password, opcional)
  repositorios a bajar (-r, --repo, array, al menos uno)
  ramas a bajar (-b, --branch, array, al menos una)
  directorio (opcional o `pwd`)
"""

parser.add_argument('-u', '--user', metavar='usuario', dest='user', type=str, default=None, help=u"Usuario de GitHub")
parser.add_argument('-p', '--password', metavar='clave', dest='password', type=str, default=None, help=u"Password para ese usuario (no se recomienda pasarlo por consola si se ejecuta directamente el comando)")
parser.add_argument('-b', '--branches', metavar='rama', dest="branches", action="append", type=str, default=[], help=u"Cada rama a descargar (esta opción se puede incluir varias veces - en su ausencia permanece la rama 'master'), para todos los repositorios")
parser.add_argument('-d', '--directory', metavar='directorio', default=None, help=u"Directorio en donde descargar los repositorios (o descarga en el directorio de trabajo actual)")
parser.add_argument('repositories', metavar='repositorio', nargs='+', help=u"Repositorios a clonar, si no existen. Debe especificarse como una lista de repositorios: <repo> <repo> <repo>, donde cada repositorio puede expresarse como <nombre> o <usuario>/<nombre>. Esto último es necesario si el repositorio no pertenece al usuario actual, sino que es de otro quien nos dió permisos. Para repositorios pertenecientes al usuario actual, especificar el usuario es permitido, pero no requerido.")

args = parser.parse_args()
args = {
    'directory': args.directory or os.getcwd(),
    'repositories': args.repositories,
    'branches': args.branches or [],
    'user': args.user,
    'password': args.password
}

print u"""
----------
---------------------------------
---------------------------------------------------------------
TRESCLOUD - Utilitario para descarga de repositorios de GitHub.
---------------------------------------------------------------
---------------------------------
-----------
"""

if args['password']:
    print u"""
---------------------------------
Advertencia! Ingresando password en la linea de comando! Hacer esto directamente en la línea de comando puede ser peligroso
---------------------------------
"""

if not args['user']:
    while not args['user']:
        args['user'] = raw_input("Usuario de GitHub: ").strip()
        if not args['user']:
            print "Debe ingresar el usuario de GitHub"

if not args['password']:
    while not args['password']:
        args['password'] = getpass.getpass("Password de GitHub: ")


def input_option(message, options="yn", error_message=None):
    """
    Lee una opción de la pantalla
    """
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


if not args['branches']:
    print u"""
---------------------------------
No ha ingresado ningún nombre de rama mediante línea de comandos (usando opción -b o --branches).
Tiene la oportunidad de indicar, a continuación, las ramas a descargar, una por una. Si no ingresa el nombre de ninguna rama, se descargará la rama "master". Si ingresa el nombre de, al menos, una rama, entonces dichas ramas se descargarán (no se incluirá "master" de manera implícita).
---------------------------------
"""
    while input_option(u'¿Desea agregar una rama a la lista de ramas a descargar?') == 'y':
        rama = raw_input('Ingrese nombre de rama: ').strip()
        if rama:
            args['branches'].append(rama)
        else:
            print u"No ha ingresado ningún dato"
    if not args['branches']:
        args['branches'].append('master')


def git_exists():
    """
    Intenta ejecutar "git --version". Si falla, no tenemos git instalado o no se puede localizar.
    """
    try:
        subprocess.call("git --version".split())
        return True
    except os.error as e:
        return False


def git_pull(branch):
    """
    git pull origin "<branch>"
    """

    command = "git checkout {branch}".format(branch=branch).split()
    returned = subprocess.call(command)

    if returned == 1:
        # la rama no existe: hay que crearla
        print "Cargando y seleccionando nueva rama {branch} desde remoto".format(branch=branch)
        command = "git checkout -b {branch} --track origin/{branch}".format(branch=branch).split()
        returned = subprocess.call(command)
        if returned == 1:
            # la rama remota no existe
            print "¡¡¡ La rama remota {branch} no existe !!!".format(branch=branch)
        else:
            print "Seleccionada la rama {branch}".format(branch=branch)
    else:
        # la rama local existe
        # 1. stasheamos ...
        print "Haciendo stash en rama {branch}".format(branch=branch)
        fecha_actual = datetime.now().strftime("%Y%m%d%H%M%S%f")
        print "..."
        command = 'git stash save "Stashed on {fecha_actual} by fetcher.py"'.format(fecha_actual=fecha_actual).split(' ', 3)
        print "..."
        returned_stash = subprocess.call(command)
        print "..."
        if returned_stash != 0:
            print "¡¡¡ No se pudo hacer stash en la rama {branch} !!!".format(branch=branch)
        # 2. pulleamos ...
        print "Haciendo pull en rama {branch}".format(branch=branch)
        command = "git pull origin {branch} ".format(branch=branch).split()
        returned = subprocess.call(command)
        if returned != 0:
            # la rama remota no existe, o no esta trackeada !!!
            print "¡¡¡ La rama local {branch} no tiene trackeo, o la rama remota origin/{branch} no existe !!!".format(branch=branch)
        # 3. un-stasheamos (si es que no hubo error al hacer stash) ...
        if returned_stash == 0:
            # obtenemos lista de stashes previos. debemos encontrar al primero con fecha actual.
            command = "git stash list".split()
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            outdata, errdata = process._communicate("")
            output_lines = [l for l in (l.strip() for l in outdata.split("\n")) if l]
            for line in output_lines:
                if fecha_actual in line and branch in line:
                    match = re.match("^stash@\{(\d+)\}", line)
                    if match:
                        # encontramos un stash con fecha actual y rama actual. obtenemos su indice
                        stash_index = match.group(0)
                        # intentamos hacer el stash pop
                        print "Haciendo stash-pop en rama {branch}".format(branch=branch)
                        command = ("git stash pop stash@{%d}" % stash_index).split()
                        returned = subprocess.call(command)
                        if returned != 0:
                            print ("¡¡¡ Hubo un error al intentar revertir el stash@{%d} !!!" % stash_index)
                    break


def git_clone(repo, repo_name):
    """
    git clone https://(user):(password)@github.com/(user)/(repo)
    """
    username = urllib.quote_plus(args['user'])
    password = args['password']
    repository = urllib.quote(repo)
    if '/' not in repository:
        repository = username + '/' + repository
    command = "git clone https://{username}:{password}@github.com/{repository}.git {repo_name}".format(username=username, password=password, repository=repository, repo_name=repo_name).split()
    subprocess.call(command)


if not git_exists():
    print u"""
---------------------------------------
!!! Bestia! no tienes Git instalado !!!
---------------------------------------
"""
    sys.exit(1)

if input_option(u'Está a punto de crear los repositorios en "{directory}". ¿Desea continuar?'.format(**args)) == 'y':
    
    initial_path = os.getcwd()
    try:
        path = ''
        try:
            os.makedirs(args['directory'])
        except os.error as e:
            if e.errno != errno.EEXIST:
                raise e
        os.chdir(args['directory'])

        for repository in args['repositories']:
            repo_name = repo_name = repository.split('/')[1] if '/' in repository else repository
            path = os.path.join(args['directory'], repo_name)
            git = os.path.join(path, '.git')
            exists = os.path.exists(git)
            isdir = os.path.isdir(git)
            if not isdir:
                if exists:
                    os.unlink(git)
                    os.remove(path)
                print u"""
---------------------------------
Clonando repositorio %s (usuario: %s)
---------------------------------
""" % (repository, args['user'])
                git_clone(repository, repo_name)
            os.chdir(path)

            for branch in args['branches']:
                print u"""
---------------------------------
Descargando rama %s en repositorio %s (usuario: %s)
---------------------------------
""" % (branch, repository, args['user'])
                git_pull(branch)
            os.chdir(args['directory'])
    except os.error as e:
        if e.errno == errno.ENOENT:
            print "No existe el directorio %s - probablemente no se pudo clonar" % path
        else:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print "Ocurrió una excepción en linea %d: %s - %s" % (exc_tb.tb_lineno, exc_type.__name__, exc_obj.message)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print "Ocurrió una excepción en linea %d: %s - %s" % (exc_tb.tb_lineno, exc_type.__name__, exc_obj.message)
    finally:
        os.chdir(initial_path)
